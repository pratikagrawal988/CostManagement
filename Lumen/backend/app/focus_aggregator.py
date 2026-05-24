"""
FOCUS → CostAggregation rollup engine.

Reads focus_cost rows (both cloud infra and AI) and upserts into cost_aggregations
for fast dashboard queries. Groups by sub_account_id so team-level granularity is
preserved without violating the unique constraint on the aggregations table.

Unique constraint on cost_aggregations:
  (tenant_id, date, account_id, service, category, region, ai_type, ai_subtype)

We use sub_account_id as the aggregation account_id so that per-team rows
(aws-sub-platform, aws-sub-product, …) don't collide.

Usage:
    from .focus_aggregator import build_aggregations_from_focus
    result = build_aggregations_from_focus(db, tenant_id)
"""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from .models import CostAggregation, FocusCost, new_id, utcnow

logger = logging.getLogger(__name__)

_BATCH = 5_000   # upsert chunk size


def build_aggregations_from_focus(
    db: Session,
    tenant_id: str = "tenant-demo",
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    """
    Idempotent rollup: groups focus_cost → upserts cost_aggregations.

    Returns summary dict with counts.
    """
    logger.info("Building cost aggregations for tenant=%s", tenant_id)

    # ── 1. Pull relevant focus_cost rows ─────────────────────────────────────
    query = db.query(FocusCost).filter(FocusCost.tenant_id == tenant_id)
    if start_date:
        query = query.filter(FocusCost.billing_period_start >= start_date)
    if end_date:
        query = query.filter(FocusCost.billing_period_start <= end_date)

    # Aggregate in Python to avoid complex SQL across different DB dialects
    # Group key: (date, sub_account_id, provider_name, service_name, service_category,
    #             region_name, x_team, x_environment, x_ai_tier, x_ai_model)
    groups: dict[tuple, dict] = defaultdict(lambda: {
        "total_cost": 0.0,
        "effective_cost": 0.0,
        "list_cost": 0.0,
        "total_usage": 0.0,
        "unit_count": 0,
        "resource_ids": set(),
        "request_count": 0,
        "input_tokens": 0.0,
        "output_tokens": 0.0,
        "provider": "",
        "team": "",
        "environment": "",
    })

    row_count = 0
    for row in query.yield_per(2000):
        date = (row.billing_period_start or "")[:10]   # ensure YYYY-MM-DD
        if not date:
            continue

        key = (
            date,
            row.sub_account_id or row.billing_account_id or "",
            row.service_name or "",
            row.service_category or "",
            row.region_id or row.region_name or "",
            row.x_ai_tier or "",         # maps to ai_type in aggregations
            row.x_ai_model or "",        # maps to ai_subtype
        )

        g = groups[key]
        g["total_cost"]    += float(row.billed_cost or 0)
        g["effective_cost"] += float(row.effective_cost or 0)
        g["list_cost"]     += float(row.list_cost or 0)
        g["total_usage"]   += float(row.usage_quantity or 0)
        g["unit_count"]    += 1
        g["request_count"] += int(row.x_request_count or 0)
        g["input_tokens"]  += float(row.x_input_tokens or 0)
        g["output_tokens"] += float(row.x_output_tokens or 0)
        if row.resource_id:
            g["resource_ids"].add(row.resource_id)
        # Store provider / team / env from first row in group (consistent per sub_account)
        g["provider"]     = row.provider_name or ""
        g["team"]         = row.x_team or ""
        g["environment"]  = row.x_environment or ""
        row_count += 1

    if not groups:
        logger.info("No focus_cost rows found for tenant=%s", tenant_id)
        return {"status": "skipped", "reason": "no_focus_cost_rows", "focus_rows": 0, "aggregations": 0}

    # ── 2. Upsert into cost_aggregations ─────────────────────────────────────
    upserted = 0
    inserted = 0
    updated  = 0
    batch_items = list(groups.items())

    for chunk_start in range(0, len(batch_items), _BATCH):
        chunk = batch_items[chunk_start : chunk_start + _BATCH]

        for key, g in chunk:
            (date, account_id, service, category, region, ai_type, ai_subtype) = key

            existing = (
                db.query(CostAggregation)
                .filter(
                    CostAggregation.tenant_id  == tenant_id,
                    CostAggregation.date        == date,
                    CostAggregation.account_id  == account_id,
                    CostAggregation.service     == service,
                    CostAggregation.category    == category,
                    CostAggregation.region      == region,
                    CostAggregation.ai_type     == ai_type,
                    CostAggregation.ai_subtype  == ai_subtype,
                )
                .one_or_none()
            )

            if existing:
                existing.total_cost     = round(g["total_cost"], 6)
                existing.effective_cost = round(g["effective_cost"], 6)
                existing.list_cost      = round(g["list_cost"], 6)
                existing.total_usage    = round(g["total_usage"], 4)
                existing.unit_count     = g["unit_count"]
                existing.resource_count = len(g["resource_ids"])
                existing.request_count  = g["request_count"]
                existing.input_tokens   = round(g["input_tokens"], 0)
                existing.output_tokens  = round(g["output_tokens"], 0)
                existing.provider       = g["provider"]
                existing.team           = g["team"]
                existing.environment    = g["environment"]
                db.add(existing)
                updated += 1
            else:
                db.add(CostAggregation(
                    id             = new_id(),
                    tenant_id      = tenant_id,
                    date           = date,
                    account_id     = account_id,
                    provider       = g["provider"],
                    service        = service,
                    category       = category,
                    subcategory    = "",
                    region         = region,
                    team           = g["team"],
                    environment    = g["environment"],
                    ai_type        = ai_type,
                    ai_subtype     = ai_subtype,
                    total_cost     = round(g["total_cost"], 6),
                    effective_cost = round(g["effective_cost"], 6),
                    list_cost      = round(g["list_cost"], 6),
                    total_usage    = round(g["total_usage"], 4),
                    unit_count     = g["unit_count"],
                    resource_count = len(g["resource_ids"]),
                    request_count  = g["request_count"],
                    input_tokens   = round(g["input_tokens"], 0),
                    output_tokens  = round(g["output_tokens"], 0),
                ))
                inserted += 1

            upserted += 1

        db.flush()

    db.commit()
    logger.info(
        "Aggregation complete: tenant=%s focus_rows=%d groups=%d inserted=%d updated=%d",
        tenant_id, row_count, len(groups), inserted, updated,
    )
    return {
        "status":      "ok",
        "focus_rows":  row_count,
        "groups":      len(groups),
        "inserted":    inserted,
        "updated":     updated,
        "total":       upserted,
    }
