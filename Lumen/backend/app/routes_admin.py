"""
Admin / operational endpoints.

Endpoints:
- POST /api/admin/seed-csp              — Generate CSP mock data (30 or N days, force re-seed)
- POST /api/admin/seed-ai               — Generate AI demo data (90 days, force re-seed)
- POST /api/admin/rebuild-aggregations  — Re-run focus → cost_aggregations rollup
- GET  /api/admin/seed-status           — Check seed data counts
"""

import logging

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .auth import get_optional_tenant
from .database import get_db
from .focus_aggregator import build_aggregations_from_focus
from .models import CostAggregation, FocusCost

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.post("/seed-csp")
def seed_csp(
    tenant_id: str = Depends(get_optional_tenant),
    days: int      = Query(default=30,   ge=1, le=365, description="Trailing days of data to generate"),
    force: bool    = Query(default=True,               description="Delete existing CSP rows first"),
    db: Session    = Depends(get_db),
):
    """
    Generate (or re-generate) CSP mock data for AWS, Azure, and GCP.

    - days=30  → produces the last 30 days of realistic billing rows
    - force=true (default) → clears any existing CSP rows before seeding
    - After seeding, automatically rebuilds cost_aggregations

    Approximate row counts per day: 3 CSPs × 12 services × 5 teams = 180 rows/day
    For 30 days that's ~5 400 focus_cost rows + ~1 800 aggregation rows.
    """
    from .seed_focus_csp import seed_csp_focus_data

    logger.info("seed-csp: tenant=%s days=%d force=%s", tenant_id, days, force)

    seed_result = seed_csp_focus_data(db, tenant_id=tenant_id, days=days, force=force)
    logger.info("seed-csp seeder: %s", seed_result)

    # Rebuild aggregations covering only the newly seeded window
    from datetime import date, timedelta
    end_date   = date.today().isoformat()
    start_date = (date.today() - timedelta(days=days - 1)).isoformat()
    agg_result = build_aggregations_from_focus(
        db, tenant_id=tenant_id, start_date=start_date, end_date=end_date
    )
    logger.info("seed-csp aggregator: %s", agg_result)

    return {
        "tenant_id":   tenant_id,
        "days":        days,
        "force":       force,
        "seed":        seed_result,
        "aggregations": agg_result,
    }


@router.post("/seed-ai")
def seed_ai(
    tenant_id: str = Depends(get_optional_tenant),
    force: bool    = Query(default=False, description="Delete existing AI rows and re-seed"),
    db: Session    = Depends(get_db),
):
    """
    Seed 90 days of realistic AI cost data across Anthropic, OpenAI, AWS Bedrock,
    Google Vertex, and Cohere. Also seeds SaaS tool allocations and app attributions.

    - force=false (default): skips if AI rows already exist
    - force=true: deletes existing AI focus_cost rows before re-seeding
    """
    from .seed_ai_demo import seed_ai_demo_data

    if force:
        deleted = (
            db.query(FocusCost)
            .filter(FocusCost.tenant_id == tenant_id)
            .filter(FocusCost.x_ai_vendor != "")
            .delete(synchronize_session=False)
        )
        db.commit()
        logger.info("seed-ai: deleted %d existing AI rows", deleted)

    seed_result = seed_ai_demo_data(db, tenant_id=tenant_id)
    logger.info("seed-ai: %s", seed_result)

    # Rebuild aggregations for AI rows
    agg_result = build_aggregations_from_focus(db, tenant_id=tenant_id)
    logger.info("seed-ai aggregator: %s", agg_result)

    return {
        "tenant_id":    tenant_id,
        "force":        force,
        "seed":         seed_result,
        "aggregations": agg_result,
    }


@router.post("/rebuild-aggregations")
def rebuild_aggregations(
    tenant_id: str = Depends(get_optional_tenant),
    start_date: str = Query(None, description="YYYY-MM-DD — limit rebuild to this window"),
    end_date: str   = Query(None, description="YYYY-MM-DD — limit rebuild to this window"),
    db: Session = Depends(get_db),
):
    """
    Re-compute cost_aggregations from focus_cost rows.

    Safe to run at any time — existing rows are updated in-place, new rows are
    inserted. Useful after importing new FOCUS data or re-seeding mock data.
    """
    result = build_aggregations_from_focus(
        db,
        tenant_id  = tenant_id,
        start_date = start_date,
        end_date   = end_date,
    )
    return {"tenant_id": tenant_id, **result}


@router.get("/seed-status")
def seed_status(
    tenant_id: str = Depends(get_optional_tenant),
    db: Session = Depends(get_db),
):
    """Return row counts for key tables to verify seed data is present."""
    focus_total = db.query(FocusCost).filter(FocusCost.tenant_id == tenant_id).count()
    focus_csp   = (
        db.query(FocusCost)
        .filter(FocusCost.tenant_id == tenant_id, FocusCost.x_ai_vendor == "")
        .count()
    )
    focus_ai    = focus_total - focus_csp
    agg_total   = (
        db.query(CostAggregation)
        .filter(CostAggregation.tenant_id == tenant_id)
        .count()
    )
    return {
        "tenant_id":            tenant_id,
        "focus_cost_total":     focus_total,
        "focus_cost_csp":       focus_csp,
        "focus_cost_ai":        focus_ai,
        "cost_aggregations":    agg_total,
    }
