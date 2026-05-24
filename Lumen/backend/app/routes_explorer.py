"""
Cloud Cost Explorer routes — interactive cost drill-down (Screen 02).

Endpoints:
  GET /api/explorer/summary        — total spend + top-N breakdown for a dimension
  GET /api/explorer/timeseries     — daily spend grouped by dimension (stacked area)
  GET /api/explorer/breakdown      — paginated table with sort + filter
  GET /api/explorer/filters        — available filter values (providers, services, teams, regions, envs)
  GET /api/explorer/resource-detail — per-resource cost rows (finest granularity)

Dimensions: provider | service | service_category | region | team | environment | app | cost_center | model
Date range:  start_date / end_date (YYYY-MM-DD), default = rolling 30 days
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from .auth import get_optional_tenant
from .database import get_db
from .models import FocusCost

router = APIRouter(prefix="/api/explorer", tags=["explorer"])


# ── Dimension map ──────────────────────────────────────────────────────────────

_DIM_COLS: dict[str, Any] = {
    "provider":         FocusCost.provider_name,
    "service":          FocusCost.service_name,
    "service_category": FocusCost.service_category,
    "region":           FocusCost.region_name,
    "team":             FocusCost.x_team,
    "environment":      FocusCost.x_environment,
    "app":              FocusCost.x_app_id,
    "cost_center":      FocusCost.x_cost_center,
    "model":            FocusCost.x_ai_model,
}


def _resolve_dim(dimension: str):
    return _DIM_COLS.get(dimension, FocusCost.service_name)


# ── Date helpers ───────────────────────────────────────────────────────────────

def _default_range(days: int = 30) -> tuple[str, str]:
    today = date.today()
    return (today - timedelta(days=days - 1)).isoformat(), today.isoformat()


def _prior_window(start: str, end: str) -> tuple[str, str]:
    s = date.fromisoformat(start)
    e = date.fromisoformat(end)
    delta = (e - s) + timedelta(days=1)
    return (s - delta).isoformat(), (s - timedelta(days=1)).isoformat()


# ── Base query helper ─────────────────────────────────────────────────────────

def _base(
    db:            Session,
    tenant_id:     str,
    start:         str,
    end:           str,
    provider:      str | None,
    service:       str | None,
    team:          str | None,
    region:        str | None,
    environment:   str | None,
    ai_only:       bool,
):
    q = (
        db.query(FocusCost)
        .filter(
            FocusCost.tenant_id            == tenant_id,
            FocusCost.billing_period_start >= start,
            FocusCost.billing_period_start <= end,
        )
    )
    if provider:    q = q.filter(FocusCost.provider_name == provider)
    if service:     q = q.filter(FocusCost.service_name  == service)
    if team:        q = q.filter(FocusCost.x_team        == team)
    if region:      q = q.filter(FocusCost.region_name   == region)
    if environment: q = q.filter(FocusCost.x_environment == environment)
    if ai_only:     q = q.filter(FocusCost.x_ai_vendor   != "")
    return q


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/summary")
def explorer_summary(
    dimension:   str       = Query(default="provider"),
    start_date:  str | None = Query(default=None),
    end_date:    str | None = Query(default=None),
    provider:    str | None = Query(default=None),
    service:     str | None = Query(default=None),
    team:        str | None = Query(default=None),
    region:      str | None = Query(default=None),
    environment: str | None = Query(default=None),
    ai_only:     bool       = Query(default=False),
    top_n:       int        = Query(default=10, ge=3, le=50),
    db:          Session    = Depends(get_db),
    tenant_id:   str        = Depends(get_optional_tenant),
):
    """
    Returns:
      - total_cost for the period
      - breakdown: top-N rows [{name, cost, pct, prior_cost, delta_pct, request_count}]
      - period metadata
    """
    start, end = (start_date, end_date) if start_date else _default_range(30)
    prior_s, prior_e = _prior_window(start, end)
    dim_col = _resolve_dim(dimension)

    def _agg(s, e):
        return (
            _base(db, tenant_id, s, e, provider, service, team, region, environment, ai_only)
            .with_entities(
                dim_col.label("name"),
                func.sum(FocusCost.effective_cost).label("cost"),
                func.sum(FocusCost.x_request_count).label("requests"),
                func.sum(FocusCost.x_input_tokens + FocusCost.x_output_tokens).label("tokens"),
            )
            .group_by(dim_col)
            .order_by(func.sum(FocusCost.effective_cost).desc())
            .limit(top_n + 5)
            .all()
        )

    cur_rows   = _agg(start, end)
    prior_rows = _agg(prior_s, prior_e)
    prior_map  = {r.name: float(r.cost or 0) for r in prior_rows}

    total_cost = sum(float(r.cost or 0) for r in cur_rows)

    breakdown = []
    for r in cur_rows[:top_n]:
        cur_c  = float(r.cost or 0)
        prior_c = prior_map.get(r.name, 0)
        breakdown.append({
            "name":      r.name or "Unknown",
            "cost":      round(cur_c, 2),
            "pct":       round(cur_c / total_cost * 100, 1) if total_cost else 0,
            "prior_cost": round(prior_c, 2),
            "delta_pct": round((cur_c - prior_c) / prior_c * 100, 1) if prior_c else None,
            "requests":  int(r.requests or 0),
            "tokens":    int(r.tokens or 0),
        })

    return {
        "total_cost":  round(total_cost, 2),
        "breakdown":   breakdown,
        "dimension":   dimension,
        "start":       start,
        "end":         end,
        "prior_start": prior_s,
        "prior_end":   prior_e,
    }


@router.get("/timeseries")
def explorer_timeseries(
    dimension:   str       = Query(default="provider"),
    start_date:  str | None = Query(default=None),
    end_date:    str | None = Query(default=None),
    provider:    str | None = Query(default=None),
    service:     str | None = Query(default=None),
    team:        str | None = Query(default=None),
    region:      str | None = Query(default=None),
    environment: str | None = Query(default=None),
    ai_only:     bool       = Query(default=False),
    granularity: str        = Query(default="day"),   # day | week
    db:          Session    = Depends(get_db),
    tenant_id:   str        = Depends(get_optional_tenant),
):
    start, end = (start_date, end_date) if start_date else _default_range(30)
    dim_col    = _resolve_dim(dimension)

    rows = (
        _base(db, tenant_id, start, end, provider, service, team, region, environment, ai_only)
        .with_entities(
            FocusCost.billing_period_start.label("date"),
            dim_col.label("dim"),
            func.sum(FocusCost.effective_cost).label("cost"),
        )
        .group_by(FocusCost.billing_period_start, dim_col)
        .all()
    )

    # Pivot to {date: {dim: cost}}
    by_date: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    dims: set[str] = set()
    for r in rows:
        d   = str(r.date)[:10]
        dim = r.dim or "Unknown"
        by_date[d][dim] += float(r.cost or 0)
        dims.add(dim)

    dims_list    = sorted(dims)
    sorted_dates = sorted(by_date.keys())

    series = [
        {"date": d, **{dim: round(by_date[d].get(dim, 0), 4) for dim in dims_list}}
        for d in sorted_dates
    ]

    return {"series": series, "dimensions": dims_list, "granularity": granularity}


@router.get("/breakdown")
def explorer_breakdown(
    dimension:   str       = Query(default="service"),
    group_by2:   str | None = Query(default=None),    # optional second grouping (e.g. region within service)
    start_date:  str | None = Query(default=None),
    end_date:    str | None = Query(default=None),
    provider:    str | None = Query(default=None),
    service:     str | None = Query(default=None),
    team:        str | None = Query(default=None),
    region:      str | None = Query(default=None),
    environment: str | None = Query(default=None),
    ai_only:     bool       = Query(default=False),
    sort_by:     str        = Query(default="cost"),  # cost | name | delta
    page:        int        = Query(default=1, ge=1),
    page_size:   int        = Query(default=25, ge=5, le=100),
    db:          Session    = Depends(get_db),
    tenant_id:   str        = Depends(get_optional_tenant),
):
    start, end   = (start_date, end_date) if start_date else _default_range(30)
    prior_s, prior_e = _prior_window(start, end)
    dim_col      = _resolve_dim(dimension)
    dim2_col     = _resolve_dim(group_by2) if group_by2 else None

    group_cols = [dim_col] + ([dim2_col] if dim2_col else [])

    def _fetch(s, e):
        q = (
            _base(db, tenant_id, s, e, provider, service, team, region, environment, ai_only)
            .with_entities(
                *[c.label(f"dim{i}") for i, c in enumerate(group_cols)],
                func.sum(FocusCost.effective_cost).label("cost"),
                func.sum(FocusCost.billed_cost).label("billed"),
                func.sum(FocusCost.list_cost).label("list"),
                func.sum(FocusCost.x_request_count).label("requests"),
                func.sum(FocusCost.x_input_tokens).label("in_tok"),
                func.sum(FocusCost.x_output_tokens).label("out_tok"),
            )
            .group_by(*group_cols)
        )
        return q.all()

    cur_rows   = _fetch(start, end)
    prior_rows = _fetch(prior_s, prior_e)

    def _key(r):
        return (str(r.dim0 or ""),) + ((str(r.dim1 or ""),) if dim2_col else ())

    prior_map = {_key(r): float(r.cost or 0) for r in prior_rows}
    total     = sum(float(r.cost or 0) for r in cur_rows) or 1

    items = []
    for r in cur_rows:
        k      = _key(r)
        cur_c  = float(r.cost or 0)
        prior_c = prior_map.get(k, 0)
        items.append({
            "name":       r.dim0 or "Unknown",
            **({"group": r.dim1 or "Unknown"} if dim2_col else {}),
            "cost":       round(cur_c, 2),
            "billed":     round(float(r.billed or 0), 2),
            "list_cost":  round(float(r.list or 0), 2),
            "savings":    round(float(r.list or 0) - cur_c, 2),
            "pct":        round(cur_c / total * 100, 1),
            "prior_cost": round(prior_c, 2),
            "delta_pct":  round((cur_c - prior_c) / prior_c * 100, 1) if prior_c else None,
            "requests":   int(r.requests or 0),
            "in_tokens":  int(r.in_tok or 0),
            "out_tokens": int(r.out_tok or 0),
        })

    # Sort
    if sort_by == "name":
        items.sort(key=lambda x: x["name"])
    elif sort_by == "delta":
        items.sort(key=lambda x: abs(x["delta_pct"] or 0), reverse=True)
    else:
        items.sort(key=lambda x: x["cost"], reverse=True)

    # Paginate
    offset     = (page - 1) * page_size
    page_items = items[offset: offset + page_size]

    return {
        "items":       page_items,
        "total_items": len(items),
        "total_cost":  round(total, 2),
        "page":        page,
        "page_size":   page_size,
        "pages":       -(-len(items) // page_size),
    }


@router.get("/filters")
def explorer_filters(
    start_date:  str | None = Query(default=None),
    end_date:    str | None = Query(default=None),
    db:          Session    = Depends(get_db),
    tenant_id:   str        = Depends(get_optional_tenant),
):
    """Returns distinct filter values for the explorer dropdowns."""
    start, end = (start_date, end_date) if start_date else _default_range(30)

    def _distinct(col):
        return [
            r[0] for r in
            db.query(col).filter(
                FocusCost.tenant_id == tenant_id,
                FocusCost.billing_period_start >= start,
                FocusCost.billing_period_start <= end,
                col != "",
                col.isnot(None),
            ).distinct().order_by(col).all()
        ]

    return {
        "providers":    _distinct(FocusCost.provider_name),
        "services":     _distinct(FocusCost.service_name)[:40],
        "categories":   _distinct(FocusCost.service_category),
        "regions":      _distinct(FocusCost.region_name),
        "teams":        _distinct(FocusCost.x_team),
        "environments": _distinct(FocusCost.x_environment),
        "apps":         _distinct(FocusCost.x_app_id),
        "cost_centers": _distinct(FocusCost.x_cost_center),
        "ai_vendors":   _distinct(FocusCost.x_ai_vendor),
    }


@router.get("/resource-detail")
def explorer_resource_detail(
    start_date:  str | None = Query(default=None),
    end_date:    str | None = Query(default=None),
    provider:    str | None = Query(default=None),
    service:     str | None = Query(default=None),
    team:        str | None = Query(default=None),
    region:      str | None = Query(default=None),
    environment: str | None = Query(default=None),
    ai_only:     bool       = Query(default=False),
    page:        int        = Query(default=1, ge=1),
    page_size:   int        = Query(default=50, ge=10, le=200),
    db:          Session    = Depends(get_db),
    tenant_id:   str        = Depends(get_optional_tenant),
):
    """Finest-grain: one row per (resource_id, billing_date)."""
    start, end = (start_date, end_date) if start_date else _default_range(7)

    q = _base(db, tenant_id, start, end, provider, service, team, region, environment, ai_only)

    total = q.count()
    rows  = (
        q.order_by(FocusCost.effective_cost.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = [
        {
            "date":          r.billing_period_start,
            "provider":      r.provider_name,
            "service":       r.service_name,
            "resource_id":   r.resource_id,
            "resource_name": r.resource_name,
            "region":        r.region_name,
            "team":          r.x_team,
            "app":           r.x_app_id,
            "environment":   r.x_environment,
            "effective_cost": round(r.effective_cost, 4),
            "list_cost":     round(r.list_cost, 4),
            "ai_vendor":     r.x_ai_vendor or None,
            "ai_model":      r.x_ai_model  or None,
            "requests":      r.x_request_count,
        }
        for r in rows
    ]

    return {
        "items":       items,
        "total_items": total,
        "page":        page,
        "page_size":   page_size,
        "pages":       -(-total // page_size),
    }
