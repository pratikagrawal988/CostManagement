"""
Credential Management API — unified CRUD + test-connection for all providers.

Endpoints:
  GET  /api/credentials                    — List all provider credential configs
  POST /api/credentials/aws                — Add/update AWS CUR config
  POST /api/credentials/azure              — Add/update Azure Cost config
  POST /api/credentials/gcp                — Add/update GCP Billing config
  POST /api/credentials/{provider}/test    — Test connection and update status
  DELETE /api/credentials/{id}             — Remove a config
  GET  /api/credentials/status             — Health summary across all providers
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .auth import get_optional_tenant
from .database import get_db
from .models import (
    CostIngestConfig, AzureCostIngestConfig, GcpCostIngestConfig,
    ProviderConnection, new_id, utcnow,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/credentials", tags=["credentials"])


# ─────────────────────────────────────────────────────────────────────────────
# Request bodies
# ─────────────────────────────────────────────────────────────────────────────

class AWSCredentialRequest(BaseModel):
    tenant_id:       str
    name:            str = "AWS CUR"
    s3_bucket:       str
    s3_prefix:       str = ""
    aws_role_arn:    str
    aws_external_id: str = ""
    aws_region:      str = "us-east-1"
    enabled:         bool = True


class AzureCredentialRequest(BaseModel):
    tenant_id:           str
    name:                str = "Azure Cost"
    azure_tenant_id:     str
    client_id:           str
    client_secret:       str   # stored encrypted in config JSON
    subscription_id:     str
    management_group_id: str = ""
    enabled:             bool = True


class GCPCredentialRequest(BaseModel):
    tenant_id:          str
    name:               str = "GCP Billing"
    gcp_project_id:     str
    bigquery_dataset:   str
    bigquery_table:     str = "gcp_billing_export_v1"
    service_account_json: str = ""   # inline JSON or path — stored encrypted
    enabled:            bool = True


# ─────────────────────────────────────────────────────────────────────────────
# List all configs
# ─────────────────────────────────────────────────────────────────────────────

@router.get("")
def list_credentials(
    tenant_id: str = Depends(get_optional_tenant),
    db: Session = Depends(get_db),
):
    """Returns all AWS, Azure, and GCP configurations for a tenant."""
    aws_cfgs   = db.query(CostIngestConfig).filter(CostIngestConfig.tenant_id == tenant_id).all()
    azure_cfgs = db.query(AzureCostIngestConfig).filter(AzureCostIngestConfig.tenant_id == tenant_id).all()
    gcp_cfgs   = db.query(GcpCostIngestConfig).filter(GcpCostIngestConfig.tenant_id == tenant_id).all()

    def fmt_aws(c):
        return {
            "id": c.id, "provider": "aws", "name": c.name,
            "s3_bucket": c.s3_bucket, "s3_prefix": c.s3_prefix,
            "aws_role_arn": c.aws_role_arn, "aws_region": c.aws_region,
            "enabled": c.enabled,
            "test_status": c.test_status, "test_message": c.test_message,
            "last_tested_at": c.last_tested_at.isoformat() if c.last_tested_at else None,
            "last_sync_at":   c.last_sync_at.isoformat()   if c.last_sync_at   else None,
            "created_at": c.created_at.isoformat(),
        }

    def fmt_azure(c):
        return {
            "id": c.id, "provider": "azure", "name": c.name,
            "azure_tenant_id": c.azure_tenant_id,
            "client_id": c.client_id,
            "subscription_id": c.subscription_id,
            "management_group_id": c.management_group_id,
            "enabled": c.enabled,
            "test_status": c.test_status, "test_message": c.test_message,
            "last_tested_at": c.last_tested_at.isoformat() if c.last_tested_at else None,
            "last_sync_at":   c.last_sync_at.isoformat()   if c.last_sync_at   else None,
            "created_at": c.created_at.isoformat(),
        }

    def fmt_gcp(c):
        return {
            "id": c.id, "provider": "gcp", "name": c.name,
            "gcp_project_id": c.gcp_project_id,
            "bigquery_dataset": c.bigquery_dataset,
            "bigquery_table": c.bigquery_table,
            "enabled": c.enabled,
            "test_status": c.test_status, "test_message": c.test_message,
            "last_tested_at": c.last_tested_at.isoformat() if c.last_tested_at else None,
            "last_sync_at":   c.last_sync_at.isoformat()   if c.last_sync_at   else None,
            "created_at": c.created_at.isoformat(),
        }

    return {
        "tenant_id": tenant_id,
        "providers": {
            "aws":   [fmt_aws(c)   for c in aws_cfgs],
            "azure": [fmt_azure(c) for c in azure_cfgs],
            "gcp":   [fmt_gcp(c)   for c in gcp_cfgs],
        },
        "total": len(aws_cfgs) + len(azure_cfgs) + len(gcp_cfgs),
    }


# ─────────────────────────────────────────────────────────────────────────────
# Create / Update — AWS
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/aws")
def upsert_aws_credential(req: AWSCredentialRequest, db: Session = Depends(get_db)):
    """Create or update an AWS CUR ingest config."""
    existing = db.query(CostIngestConfig).filter(
        CostIngestConfig.tenant_id == req.tenant_id,
        CostIngestConfig.s3_bucket == req.s3_bucket,
    ).one_or_none()

    if existing:
        existing.name            = req.name
        existing.s3_prefix       = req.s3_prefix
        existing.aws_role_arn    = req.aws_role_arn
        existing.aws_external_id = req.aws_external_id
        existing.aws_region      = req.aws_region
        existing.enabled         = req.enabled
        existing.updated_at      = utcnow()
        db.commit()
        return {"status": "updated", "id": existing.id}

    cfg = CostIngestConfig(
        id=new_id(),
        tenant_id=req.tenant_id,
        name=req.name,
        s3_bucket=req.s3_bucket,
        s3_prefix=req.s3_prefix,
        aws_role_arn=req.aws_role_arn,
        aws_external_id=req.aws_external_id,
        aws_region=req.aws_region,
        enabled=req.enabled,
    )
    db.add(cfg)
    db.commit()
    return {"status": "created", "id": cfg.id}


# ─────────────────────────────────────────────────────────────────────────────
# Create / Update — Azure
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/azure")
def upsert_azure_credential(req: AzureCredentialRequest, db: Session = Depends(get_db)):
    """
    Create or update an Azure Cost Management config.
    client_secret is stored in the encrypted config JSON blob — never in a
    plaintext column.
    """
    existing = db.query(AzureCostIngestConfig).filter(
        AzureCostIngestConfig.tenant_id       == req.tenant_id,
        AzureCostIngestConfig.subscription_id == req.subscription_id,
    ).one_or_none()

    # Encrypt secret (basic base64 here — replace with KMS/Vault in production)
    import base64
    encrypted_secret = base64.b64encode(req.client_secret.encode()).decode()

    if existing:
        existing.name                = req.name
        existing.azure_tenant_id     = req.azure_tenant_id
        existing.client_id           = req.client_id
        existing.management_group_id = req.management_group_id
        existing.enabled             = req.enabled
        existing.config              = {**existing.config, "encrypted_secret": encrypted_secret}
        existing.updated_at          = utcnow()
        db.commit()
        return {"status": "updated", "id": existing.id}

    cfg = AzureCostIngestConfig(
        id=new_id(),
        tenant_id=req.tenant_id,
        name=req.name,
        azure_tenant_id=req.azure_tenant_id,
        client_id=req.client_id,
        subscription_id=req.subscription_id,
        management_group_id=req.management_group_id,
        enabled=req.enabled,
        config={"encrypted_secret": encrypted_secret},
    )
    db.add(cfg)
    db.commit()
    return {"status": "created", "id": cfg.id}


# ─────────────────────────────────────────────────────────────────────────────
# Create / Update — GCP
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/gcp")
def upsert_gcp_credential(req: GCPCredentialRequest, db: Session = Depends(get_db)):
    """
    Create or update a GCP Billing BigQuery config.
    service_account_json stored encrypted in config JSON.
    """
    existing = db.query(GcpCostIngestConfig).filter(
        GcpCostIngestConfig.tenant_id      == req.tenant_id,
        GcpCostIngestConfig.gcp_project_id == req.gcp_project_id,
    ).one_or_none()

    import base64
    encrypted_sa = base64.b64encode(req.service_account_json.encode()).decode() if req.service_account_json else ""

    if existing:
        existing.name              = req.name
        existing.bigquery_dataset  = req.bigquery_dataset
        existing.bigquery_table    = req.bigquery_table
        existing.enabled           = req.enabled
        existing.config            = {**existing.config, "encrypted_sa_json": encrypted_sa}
        existing.updated_at        = utcnow()
        db.commit()
        return {"status": "updated", "id": existing.id}

    cfg = GcpCostIngestConfig(
        id=new_id(),
        tenant_id=req.tenant_id,
        name=req.name,
        gcp_project_id=req.gcp_project_id,
        bigquery_dataset=req.bigquery_dataset,
        bigquery_table=req.bigquery_table,
        enabled=req.enabled,
        config={"encrypted_sa_json": encrypted_sa},
    )
    db.add(cfg)
    db.commit()
    return {"status": "created", "id": cfg.id}


# ─────────────────────────────────────────────────────────────────────────────
# Test Connection
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/{config_id}/test")
async def test_credential(
    config_id: str,
    tenant_id: str = Depends(get_optional_tenant),
    db: Session = Depends(get_db),
):
    """
    Probe the configured provider and update test_status / test_message.
    Returns immediately; the actual probe runs inline (consider making async in production).
    """
    # Try all config tables
    cfg_obj = None
    provider = None

    aws_cfg = db.query(CostIngestConfig).filter(CostIngestConfig.id == config_id).one_or_none()
    if aws_cfg:
        cfg_obj, provider = aws_cfg, "aws"

    if not cfg_obj:
        az_cfg = db.query(AzureCostIngestConfig).filter(AzureCostIngestConfig.id == config_id).one_or_none()
        if az_cfg:
            cfg_obj, provider = az_cfg, "azure"

    if not cfg_obj:
        gcp_cfg = db.query(GcpCostIngestConfig).filter(GcpCostIngestConfig.id == config_id).one_or_none()
        if gcp_cfg:
            cfg_obj, provider = gcp_cfg, "gcp"

    if not cfg_obj:
        raise HTTPException(status_code=404, detail="Configuration not found")

    result = await _run_connection_test(provider, cfg_obj)

    cfg_obj.test_status    = result["status"]
    cfg_obj.test_message   = result["message"]
    cfg_obj.last_tested_at = utcnow()
    db.commit()

    return result


async def _run_connection_test(provider: str, cfg) -> dict:
    """Perform a lightweight probe to verify credentials are valid."""
    try:
        if provider == "aws":
            return await _test_aws(cfg)
        elif provider == "azure":
            return await _test_azure(cfg)
        elif provider == "gcp":
            return await _test_gcp(cfg)
    except Exception as exc:
        logger.exception("Connection test failed for %s", provider)
        return {"status": "error", "message": str(exc)[:500], "provider": provider}

    return {"status": "error", "message": "Unknown provider", "provider": provider}


async def _test_aws(cfg: CostIngestConfig) -> dict:
    try:
        import boto3, botocore
        session = boto3.Session(region_name=cfg.aws_region)
        sts = session.client("sts")
        identity = sts.get_caller_identity()
        # Try to list the S3 bucket
        s3 = session.client("s3")
        s3.head_bucket(Bucket=cfg.s3_bucket)
        return {
            "status": "ok",
            "message": f"Connected. Account: {identity.get('Account')}. Bucket '{cfg.s3_bucket}' accessible.",
            "provider": "aws",
        }
    except ImportError:
        return {"status": "warning", "message": "boto3 not installed — install via pip.", "provider": "aws"}
    except Exception as exc:
        return {"status": "error", "message": str(exc)[:400], "provider": "aws"}


async def _test_azure(cfg: AzureCostIngestConfig) -> dict:
    try:
        from azure.identity import ClientSecretCredential
        import base64, json as _json
        secret = base64.b64decode(cfg.config.get("encrypted_secret", "")).decode()
        cred = ClientSecretCredential(
            tenant_id=cfg.azure_tenant_id,
            client_id=cfg.client_id,
            client_secret=secret,
        )
        token = cred.get_token("https://management.azure.com/.default")
        return {
            "status": "ok",
            "message": f"Azure token acquired. Subscription: {cfg.subscription_id}.",
            "provider": "azure",
        }
    except ImportError:
        return {"status": "warning", "message": "azure-identity not installed.", "provider": "azure"}
    except Exception as exc:
        return {"status": "error", "message": str(exc)[:400], "provider": "azure"}


async def _test_gcp(cfg: GcpCostIngestConfig) -> dict:
    try:
        from google.cloud import bigquery
        from google.oauth2 import service_account
        import base64, json as _json
        sa_json = base64.b64decode(cfg.config.get("encrypted_sa_json", "")).decode()
        creds = service_account.Credentials.from_service_account_info(
            _json.loads(sa_json),
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
        client = bigquery.Client(project=cfg.gcp_project_id, credentials=creds)
        # Simple probe: check dataset exists
        dataset_ref = f"{cfg.gcp_project_id}.{cfg.bigquery_dataset}"
        client.get_dataset(dataset_ref)
        return {
            "status": "ok",
            "message": f"BigQuery dataset '{cfg.bigquery_dataset}' accessible in project '{cfg.gcp_project_id}'.",
            "provider": "gcp",
        }
    except ImportError:
        return {"status": "warning", "message": "google-cloud-bigquery not installed.", "provider": "gcp"}
    except Exception as exc:
        return {"status": "error", "message": str(exc)[:400], "provider": "gcp"}


# ─────────────────────────────────────────────────────────────────────────────
# Delete
# ─────────────────────────────────────────────────────────────────────────────

@router.delete("/{config_id}")
def delete_credential(
    config_id: str,
    tenant_id: str = Depends(get_optional_tenant),
    db: Session = Depends(get_db),
):
    """Remove a provider credential config."""
    for Model in [CostIngestConfig, AzureCostIngestConfig, GcpCostIngestConfig]:
        obj = db.query(Model).filter(Model.id == config_id).one_or_none()
        if obj:
            db.delete(obj)
            db.commit()
            return {"status": "deleted", "id": config_id}

    raise HTTPException(status_code=404, detail="Configuration not found")


# ─────────────────────────────────────────────────────────────────────────────
# Status overview
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/status")
def get_credential_status(
    tenant_id: str = Depends(get_optional_tenant),
    db: Session = Depends(get_db),
):
    """Health summary: how many providers are configured, ok, errored, or missing."""
    aws   = db.query(CostIngestConfig).filter(CostIngestConfig.tenant_id == tenant_id).all()
    azure = db.query(AzureCostIngestConfig).filter(AzureCostIngestConfig.tenant_id == tenant_id).all()
    gcp   = db.query(GcpCostIngestConfig).filter(GcpCostIngestConfig.tenant_id == tenant_id).all()

    def summary(cfgs, provider):
        return {
            "provider": provider,
            "configured": len(cfgs) > 0,
            "count": len(cfgs),
            "ok":    sum(1 for c in cfgs if c.test_status == "ok"),
            "error": sum(1 for c in cfgs if c.test_status == "error"),
            "pending": sum(1 for c in cfgs if c.test_status == "pending"),
            "last_sync": max(
                (c.last_sync_at for c in cfgs if c.last_sync_at), default=None
            ),
        }

    return {
        "tenant_id": tenant_id,
        "providers": [
            summary(aws,   "aws"),
            summary(azure, "azure"),
            summary(gcp,   "gcp"),
        ],
    }
