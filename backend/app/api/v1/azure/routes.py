"""
REST API endpoints for Azure cost configuration and management.

Endpoints:
- GET /api/azure/ingest-config - List Azure ingest configurations
- POST /api/azure/ingest-config - Create Azure ingest configuration
- PATCH /api/azure/ingest-config/{id} - Update configuration
- POST /api/azure/test-connection - Test Azure API connection
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_db as get_db_dependency
from app.models import AzureCostIngestConfig, utcnow, new_id
from app.jobs.azure.azure_jobs import get_azure_access_token

router = APIRouter(prefix="/azure", tags=["azure"])


def get_db() -> Session:
    """Dependency injection for database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================================
# Azure Ingest Configuration
# ============================================================================

@router.get("/ingest-config")
def list_azure_ingest_configs(
    tenant_id: Optional[str] = Query(None, description="Filter by tenant"),
    db: Session = Depends(get_db),
):
    """
    List all Azure cost ingest configurations.

    Returns Azure subscription, tenant ID, and last sync status for each config.
    """
    query = db.query(AzureCostIngestConfig)

    if tenant_id:
        query = query.filter(AzureCostIngestConfig.tenant_id == tenant_id)

    configs = query.all()

    return {
        "count": len(configs),
        "configs": [
            {
                "id": c.id,
                "tenant_id": c.tenant_id,
                "azure_subscription_id": c.azure_subscription_id,
                "azure_tenant_id": c.azure_tenant_id,
                "client_id": c.client_id,
                "export_scope": c.export_scope,
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
def create_azure_ingest_config(
    tenant_id: str = Query(..., description="Tenant ID"),
    azure_subscription_id: str = Query(..., description="Azure subscription GUID"),
    azure_tenant_id: str = Query(..., description="Azure AD tenant GUID"),
    client_id: str = Query(..., description="Service Principal app ID"),
    client_secret: str = Query(..., description="Service Principal client secret"),
    export_frequency: str = Query("Daily", description="Daily or Monthly"),
    data_source: str = Query("actual_cost", description="actual_cost or amortized_cost"),
    enabled: bool = Query(True),
    db: Session = Depends(get_db),
):
    """
    Create a new Azure cost ingest configuration.

    Configures Azure Cost Management API access via Service Principal credentials.
    """
    # Check for duplicate
    existing = db.query(AzureCostIngestConfig).filter(
        AzureCostIngestConfig.tenant_id == tenant_id,
        AzureCostIngestConfig.azure_subscription_id == azure_subscription_id,
    ).one_or_none()

    if existing:
        raise HTTPException(status_code=409, detail="Configuration already exists")

    # Validate inputs
    if len(azure_subscription_id) != 36:
        raise HTTPException(status_code=400, detail="Invalid Azure subscription ID format")
    if len(azure_tenant_id) != 36:
        raise HTTPException(status_code=400, detail="Invalid Azure tenant ID format")
    if len(client_id) != 36:
        raise HTTPException(status_code=400, detail="Invalid client ID format")
    if export_frequency not in ["Daily", "Monthly"]:
        raise HTTPException(status_code=400, detail="export_frequency must be Daily or Monthly")
    if data_source not in ["actual_cost", "amortized_cost"]:
        raise HTTPException(status_code=400, detail="data_source must be actual_cost or amortized_cost")

    config = AzureCostIngestConfig(
        id=new_id(),
        tenant_id=tenant_id,
        azure_subscription_id=azure_subscription_id,
        azure_tenant_id=azure_tenant_id,
        client_id=client_id,
        client_secret_encrypted=client_secret,  # TODO: Encrypt in production using Key Vault
        export_scope=f"/subscriptions/{azure_subscription_id}",
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
        "azure_subscription_id": config.azure_subscription_id,
    }


@router.patch("/ingest-config/{config_id}")
def update_azure_ingest_config(
    config_id: str,
    export_frequency: Optional[str] = Query(None),
    data_source: Optional[str] = Query(None),
    enabled: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Update an Azure ingest configuration.

    Only provided fields are updated; others remain unchanged.
    """
    config = db.query(AzureCostIngestConfig).filter(
        AzureCostIngestConfig.id == config_id
    ).one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")

    if export_frequency:
        if export_frequency not in ["Daily", "Monthly"]:
            raise HTTPException(status_code=400, detail="export_frequency must be Daily or Monthly")
        config.export_frequency = export_frequency

    if data_source:
        if data_source not in ["actual_cost", "amortized_cost"]:
            raise HTTPException(status_code=400, detail="data_source must be actual_cost or amortized_cost")
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
def test_azure_connection(
    config_id: str = Query(..., description="Configuration ID"),
    db: Session = Depends(get_db),
):
    """
    Test Azure Cost Management API connection.

    Validates Service Principal credentials and API access.
    """
    config = db.query(AzureCostIngestConfig).filter(
        AzureCostIngestConfig.id == config_id
    ).one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")

    try:
        # Try to get an access token (validates credentials)
        token = get_azure_access_token(config)

        if not token:
            raise ValueError("No token returned from Azure")

        # Update config with success
        config.test_status = "success"
        config.test_message = "Successfully authenticated with Azure Cost Management API"
        config.last_tested_at = utcnow()
        db.commit()

        return {
            "status": "success",
            "message": "Azure connection test passed",
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
            detail=f"Azure connection test failed: {str(exc)}"
        )
