"""
REST API endpoints for GCP cost configuration and management.

Endpoints:
- GET /api/gcp/ingest-config - List GCP ingest configurations
- POST /api/gcp/ingest-config - Create GCP ingest configuration
- PATCH /api/gcp/ingest-config/{id} - Update configuration
- POST /api/gcp/test-connection - Test GCP BigQuery connection
"""

import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .auth import get_optional_tenant
from .database import SessionLocal, get_db
from .models import GcpCostIngestConfig, utcnow, new_id
from .gcp_jobs import get_bigquery_client

router = APIRouter(prefix="/api/gcp", tags=["gcp"])


def get_db() -> Session:
    """Dependency injection for database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================================
# GCP Ingest Configuration
# ============================================================================

@router.get("/ingest-config")
def list_gcp_ingest_configs(
    tenant_id: str = Depends(get_optional_tenant),
    db: Session = Depends(get_db),
):
    """
    List all GCP cost ingest configurations.

    Returns GCP project, billing account, and last sync status for each config.
    """
    query = db.query(GcpCostIngestConfig)

    if tenant_id:
        query = query.filter(GcpCostIngestConfig.tenant_id == tenant_id)

    configs = query.all()

    return {
        "count": len(configs),
        "configs": [
            {
                "id": c.id,
                "tenant_id": c.tenant_id,
                "gcp_project_id": c.gcp_project_id,
                "service_account_email": c.service_account_email,
                "billing_account_id": c.billing_account_id,
                "bq_dataset_id": c.bq_dataset_id,
                "bq_table_id": c.bq_table_id,
                "export_frequency": c.export_frequency,
                "data_source": c.data_source,
                "enabled": c.enabled,
                "last_synced_at": c.last_synced_at.isoformat() if c.last_synced_at else None,
                "last_tested_at": c.last_tested_at.isoformat() if c.last_tested_at else None,
                "test_status": c.test_status,
                "test_message": c.test_message,
                "created_at": c.created_at.isoformat(),
            }
            for c in configs
        ],
    }


@router.post("/ingest-config")
def create_gcp_ingest_config(
    tenant_id: str = Depends(get_optional_tenant),
    gcp_project_id: str = Query(..., description="GCP project ID"),
    service_account_email: str = Query(..., description="Service account email"),
    service_account_key: str = Query(..., description="Service account JSON key (base64 or JSON string)"),
    billing_account_id: str = Query(..., description="GCP billing account ID"),
    bq_dataset_id: str = Query("billing_export", description="BigQuery dataset ID"),
    bq_table_id: str = Query("gcp_billing_export_v1", description="BigQuery table ID"),
    export_frequency: str = Query("Daily", description="Daily or Monthly"),
    data_source: str = Query("standard", description="standard or detailed"),
    enabled: bool = Query(True),
    db: Session = Depends(get_db),
):
    """
    Create a new GCP cost ingest configuration.

    Configures BigQuery access for cost data retrieval.
    """
    # Check for duplicate
    existing = db.query(GcpCostIngestConfig).filter(
        GcpCostIngestConfig.tenant_id == tenant_id,
        GcpCostIngestConfig.gcp_project_id == gcp_project_id,
        GcpCostIngestConfig.billing_account_id == billing_account_id,
    ).one_or_none()

    if existing:
        raise HTTPException(status_code=409, detail="Configuration already exists")

    # Validate inputs
    if export_frequency not in ["Daily", "Monthly"]:
        raise HTTPException(status_code=400, detail="export_frequency must be Daily or Monthly")
    if data_source not in ["standard", "detailed"]:
        raise HTTPException(status_code=400, detail="data_source must be standard or detailed")

    # Validate service account key format
    try:
        # Try to parse as JSON
        if isinstance(service_account_key, str):
            key_dict = json.loads(service_account_key)
        else:
            key_dict = service_account_key

        if "type" not in key_dict or key_dict.get("type") != "service_account":
            raise ValueError("Invalid service account key format")
    except (json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid service account key: {str(exc)}"
        )

    config = GcpCostIngestConfig(
        id=new_id(),
        tenant_id=tenant_id,
        gcp_project_id=gcp_project_id,
        service_account_email=service_account_email,
        service_account_key_encrypted=json.dumps(key_dict),  # TODO: Encrypt in production
        billing_account_id=billing_account_id,
        bq_dataset_id=bq_dataset_id,
        bq_table_id=bq_table_id,
        export_frequency=export_frequency,
        data_source=data_source,
        enabled=enabled,
        test_status="pending",
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    db.add(config)
    db.commit()
    db.refresh(config)

    return {
        "status": "created",
        "config_id": config.id,
        "tenant_id": config.tenant_id,
        "gcp_project_id": config.gcp_project_id,
    }


@router.patch("/ingest-config/{config_id}")
def update_gcp_ingest_config(
    config_id: str,
    export_frequency: Optional[str] = Query(None),
    data_source: Optional[str] = Query(None),
    enabled: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Update a GCP ingest configuration.

    Only provided fields are updated; others remain unchanged.
    """
    config = db.query(GcpCostIngestConfig).filter(
        GcpCostIngestConfig.id == config_id
    ).one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")

    if export_frequency:
        if export_frequency not in ["Daily", "Monthly"]:
            raise HTTPException(status_code=400, detail="export_frequency must be Daily or Monthly")
        config.export_frequency = export_frequency

    if data_source:
        if data_source not in ["standard", "detailed"]:
            raise HTTPException(status_code=400, detail="data_source must be standard or detailed")
        config.data_source = data_source

    if enabled is not None:
        config.enabled = enabled

    config.updated_at = utcnow()
    db.commit()
    db.refresh(config)

    return {
        "status": "updated",
        "config_id": config.id,
        "updated_at": config.updated_at.isoformat(),
    }


@router.post("/test-connection")
def test_gcp_connection(
    config_id: str = Query(..., description="Configuration ID"),
    db: Session = Depends(get_db),
):
    """
    Test GCP BigQuery connection.

    Validates Service Account credentials and BigQuery access.
    """
    config = db.query(GcpCostIngestConfig).filter(
        GcpCostIngestConfig.id == config_id
    ).one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")

    try:
        # Try to create BigQuery client (validates credentials)
        client = get_bigquery_client(config)

        # Try a simple query to test connectivity
        test_query = f"""
        SELECT COUNT(*) as row_count
        FROM `{config.gcp_project_id}.{config.bq_dataset_id}.{config.bq_table_id}`
        LIMIT 1
        """
        query_job = client.query(test_query, timeout=30)
        query_job.result()

        # Update config with success
        config.test_status = "success"
        config.test_message = "Successfully connected to BigQuery"
        config.last_tested_at = utcnow()
        db.commit()

        return {
            "status": "success",
            "message": "GCP BigQuery connection test passed",
            "config_id": config.id,
            "test_time": config.last_tested_at.isoformat(),
        }

    except Exception as exc:
        # Update config with failure
        config.test_status = "failed"
        config.test_message = f"Connection test failed: {str(exc)}"
        config.last_tested_at = utcnow()
        db.commit()

        raise HTTPException(
            status_code=400,
            detail=f"GCP BigQuery connection test failed: {str(exc)}"
        )
