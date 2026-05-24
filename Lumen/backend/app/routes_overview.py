"""
Executive Overview routes — CFO / VP-Engineering facing dashboard endpoints.

GET /api/overview/kpis          — 6-card strip (MTD spend, MoM%, AI%, top provider, savings opp, anomalies)
GET /api/overview/trend         — 90-day stacked area (by provider)
GET /api/overview/sankey        — provider → service_category → team flow nodes+links
GET /api/overview/top-movers    — biggest cost increases / decreases vs prior period
GET /api/overview/team-chargeback — team spend breakdown with MoM delta
GET /api/overview/ai-insight    — AI-generated commentary blurb (rule-based)
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from .auth import get_optional_tenant
from .database import get_db
from .models import FocusCost, CostAggregation

router = APIRouter(prefix="/api/overview", tags=["overview"])


# ── Helpers ───────────────────────────────────────────────────────────────────

def _period_bounds(offset_months: int = 0):
    """Return (start_iso, end_iso) for a calendar month, offset by N months."""
    today   = date.today()
    # First day of offset month
    month   = today.month - offset_months
    year    = today.year
    while month <= 0:
        month += 12
        year  -= 1
    start = date(year, month, 1)
    # Last day: first day of next month minus 1
    if month == 12:
        end = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        end = date(year, month + 1, 1) - timedelta(days=1)
    return start.isoformat(), end.isoformat()


def _mtd_bounds():
    today = date.today()
    return date(today.year, today.month, 1).isoformat(), today.isoformat()


def _sum_focus(db: Session, tenant_id: str, start: str, end: str) -> float:
    result = (
        db.query(func.sum(FocusCost.effective_cost))
        .filter(
            FocusCost.tenant_id == tenant_id,
            FocusCost.billing_period_start >= start,
            FocusCost.billing_period_start <= end,
        )
        .scalar()
    )
    return float(result or 0)


def _ai_cost(db: Session, tenant_id: str, start: str, end: str) -> float:
    result = (
        db.query(func.sum(FocusCost.effective_cost))
        .filter(
            FocusCost.tenant_id == tenant_id,
            FocusCost.billing_period_start >= start,
            FocusCost.billing_period_start <= end,
            FocusCost.x_ai_vendor != "",
        )
        .scalar()
    )
    return float(result or 0)


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/kpis")
def overview_kpis(
    db:        Session = Depends(get_db),
    tenant_id: str     = Depends(get_optional_tenant),
):
    mtd_start, mtd_end = _mtd_bounds()
    pm_start,  pm_end  = _period_bounds(1)

    mtd_total  = _sum_focus(db, tenant_id, mtd_start, mtd_end)
    pm_total   = _sum_focus(db, tenant_id, pm_start,  pm_end)
    mtd_ai     = _ai_cost(db,  tenant_id, mtd_start, mtd_end)

    mom_pct = round((mtd_total - pm_total) / pm_total * 100, 1) if pm_total else 0
    ai_pct  = round(mtd_ai / mtd_total * 100, 1) if mtd_total else 0

    # Top provider by MTD spend
    top_provider_row = (
        db.query(FocusCost.provider_name, func.sum(FocusCost.effective_cost).label("cost"))
        .filter(
            FocusCost.tenant_id == tenant_id,
            FocusCost.billing_period_start >= mtd_start,
            FocusCost.billing_period_start <= mtd_end,
        )
        .group_by(FocusCost.provider_name)
        .order_by(func.sum(FocusCost.effective_cost).desc())
        .first()
    )
    top_provider = top_provider_row[0] if top_provider_row else "—"

    # Savings opportunity: models with viable swap suggestions
    from .models import ModelSwapSuggestion
    swap_count = (
        db.query(func.count(ModelSwapSuggestion.id))
        .filter(ModelSwapSuggestion.tenant_id == tenant_id)
        .scalar()
    ) or 0

    # Estimated savings from model swaps (sum estimated_monthly_savings)
    swap_savings = (
        db.query(func.sum(ModelSwapSuggestion.estimated_monthly_savings))
        .filter(ModelSwapSuggestion.tenant_id == tenant_id)
        .scalar()
    ) or 0

    return {
        "mtd_total_spend":    round(mtd_total,  2),
        "mtd_ai_spend":       round(mtd_ai,     2),
        "ai_pct_of_total":    ai_pct,
        "mom_change_pct":     mom_pct,
        "top_provider":       top_provider,
        "swap_opportunities": swap_count,
        "swap_savings_est":   round(float(swap_savings), 2),
        "prior_month_total":  round(pm_total, 2),
    }


@router.get("/trend")
def overview_trend(
    days:      int     = Query(default=90, ge=7, le=365),
    group_by:  str     = Query(default="provider"),   # provider | service | team
    db:        Session = Depends(get_db),
    tenant_id: str     = Depends(get_optional_tenant),
):
    today     = date.today()
    start_iso = (today - timedelta(days=days - 1)).isoformat()
    end_iso   = today.isoformat()

    rows = (
        db.query(
            FocusCost.billing_period_start,
            FocusCost.provider_name,
            FocusCost.service_category,
            FocusCost.x_team,
            func.sum(FocusCost.effective_cost).label("cost"),
        )
        .filter(
            FocusCost.tenant_id == tenant_id,
            FocusCost.billing_period_start >= start_iso,
            FocusCost.billing_period_start <= end_iso,
        )
        .group_by(
            FocusCost.billing_period_start,
            FocusCost.provider_name,
            FocusCost.service_category,
            FocusCost.x_team,
        )
        .all()
    )

    # Pivot: date → {dimension: cost}
    by_date: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    dims: set[str] = set()

    for r in rows:
        d = r.billing_period_start[:10]
        if group_by == "service":
            dim = r.service_category or "Other"
        elif group_by == "team":
            dim = r.x_team or "Unknown"
        else:
            dim = r.provider_name or "Unknown"
        by_date[d][dim] += float(r.cost or 0)
        dims.add(dim)

    # Build time-series list
    sorted_dates = sorted(by_date.keys())
    dims_list    = sorted(dims)
    series = [
        {"date": d, **{dim: round(by_date[d].get(dim, 0), 4) for dim in dims_list}}
        for d in sorted_dates
    ]

    return {"series": series, "dimensions": dims_list, "group_by": group_by}


@router.get("/sankey")
def overview_sankey(
    db:        Session = Depends(get_db),
    tenant_id: str     = Depends(get_optional_tenant),
):
    """
    Returns Sankey nodes + links for provider → service_category → team.
    Covers the rolling 30 days.
    """
    today     = date.today()
    start_iso = (today - timedelta(days=30)).isoformat()
    end_iso   = today.isoformat()

    rows = (
        db.query(
            FocusCost.provider_name,
            FocusCost.service_category,
            FocusCost.x_team,
            func.sum(FocusCost.effective_cost).label("cost"),
        )
        .filter(
            FocusCost.tenant_id == tenant_id,
            FocusCost.billing_period_start >= start_iso,
            FocusCost.billing_period_start <= end_iso,
            FocusCost.effective_cost > 0,
        )
        .group_by(
            FocusCost.provider_name,
            FocusCost.service_category,
            FocusCost.x_team,
        )
        .all()
    )

    # Collect unique nodes (prefix type to avoid name clashes)
    node_index: dict[str, int] = {}
    nodes: list[dict] = []

    def get_node(label: str, group: str) -> int:
        key = f"{group}::{label}"
        if key not in node_index:
            node_index[key] = len(nodes)
            nodes.append({"id": len(nodes), "name": label, "group": group})
        return node_index[key]

    links: list[dict] = []
    # Aggregate provider → category
    prov_cat: dict[tuple, float] = defaultdict(float)
    cat_team: dict[tuple, float] = defaultdict(float)

    for r in rows:
        prov = r.provider_name or "Unknown"
        cat  = r.service_category or "Other"
        team = r.x_team or "Unallocated"
        cost = float(r.cost or 0)
        prov_cat[(prov, cat)] += cost
        cat_team[(cat, team)] += cost

    for (prov, cat), cost in prov_cat.items():
        links.append({
            "source": get_node(prov, "provider"),
            "target": get_node(cat,  "service"),
            "value":  round(cost, 2),
        })

    for (cat, team), cost in cat_team.items():
        links.append({
            "source": get_node(cat,  "service"),
            "target": get_node(team, "team"),
            "value":  round(cost, 2),
        })

    return {"nodes": nodes, "links": links}


@router.get("/top-movers")
def overview_top_movers(
    limit:     int     = Query(default=10, ge=3, le=50),
    db:        Session = Depends(get_db),
    tenant_id: str     = Depends(get_optional_tenant),
):
    """
    Returns top cost increases and decreases by service vs prior 7-day window.
    """
    today      = date.today()
    cur_start  = (today - timedelta(days=6)).isoformat()
    cur_end    = today.isoformat()
    prev_start = (today - timedelta(days=13)).isoformat()
    prev_end   = (today - timedelta(days=7)).isoformat()

    def _period_by_service(start: str, end: str) -> dict[str, float]:
        rows = (
            db.query(
                FocusCost.service_name,
                FocusCost.provider_name,
                func.sum(FocusCost.effective_cost).label("cost"),
            )
            .filter(
                FocusCost.tenant_id == tenant_id,
                FocusCost.billing_period_start >= start,
                FocusCost.billing_period_start <= end,
            )
            .group_by(FocusCost.service_name, FocusCost.provider_name)
            .all()
        )
        return {f"{r.provider_name}/{r.service_name}": float(r.cost or 0) for r in rows}

    cur  = _period_by_service(cur_start,  cur_end)
    prev = _period_by_service(prev_start, prev_end)
    all_keys = set(cur.keys()) | set(prev.keys())

    movers = []
    for key in all_keys:
        c = cur.get(key, 0)
        p = prev.get(key, 0)
        delta     = c - p
        delta_pct = round((delta / p * 100) if p else 100, 1)
        parts = key.split("/", 1)
        movers.append({
            "provider":  parts[0],
            "service":   parts[1] if len(parts) > 1 else key,
            "current":   round(c, 2),
            "previous":  round(p, 2),
            "delta":     round(delta, 2),
            "delta_pct": delta_pct,
            "direction": "up" if delta > 0 else "down",
        })

    movers.sort(key=lambda x: abs(x["delta"]), reverse=True)
    return {"movers": movers[:limit], "window_days": 7}


@router.get("/team-chargeback")
def overview_team_chargeback(
    db:        Session = Depends(get_db),
    tenant_id: str     = Depends(get_optional_tenant),
):
    mtd_start, mtd_end = _mtd_bounds()
    pm_start,  pm_end  = _period_bounds(1)

    def _by_team(start: str, end: str) -> dict[str, float]:
        rows = (
            db.query(
                FocusCost.x_team,
                func.sum(FocusCost.effective_cost).label("cost"),
            )
            .filter(
                FocusCost.tenant_id == tenant_id,
                FocusCost.billing_period_start >= start,
                FocusCost.billing_period_start <= end,
                FocusCost.x_team != "",
            )
            .group_by(FocusCost.x_team)
            .all()
        )
        return {r.x_team: float(r.cost or 0) for r in rows}

    cur  = _by_team(mtd_start, mtd_end)
    prev = _by_team(pm_start,  pm_end)
    all_teams = sorted(set(cur.keys()) | set(prev.keys()))

    result = []
    for team in all_teams:
        c = cur.get(team, 0)
        p = prev.get(team, 0)
        result.append({
            "team":      team,
            "mtd":       round(c, 2),
            "prior_month": round(p, 2),
            "delta_pct": round((c - p) / p * 100, 1) if p else 0,
        })

    result.sort(key=lambda x: x["mtd"], reverse=True)
    return {"teams": result}


@router.get("/ai-insight")
def overview_ai_insight(
    db:        Session = Depends(get_db),
    tenant_id: str     = Depends(get_optional_tenant),
):
    """Rule-based AI commentary blurb for the executive overview."""
    mtd_start, mtd_end = _mtd_bounds()
    pm_start,  pm_end  = _period_bounds(1)

    mtd_total = _sum_focus(db, tenant_id, mtd_start, mtd_end)
    pm_total  = _sum_focus(db, tenant_id, pm_start,  pm_end)
    mtd_ai    = _ai_cost(db,  tenant_id, mtd_start, mtd_end)
    pm_ai     = _ai_cost(db,  tenant_id, pm_start,  pm_end)

    mom_pct    = round((mtd_total - pm_total) / pm_total * 100, 1) if pm_total  else 0
    ai_mom_pct = round((mtd_ai   - pm_ai)    / pm_ai    * 100, 1) if pm_ai     else 0
    ai_share   = round(mtd_ai / mtd_total * 100, 1) if mtd_total else 0

    insights = []

    if ai_share > 30:
        insights.append(
            f"AI spend now represents {ai_share}% of total cloud costs — consider reviewing "
            f"model tier selections and enabling prompt caching to reduce token consumption."
        )

    if ai_mom_pct > 15:
        insights.append(
            f"AI API costs grew {ai_mom_pct}% month-over-month. The top driver is likely "
            f"increased request volume from production workloads — check the AI Cost dashboard for model breakdowns."
        )
    elif ai_mom_pct < -10:
        insights.append(
            f"AI spend decreased {abs(ai_mom_pct)}% vs last month — well done. "
            f"Model swap recommendations and cache tuning appear to be delivering savings."
        )

    if mom_pct > 20:
        insights.append(
            f"Total cloud spend is up {mom_pct}% month-over-month. Review the Top Movers panel for the highest-impact services."
        )

    if not insights:
        insights.append(
            f"Cloud spend is tracking normally at ${mtd_total:,.0f} MTD. "
            f"AI workloads account for {ai_share}% of total spend."
        )

    # Top spend model
    top_model_row = (
        db.query(FocusCost.x_ai_model, func.sum(FocusCost.effective_cost).label("cost"))
        .filter(
            FocusCost.tenant_id == tenant_id,
            FocusCost.billing_period_start >= mtd_start,
            FocusCost.x_ai_model != "",
        )
        .group_by(FocusCost.x_ai_model)
        .order_by(func.sum(FocusCost.effective_cost).desc())
        .first()
    )
    if top_model_row:
        insights.append(
            f"Highest-spend model this month: {top_model_row[0]} "
            f"(${top_model_row[1]:,.0f}). Check the Model Router for swap options."
        )

    return {
        "insights": insights,
        "mtd_total": round(mtd_total, 2),
        "ai_pct":    ai_share,
        "mom_pct":   mom_pct,
    }
