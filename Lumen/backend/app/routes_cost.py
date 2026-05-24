"""
REST API endpoints for cost data retrieval, aggregation, and export.

Endpoints:
- GET /api/cost/daily - Daily cost summaries by service/category/region
- GET /api/cost/summary - Tenant-wide cost summary
- POST /api/focus/export - Export FOCUS-normalized data as CSV
- GET /api/ai-services - AI service costs by model/tier
- GET /api/cost/ingest-config - List ingest configurations
- POST /api/cost/ingest-config - Create ingest configuration
- PATCH /api/cost/ingest-config/{id} - Update configuration
- GET /api/cost/status - Job run history and status
"""

from datetime import datetime, timedelta
from typing import Optional
import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_

from .auth import get_optional_tenant
from .database import SessionLocal, get_db
from .models import (
    CostAggregation, CostDetail, CostIngestConfig, FocusCost,
    JobRun, utcnow, new_id
)

router = APIRouter(prefix="/api/cost", tags=["cost"])


def get_db() -> Session:
    """Dependency injection for database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ============================================================================
# Cost Daily Summaries
# ============================================================================

@router.get("/daily")
def get_daily_costs(
    tenant_id: str = Depends(get_optional_tenant),
    start_date: str = Query(None, description="YYYY-MM-DD"),
    end_date: str = Query(None, description="YYYY-MM-DD"),
    service: Optional[str] = Query(None, description="Filter by service"),
    category: Optional[str] = Query(None, description="Filter by category"),
    region: Optional[str] = Query(None, description="Filter by region"),
    db: Session = Depends(get_db),
):
    """
    Get daily cost aggregations by service/category/region.

    Returns pre-computed aggregations for dashboard performance.
    """
    query = db.query(CostAggregation).filter(
        CostAggregation.tenant_id == tenant_id
    )

    if start_date:
        query = query.filter(CostAggregation.date >= start_date)
    if end_date:
        query = query.filter(CostAggregation.date <= end_date)
    if service:
        query = query.filter(CostAggregation.service == service)
    if category:
        query = query.filter(CostAggregation.category == category)
    if region:
        query = query.filter(CostAggregation.region == region)

    results = query.order_by(
        CostAggregation.date.desc(),
        CostAggregation.service,
        CostAggregation.category,
    ).all()

    return {
        "tenant_id": tenant_id,
        "count": len(results),
        "data": [
            {
                "date": r.date,
                "account_id": r.account_id,
                "service": r.service,
                "category": r.category,
                "subcategory": r.subcategory,
                "region": r.region,
                "ai_type": r.ai_type,
                "ai_subtype": r.ai_subtype,
                "total_cost": float(r.total_cost),
                "total_usage": float(r.total_usage),
                "unit_count": r.unit_count,
                "resource_count": r.resource_count,
            }
            for r in results
        ],
    }


# ============================================================================
# Cost Summary
# ============================================================================

@router.get("/summary")
def get_cost_summary(
    tenant_id: str = Depends(get_optional_tenant),
    days: int = Query(30, description="Last N days"),
    db: Session = Depends(get_db),
):
    """
    Get tenant-wide cost summary for the last N days.

    Aggregates across all services, regions, and categories.
    """
    cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    # Top services by cost
    top_services = db.query(
        CostAggregation.service,
        func.sum(CostAggregation.total_cost).label("total_cost"),
        func.count().label("days"),
    ).filter(
        CostAggregation.tenant_id == tenant_id,
        CostAggregation.date >= cutoff_date,
    ).group_by(
        CostAggregation.service,
    ).order_by(
        func.sum(CostAggregation.total_cost).desc(),
    ).limit(10).all()

    # Top categories by cost
    top_categories = db.query(
        CostAggregation.category,
        func.sum(CostAggregation.total_cost).label("total_cost"),
        func.count().label("days"),
    ).filter(
        CostAggregation.tenant_id == tenant_id,
        CostAggregation.date >= cutoff_date,
    ).group_by(
        CostAggregation.category,
    ).order_by(
        func.sum(CostAggregation.total_cost).desc(),
    ).limit(10).all()

    # Total cost
    total = db.query(
        func.sum(CostAggregation.total_cost).label("total"),
    ).filter(
        CostAggregation.tenant_id == tenant_id,
        CostAggregation.date >= cutoff_date,
    ).scalar() or 0

    # Cost by account
    by_account = db.query(
        CostAggregation.account_id,
        func.sum(CostAggregation.total_cost).label("total_cost"),
    ).filter(
        CostAggregation.tenant_id == tenant_id,
        CostAggregation.date >= cutoff_date,
    ).group_by(
        CostAggregation.account_id,
    ).all()

    return {
        "tenant_id": tenant_id,
        "period_days": days,
        "total_cost": float(total),
        "average_daily_cost": float(total / days) if days > 0 else 0,
        "top_services": [
            {"service": s[0], "cost": float(s[1]), "days": s[2]}
            for s in top_services
        ],
        "top_categories": [
            {"category": c[0], "cost": float(c[1]), "days": c[2]}
            for c in top_categories
        ],
        "by_account": [
            {"account_id": a[0], "cost": float(a[1])}
            for a in by_account
        ],
    }


# ============================================================================
# FOCUS Export
# ============================================================================

@router.post("/focus/export")
def export_focus_csv(
    tenant_id: str = Depends(get_optional_tenant),
    start_date: str = Query(None, description="YYYY-MM-DD"),
    end_date: str = Query(None, description="YYYY-MM-DD"),
    db: Session = Depends(get_db),
):
    """
    Export FOCUS-normalized cost data as CSV.

    Returns CSV file in FOCUS specification format.
    """
    query = db.query(FocusCost).filter(FocusCost.tenant_id == tenant_id)

    if start_date:
        query = query.filter(FocusCost.billing_period_start >= start_date)
    if end_date:
        query = query.filter(FocusCost.billing_period_start <= end_date)

    results = query.order_by(FocusCost.billing_period_start.desc()).all()

    # Generate CSV
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=[
            "BillingPeriodStart",
            "InvoiceIssuer",
            "ServiceName",
            "ServiceCategory",
            "SKU",
            "Region",
            "UsageQuantity",
            "UsageUnit",
            "UnitPrice",
            "BilledCost",
            "Currency",
            "ResourceId",
            "CostCategory",
            "ChargebackEntity",
            "Tags",
        ],
    )
    writer.writeheader()

    for row in results:
        writer.writerow({
            "BillingPeriodStart": row.billing_period_start,
            "InvoiceIssuer": row.invoice_issuer,
            "ServiceName": row.service_name,
            "ServiceCategory": row.service_category,
            "SKU": row.sku,
            "Region": row.region,
            "UsageQuantity": row.usage_quantity,
            "UsageUnit": row.usage_unit,
            "UnitPrice": row.unit_price,
            "BilledCost": row.billed_cost,
            "Currency": row.currency,
            "ResourceId": row.resource_id,
            "CostCategory": row.cost_category,
            "ChargebackEntity": row.chargeback_entity,
            "Tags": row.tags,
        })

    return {
        "status": "success",
        "tenant_id": tenant_id,
        "record_count": len(results),
        "csv_content": output.getvalue(),
        "filename": f"focus-export-{tenant_id}-{datetime.now().strftime('%Y%m%d')}.csv",
    }


# ============================================================================
# AI Services
# ============================================================================

@router.get("/ai-services")
def get_ai_services(
    tenant_id: str = Depends(get_optional_tenant),
    start_date: str = Query(None, description="YYYY-MM-DD"),
    end_date: str = Query(None, description="YYYY-MM-DD"),
    ai_type: Optional[str] = Query(None, description="Filter by AI type (LLM, Vision, etc.)"),
    ai_subtype: Optional[str] = Query(None, description="Filter by AI subtype (Claude, Gemini, etc.)"),
    db: Session = Depends(get_db),
):
    """
    Get AI service costs by model and tier.

    Includes input tokens, output tokens, cache reads, and per-request costs.
    """
    query = db.query(FocusCost).filter(FocusCost.tenant_id == tenant_id)

    if start_date:
        query = query.filter(FocusCost.billing_period_start >= start_date)
    if end_date:
        query = query.filter(FocusCost.billing_period_start <= end_date)

    # Filter for AI services (commonly Bedrock, SageMaker)
    query = query.filter(FocusCost.service_category == "AI/ML")

    results = query.all()

    # Group by model/tier
    grouped = {}
    for row in results:
        key = f"{row.service_name}:{row.usage_unit}"
        if key not in grouped:
            grouped[key] = {
                "service": row.service_name,
                "unit": row.usage_unit,
                "total_cost": 0,
                "total_usage": 0,
                "periods": 0,
            }
        grouped[key]["total_cost"] += float(row.billed_cost)
        grouped[key]["total_usage"] += float(row.usage_quantity)
        grouped[key]["periods"] += 1

    if ai_type:
        results = [r for r in results if r.service_name == ai_type]

    return {
        "tenant_id": tenant_id,
        "ai_services": [
            {
                "service": v["service"],
                "usage_unit": v["unit"],
                "total_cost": v["total_cost"],
                "total_usage": v["total_usage"],
                "average_unit_price": v["total_cost"] / v["total_usage"] if v["total_usage"] > 0 else 0,
                "billing_periods": v["periods"],
            }
            for v in grouped.values()
        ],
    }


# ============================================================================
# Ingest Configuration
# ============================================================================

@router.get("/ingest-config")
def list_ingest_configs(
    tenant_id: str = Depends(get_optional_tenant),
    db: Session = Depends(get_db),
):
    """
    List all cost ingest configurations.

    Returns S3 bucket, role ARN, and last test status for each config.
    """
    query = db.query(CostIngestConfig)

    if tenant_id:
        query = query.filter(CostIngestConfig.tenant_id == tenant_id)

    configs = query.all()

    return {
        "count": len(configs),
        "configs": [
            {
                "id": c.id,
                "tenant_id": c.tenant_id,
                "s3_bucket": c.s3_bucket,
                "s3_prefix": c.s3_prefix,
                "aws_role_arn": c.aws_role_arn,
                "enabled": c.enabled,
                "last_tested_at": c.last_tested_at.isoformat() if c.last_tested_at else None,
                "test_status": c.test_status,
                "test_message": c.test_message,
                "created_at": c.created_at.isoformat(),
            }
            for c in configs
        ],
    }


@router.post("/ingest-config")
def create_ingest_config(
    tenant_id: str = Depends(get_optional_tenant),
    s3_bucket: str = Query(...),
    s3_prefix: str = Query(...),
    aws_role_arn: str = Query(...),
    aws_external_id: str = Query(...),
    enabled: bool = Query(True),
    db: Session = Depends(get_db),
):
    """
    Create a new cost ingest configuration.

    Configures S3 access for CUR ingestion via cross-account IAM role.
    """
    # Check for duplicate
    existing = db.query(CostIngestConfig).filter(
        CostIngestConfig.tenant_id == tenant_id,
        CostIngestConfig.s3_bucket == s3_bucket,
    ).one_or_none()

    if existing:
        raise HTTPException(status_code=409, detail="Configuration already exists")

    config = CostIngestConfig(
        id=new_id(),
        tenant_id=tenant_id,
        s3_bucket=s3_bucket,
        s3_prefix=s3_prefix,
        aws_role_arn=aws_role_arn,
        aws_external_id=aws_external_id,
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
        "s3_bucket": config.s3_bucket,
    }


@router.patch("/ingest-config/{config_id}")
def update_ingest_config(
    config_id: str,
    s3_bucket: Optional[str] = Query(None),
    s3_prefix: Optional[str] = Query(None),
    aws_role_arn: Optional[str] = Query(None),
    aws_external_id: Optional[str] = Query(None),
    enabled: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Update an ingest configuration.

    Only provided fields are updated; others remain unchanged.
    """
    config = db.query(CostIngestConfig).filter(
        CostIngestConfig.id == config_id
    ).one_or_none()

    if not config:
        raise HTTPException(status_code=404, detail="Configuration not found")

    if s3_bucket:
        config.s3_bucket = s3_bucket
    if s3_prefix:
        config.s3_prefix = s3_prefix
    if aws_role_arn:
        config.aws_role_arn = aws_role_arn
    if aws_external_id:
        config.aws_external_id = aws_external_id
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


# ============================================================================
# Job Status
# ============================================================================

@router.get("/status")
def get_cost_job_status(
    job_name: Optional[str] = Query(None, description="Filter by job name"),
    limit: int = Query(20, description="Max results"),
    db: Session = Depends(get_db),
):
    """
    Get job run history and status for cost ingestion and transform jobs.

    Shows execution details for cost_ingest, focus_transform, etc.
    """
    query = db.query(JobRun).filter(
        JobRun.job_name.in_(["cost_ingest", "focus_transform"])
    )

    if job_name:
        query = query.filter(JobRun.job_name == job_name)

    runs = query.order_by(JobRun.started_at.desc()).limit(limit).all()

    return {
        "total": len(runs),
        "job_runs": [
            {
                "id": r.id,
                "job_name": r.job_name,
                "status": r.status,
                "started_at": r.started_at.isoformat(),
                "finished_at": r.finished_at.isoformat() if r.finished_at else None,
                "duration_seconds": (r.finished_at - r.started_at).total_seconds() if r.finished_at else None,
                "records_processed": r.records_processed,
                "details": r.details,
            }
            for r in runs
        ],
    }
