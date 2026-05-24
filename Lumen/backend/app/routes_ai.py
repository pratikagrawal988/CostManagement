"""
AI Cost API endpoints — powers the AI Cost Dashboard (Screen 06).

Endpoints:
  GET  /api/ai/kpis                  — 5-card KPI strip (MTD spend, % of cloud, tokens, $/1M, cache hit)
  GET  /api/ai/vendor-breakdown      — Cost + token totals grouped by vendor
  GET  /api/ai/model-detail          — Per-model row with input/output split, 7d trend, swap suggestion
  GET  /api/ai/model-router          — Swap suggestions (current → cheaper, savings/mo, risk)
  GET  /api/ai/seat-heatmap          — Per-user SaaS seat status grid (Cursor, Copilot, etc.)
  GET  /api/ai/app-attribution       — Cost-per-app breakdown with request count + error rate
  GET  /api/ai/daily-trend           — Daily AI spend series (last N days) for sparklines / area chart
  POST /api/ai/classify              — Manually classify a SKU line into AI vendor/model
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, case, text

from .auth import get_optional_tenant
from .database import get_db
from .models import (
    FocusCost, CostAggregation, AIServiceClassification,
    ModelSwapSuggestion, SaaSToolAllocation, AppCostAttribution,
    new_id, utcnow,
)

router = APIRouter(prefix="/api/ai", tags=["ai-cost"])


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _mtd_range() -> tuple[str, str]:
    """Return (YYYY-MM-01, today) as ISO date strings."""
    today = datetime.now(timezone.utc).date()
    start = today.replace(day=1)
    return str(start), str(today)


def _days_range(days: int) -> tuple[str, str]:
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=days)
    return str(start), str(today)


def _prev_period(start: str, end: str) -> tuple[str, str]:
    """Return the same-length window immediately before [start, end]."""
    s = datetime.strptime(start, "%Y-%m-%d").date()
    e = datetime.strptime(end,   "%Y-%m-%d").date()
    delta = (e - s) + timedelta(days=1)
    prev_end   = s - timedelta(days=1)
    prev_start = prev_end - delta + timedelta(days=1)
    return str(prev_start), str(prev_end)


def _pct_change(current: float, previous: float) -> Optional[float]:
    if previous == 0:
        return None
    return round((current - previous) / previous * 100, 1)


# ─────────────────────────────────────────────────────────────────────────────
# 1. KPI Strip
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/kpis")
def get_ai_kpis(
    tenant_id: str = Depends(get_optional_tenant),
    start_date: Optional[str] = Query(None, description="YYYY-MM-DD (default: MTD)"),
    end_date:   Optional[str] = Query(None, description="YYYY-MM-DD (default: today)"),
    db: Session = Depends(get_db),
):
    """
    Returns KPI cards for the AI Cost dashboard header strip:
      - ai_spend_mtd        Total AI billed cost in period
      - ai_pct_of_cloud     AI spend as % of total cloud spend
      - total_tokens_14d    Input + output tokens over last 14 days
      - blended_per_1m_tok  Blended cost per 1M tokens
      - cache_hit_rate_pct  % tokens served from cache (x_cache_read_tokens / total input)
      - cache_saving_usd    Estimated saving from cache hits
    """
    s, e = (start_date, end_date) if start_date else _mtd_range()
    ps, pe = _prev_period(s, e)

    # ── AI spend this period ──────────────────────────────────────────────────
    ai_q = db.query(
        func.sum(FocusCost.billed_cost).label("cost"),
        func.sum(FocusCost.x_input_tokens).label("input_tok"),
        func.sum(FocusCost.x_output_tokens).label("output_tok"),
        func.sum(FocusCost.x_cache_read_tokens).label("cache_tok"),
    ).filter(
        FocusCost.tenant_id == tenant_id,
        FocusCost.billing_period_start >= s,
        FocusCost.billing_period_start <= e,
        FocusCost.x_ai_vendor != "",
    ).one()

    ai_cost      = float(ai_q.cost or 0)
    input_tok    = float(ai_q.input_tok or 0)
    output_tok   = float(ai_q.output_tok or 0)
    cache_tok    = float(ai_q.cache_tok or 0)
    total_tok    = input_tok + output_tok

    # ── AI spend previous period (for trend) ─────────────────────────────────
    prev_ai = db.query(func.sum(FocusCost.billed_cost)).filter(
        FocusCost.tenant_id == tenant_id,
        FocusCost.billing_period_start >= ps,
        FocusCost.billing_period_start <= pe,
        FocusCost.x_ai_vendor != "",
    ).scalar() or 0

    # ── Total cloud spend this period ─────────────────────────────────────────
    total_cloud = db.query(func.sum(FocusCost.billed_cost)).filter(
        FocusCost.tenant_id == tenant_id,
        FocusCost.billing_period_start >= s,
        FocusCost.billing_period_start <= e,
    ).scalar() or 0

    # ── Token economics ───────────────────────────────────────────────────────
    blended_per_1m = (ai_cost / total_tok * 1_000_000) if total_tok > 0 else 0

    # Cache hit rate: cache_read_tokens / input_tokens
    cache_hit_pct = (cache_tok / input_tok * 100) if input_tok > 0 else 0

    # Cache saving: cache tokens cost ~10% of full input price on average
    avg_input_per_1m = (ai_cost / input_tok * 1_000_000 * 0.6) if input_tok > 0 else 0
    cache_saving = cache_tok / 1_000_000 * avg_input_per_1m * 0.9  # 90% discount vs full price

    # ── Last 14 days token total ──────────────────────────────────────────────
    s14, e14 = _days_range(14)
    tokens_14d_row = db.query(
        func.sum(FocusCost.x_input_tokens + FocusCost.x_output_tokens)
    ).filter(
        FocusCost.tenant_id == tenant_id,
        FocusCost.billing_period_start >= s14,
        FocusCost.billing_period_start <= e14,
        FocusCost.x_ai_vendor != "",
    ).scalar() or 0

    return {
        "period": {"start": s, "end": e},
        "kpis": {
            "ai_spend_mtd": {
                "value": round(ai_cost, 2),
                "currency": "USD",
                "trend_pct": _pct_change(ai_cost, float(prev_ai)),
                "label": "AI Spend MTD",
            },
            "ai_pct_of_cloud": {
                "value": round(ai_cost / float(total_cloud) * 100, 1) if total_cloud else 0,
                "label": "% of Cloud Spend",
                "total_cloud_usd": round(float(total_cloud), 2),
            },
            "total_tokens_14d": {
                "value": round(float(tokens_14d_row), 0),
                "label": "Tokens (14d)",
                "input_tokens": round(input_tok, 0),
                "output_tokens": round(output_tok, 0),
            },
            "blended_per_1m_tokens": {
                "value": round(blended_per_1m, 4),
                "label": "Blended $/1M Tokens",
                "currency": "USD",
            },
            "cache_hit_rate": {
                "value": round(cache_hit_pct, 1),
                "label": "Prompt Cache Hit Rate",
                "cache_tokens": round(cache_tok, 0),
                "saving_usd": round(cache_saving, 2),
            },
        },
    }


# ─────────────────────────────────────────────────────────────────────────────
# 2. Vendor Breakdown
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/vendor-breakdown")
def get_vendor_breakdown(
    tenant_id:  str = Depends(get_optional_tenant),
    start_date: Optional[str] = Query(None),
    end_date:   Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """
    Cost, token totals, and 7d trend grouped by AI vendor.
    Returns rows sorted by billed_cost desc.
    """
    s, e = (start_date, end_date) if start_date else _mtd_range()
    ps, pe = _prev_period(s, e)

    rows = db.query(
        FocusCost.x_ai_vendor.label("vendor"),
        func.sum(FocusCost.billed_cost).label("cost"),
        func.sum(FocusCost.x_input_tokens + FocusCost.x_output_tokens).label("tokens"),
        func.sum(FocusCost.x_request_count).label("requests"),
        func.count(func.distinct(FocusCost.x_ai_model)).label("model_count"),
    ).filter(
        FocusCost.tenant_id == tenant_id,
        FocusCost.billing_period_start >= s,
        FocusCost.billing_period_start <= e,
        FocusCost.x_ai_vendor != "",
    ).group_by(FocusCost.x_ai_vendor).order_by(func.sum(FocusCost.billed_cost).desc()).all()

    # Previous period totals per vendor for trend delta
    prev_rows = db.query(
        FocusCost.x_ai_vendor,
        func.sum(FocusCost.billed_cost).label("cost"),
    ).filter(
        FocusCost.tenant_id == tenant_id,
        FocusCost.billing_period_start >= ps,
        FocusCost.billing_period_start <= pe,
        FocusCost.x_ai_vendor != "",
    ).group_by(FocusCost.x_ai_vendor).all()

    prev_map = {r.x_ai_vendor: float(r.cost) for r in prev_rows}
    total_cost = sum(float(r.cost or 0) for r in rows)

    return {
        "period": {"start": s, "end": e},
        "vendors": [
            {
                "vendor":       r.vendor,
                "billed_cost":  round(float(r.cost or 0), 2),
                "pct_of_ai":    round(float(r.cost or 0) / total_cost * 100, 1) if total_cost else 0,
                "total_tokens": int(r.tokens or 0),
                "requests":     int(r.requests or 0),
                "model_count":  int(r.model_count or 0),
                "trend_pct":    _pct_change(float(r.cost or 0), prev_map.get(r.vendor, 0)),
            }
            for r in rows
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
# 3. Model Detail Table
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/model-detail")
def get_model_detail(
    tenant_id:  str = Depends(get_optional_tenant),
    start_date: Optional[str] = Query(None),
    end_date:   Optional[str] = Query(None),
    vendor:     Optional[str] = Query(None, description="Filter by vendor"),
    db: Session = Depends(get_db),
):
    """
    Per-model breakdown: vendor, model name, cost, input/output token split,
    blended $/1M tokens, 7d trend, and linked swap suggestion if available.
    """
    s, e = (start_date, end_date) if start_date else _mtd_range()
    s7, e7 = _days_range(7)

    q = db.query(
        FocusCost.x_ai_vendor.label("vendor"),
        FocusCost.x_ai_model.label("model"),
        FocusCost.x_ai_tier.label("tier"),
        func.sum(FocusCost.billed_cost).label("cost"),
        func.sum(FocusCost.x_input_tokens).label("input_tok"),
        func.sum(FocusCost.x_output_tokens).label("output_tok"),
        func.sum(FocusCost.x_cache_read_tokens).label("cache_tok"),
        func.sum(FocusCost.x_request_count).label("requests"),
    ).filter(
        FocusCost.tenant_id == tenant_id,
        FocusCost.billing_period_start >= s,
        FocusCost.billing_period_start <= e,
        FocusCost.x_ai_vendor != "",
    )
    if vendor:
        q = q.filter(FocusCost.x_ai_vendor == vendor)

    rows = q.group_by(
        FocusCost.x_ai_vendor,
        FocusCost.x_ai_model,
        FocusCost.x_ai_tier,
    ).order_by(func.sum(FocusCost.billed_cost).desc()).all()

    # 7-day comparison for sparkline / trend
    prev7 = db.query(
        FocusCost.x_ai_model,
        func.sum(FocusCost.billed_cost).label("cost"),
    ).filter(
        FocusCost.tenant_id == tenant_id,
        FocusCost.billing_period_start >= s7,
        FocusCost.billing_period_start <= e7,
        FocusCost.x_ai_vendor != "",
    ).group_by(FocusCost.x_ai_model).all()

    prev7_map = {r.x_ai_model: float(r.cost) for r in prev7}

    # Fetch swap suggestions
    swaps = db.query(ModelSwapSuggestion).filter(
        ModelSwapSuggestion.tenant_id == tenant_id,
        ModelSwapSuggestion.active == True,
    ).all()
    swap_map = {s.current_model: s for s in swaps}

    result = []
    for r in rows:
        cost       = float(r.cost or 0)
        input_tok  = float(r.input_tok or 0)
        output_tok = float(r.output_tok or 0)
        total_tok  = input_tok + output_tok
        swap = swap_map.get(r.model)
        result.append({
            "vendor":          r.vendor,
            "model":           r.model,
            "tier":            r.tier,
            "billed_cost":     round(cost, 2),
            "input_tokens":    round(input_tok, 0),
            "output_tokens":   round(output_tok, 0),
            "cache_tokens":    round(float(r.cache_tok or 0), 0),
            "requests":        int(r.requests or 0),
            "cost_per_1m_tok": round(cost / total_tok * 1_000_000, 4) if total_tok else 0,
            "trend_pct":       _pct_change(cost, prev7_map.get(r.model, 0)),
            "swap_suggestion": {
                "suggested_model":  swap.suggested_model,
                "suggested_vendor": swap.suggested_vendor,
                "saving_usd_mo":    round(swap.monthly_cost_saving, 2),
                "quality_risk":     swap.quality_risk,
            } if swap else None,
        })

    return {"period": {"start": s, "end": e}, "models": result}


# ─────────────────────────────────────────────────────────────────────────────
# 4. Model Router (Swap Suggestions)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/model-router")
def get_model_router(
    tenant_id: str = Depends(get_optional_tenant),
    db: Session = Depends(get_db),
):
    """
    Returns active model swap suggestions ranked by monthly saving.
    Each card shows: current model → suggested model, $/mo saving, quality risk,
    latency delta, applicable use cases, and an explanation.
    """
    suggestions = db.query(ModelSwapSuggestion).filter(
        ModelSwapSuggestion.tenant_id == tenant_id,
        ModelSwapSuggestion.active == True,
    ).order_by(ModelSwapSuggestion.monthly_cost_saving.desc()).all()

    # If no suggestions yet, generate them from classification data
    if not suggestions:
        suggestions = _generate_swap_suggestions(db, tenant_id)

    return {
        "total_potential_saving_monthly": round(
            sum(s.monthly_cost_saving for s in suggestions), 2
        ),
        "suggestions": [
            {
                "id":                  s.id,
                "current_model":       s.current_model,
                "current_vendor":      s.current_vendor,
                "suggested_model":     s.suggested_model,
                "suggested_vendor":    s.suggested_vendor,
                "monthly_cost_current": round(s.monthly_cost_current, 2),
                "monthly_cost_saving":  round(s.monthly_cost_saving, 2),
                "saving_pct":          round(s.saving_pct, 1),
                "quality_risk":        s.quality_risk,
                "latency_delta_ms":    s.latency_delta_ms,
                "rationale":           s.rationale,
                "applicable_use_cases": s.applicable_use_cases,
                "score":               round(s.score, 3),
            }
            for s in suggestions
        ],
    }


def _generate_swap_suggestions(
    db: Session, tenant_id: str
) -> list[ModelSwapSuggestion]:
    """
    Auto-generate swap suggestions based on current model spend vs known cheaper alternatives.
    Persists generated suggestions so they appear on subsequent calls.
    """
    # Model router knowledge base: {expensive_model: (cheaper_model, vendor, quality_risk, latency_delta, rationale)}
    ROUTER_RULES: dict[str, dict] = {
        "claude-3-opus-20240229": {
            "suggested": "claude-3-5-sonnet-20241022", "vendor": "Anthropic",
            "quality_risk": "Low", "latency_delta_ms": -200,
            "saving_pct": 80,
            "rationale": "Claude 3.5 Sonnet outperforms Opus on most benchmarks at 80% lower cost. Reserve Opus for tasks requiring extreme reasoning depth.",
            "use_cases": ["chat", "summarisation", "code-review", "data-extraction"],
        },
        "gpt-4": {
            "suggested": "gpt-4o-mini", "vendor": "OpenAI",
            "quality_risk": "Medium", "latency_delta_ms": -500,
            "saving_pct": 96,
            "rationale": "GPT-4o-mini handles most RAG and classification tasks at ~4% of GPT-4 cost. Evaluate on your golden set before full roll-out.",
            "use_cases": ["classification", "rag", "extraction"],
        },
        "gpt-4-turbo": {
            "suggested": "gpt-4o", "vendor": "OpenAI",
            "quality_risk": "Low", "latency_delta_ms": -300,
            "saving_pct": 33,
            "rationale": "GPT-4o provides equivalent quality to GPT-4 Turbo at 1/3 the input token cost with faster latency.",
            "use_cases": ["general", "vision", "function-calling"],
        },
        "claude-3-haiku-20240307": {
            "suggested": "claude-3-5-haiku-20241022", "vendor": "Anthropic",
            "quality_risk": "Low", "latency_delta_ms": 50,
            "saving_pct": -10,  # slightly more expensive but much better quality
            "rationale": "Claude 3.5 Haiku offers substantially better quality at similar pricing. Good upgrade path for high-volume low-latency workloads.",
            "use_cases": ["chat", "triage", "routing"],
        },
        "text-embedding-ada-002": {
            "suggested": "text-embedding-3-small", "vendor": "OpenAI",
            "quality_risk": "Low", "latency_delta_ms": 0,
            "saving_pct": 80,
            "rationale": "text-embedding-3-small exceeds ada-002 quality on MTEB benchmark at 80% lower cost.",
            "use_cases": ["embeddings", "semantic-search", "rag"],
        },
    }

    s, e = _mtd_range()

    # Get current model spend
    model_spend = db.query(
        FocusCost.x_ai_model,
        FocusCost.x_ai_vendor,
        func.sum(FocusCost.billed_cost).label("cost"),
    ).filter(
        FocusCost.tenant_id == tenant_id,
        FocusCost.billing_period_start >= s,
        FocusCost.billing_period_start <= e,
        FocusCost.x_ai_vendor != "",
    ).group_by(FocusCost.x_ai_model, FocusCost.x_ai_vendor).all()

    suggestions = []
    for row in model_spend:
        rule = ROUTER_RULES.get(row.x_ai_model)
        if not rule:
            continue
        monthly_cost = float(row.cost or 0)
        saving_pct = rule["saving_pct"]
        saving = monthly_cost * saving_pct / 100
        if saving <= 0:
            continue

        existing = db.query(ModelSwapSuggestion).filter(
            ModelSwapSuggestion.tenant_id == tenant_id,
            ModelSwapSuggestion.current_model == row.x_ai_model,
        ).one_or_none()

        if existing:
            existing.monthly_cost_current = monthly_cost
            existing.monthly_cost_saving  = saving
            existing.saving_pct           = saving_pct
            existing.updated_at           = utcnow()
            db.add(existing)
            suggestions.append(existing)
        else:
            s_obj = ModelSwapSuggestion(
                id=new_id(), tenant_id=tenant_id,
                current_model=row.x_ai_model, current_vendor=row.x_ai_vendor,
                suggested_model=rule["suggested"], suggested_vendor=rule["vendor"],
                monthly_cost_current=monthly_cost,
                monthly_cost_saving=saving,
                saving_pct=saving_pct,
                quality_risk=rule["quality_risk"],
                latency_delta_ms=rule["latency_delta_ms"],
                rationale=rule["rationale"],
                applicable_use_cases=rule["use_cases"],
                score=round(saving / (monthly_cost + 0.01), 3),
                active=True,
            )
            db.add(s_obj)
            suggestions.append(s_obj)

    db.commit()
    return sorted(suggestions, key=lambda x: x.monthly_cost_saving, reverse=True)


# ─────────────────────────────────────────────────────────────────────────────
# 5. Seat Heatmap (SaaS Tools)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/seat-heatmap")
def get_seat_heatmap(
    tenant_id: str  = Depends(get_optional_tenant),
    tool_name: Optional[str] = Query(None, description="e.g. 'Cursor', 'GitHub Copilot'"),
    period:    Optional[str] = Query(None, description="YYYY-MM (default: current month)"),
    db: Session = Depends(get_db),
):
    """
    Per-user seat utilisation grid for AI SaaS tools.
    Returns each user's activity status, seat cost, usage minutes, and completions.
    Status: active (>60min) | low (<60min) | idle (0 usage this month)
    """
    today = datetime.now(timezone.utc).date()
    p = period or today.strftime("%Y-%m")

    q = db.query(SaaSToolAllocation).filter(
        SaaSToolAllocation.tenant_id == tenant_id,
        SaaSToolAllocation.period == p,
    )
    if tool_name:
        q = q.filter(SaaSToolAllocation.tool_name == tool_name)

    rows = q.order_by(SaaSToolAllocation.usage_minutes.desc()).all()

    def status(row: SaaSToolAllocation) -> str:
        if row.usage_minutes >= 60:
            return "active"
        if row.usage_minutes > 0:
            return "low"
        return "idle"

    total_cost = sum(float(r.seat_cost) for r in rows)
    idle_cost  = sum(float(r.seat_cost) for r in rows if status(r) == "idle")

    # Group by tool
    tools: dict[str, dict] = {}
    for r in rows:
        if r.tool_name not in tools:
            tools[r.tool_name] = {
                "tool_name": r.tool_name,
                "vendor":    r.vendor,
                "total_seats": 0,
                "active_seats": 0,
                "low_seats": 0,
                "idle_seats": 0,
                "total_cost": 0.0,
                "idle_cost": 0.0,
                "seats": [],
            }
        t = tools[r.tool_name]
        s = status(r)
        t["total_seats"] += 1
        t[f"{s}_seats"] += 1
        t["total_cost"]  += float(r.seat_cost)
        if s == "idle":
            t["idle_cost"] += float(r.seat_cost)
        t["seats"].append({
            "user_id":       r.user_id,
            "user_email":    r.user_email,
            "team":          r.team,
            "status":        s,
            "seat_cost":     float(r.seat_cost),
            "usage_minutes": r.usage_minutes,
            "completions":   r.completions,
            "last_active_at": r.last_active_at.isoformat() if r.last_active_at else None,
        })

    return {
        "period": p,
        "summary": {
            "total_seats": len(rows),
            "total_cost":  round(total_cost, 2),
            "idle_cost":   round(idle_cost, 2),
            "idle_pct":    round(idle_cost / total_cost * 100, 1) if total_cost else 0,
        },
        "tools": list(tools.values()),
    }


# ─────────────────────────────────────────────────────────────────────────────
# 6. App / Caller Attribution
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/app-attribution")
def get_app_attribution(
    tenant_id:  str = Depends(get_optional_tenant),
    start_date: Optional[str] = Query(None),
    end_date:   Optional[str] = Query(None),
    ai_vendor:  Optional[str] = Query(None),
    limit:      int = Query(20),
    db: Session = Depends(get_db),
):
    """
    Cost per application (caller) breakdown with request count, token totals,
    average latency, and error rate. Sorted by daily_cost desc.
    """
    s, e = (start_date, end_date) if start_date else _days_range(30)

    q = db.query(
        AppCostAttribution.app_id,
        AppCostAttribution.app_name,
        AppCostAttribution.team,
        AppCostAttribution.ai_vendor,
        AppCostAttribution.ai_model,
        func.sum(AppCostAttribution.daily_cost).label("total_cost"),
        func.sum(AppCostAttribution.request_count).label("requests"),
        func.sum(AppCostAttribution.input_tokens).label("input_tok"),
        func.sum(AppCostAttribution.output_tokens).label("output_tok"),
        func.avg(AppCostAttribution.avg_latency_ms).label("avg_latency"),
        func.avg(AppCostAttribution.error_rate).label("avg_error_rate"),
    ).filter(
        AppCostAttribution.tenant_id == tenant_id,
        AppCostAttribution.date >= s,
        AppCostAttribution.date <= e,
    )
    if ai_vendor:
        q = q.filter(AppCostAttribution.ai_vendor == ai_vendor)

    rows = q.group_by(
        AppCostAttribution.app_id,
        AppCostAttribution.app_name,
        AppCostAttribution.team,
        AppCostAttribution.ai_vendor,
        AppCostAttribution.ai_model,
    ).order_by(func.sum(AppCostAttribution.daily_cost).desc()).limit(limit).all()

    return {
        "period": {"start": s, "end": e},
        "apps": [
            {
                "app_id":       r.app_id,
                "app_name":     r.app_name,
                "team":         r.team,
                "ai_vendor":    r.ai_vendor,
                "ai_model":     r.ai_model,
                "total_cost":   round(float(r.total_cost or 0), 2),
                "requests":     int(r.requests or 0),
                "input_tokens": int(r.input_tok or 0),
                "output_tokens":int(r.output_tok or 0),
                "avg_latency_ms": round(float(r.avg_latency or 0), 0),
                "error_rate_pct": round(float(r.avg_error_rate or 0) * 100, 2),
                "cost_per_request": round(
                    float(r.total_cost or 0) / int(r.requests or 1), 6
                ) if r.requests else 0,
            }
            for r in rows
        ],
    }


# ─────────────────────────────────────────────────────────────────────────────
# 7. Daily Trend Series
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/daily-trend")
def get_ai_daily_trend(
    tenant_id:  str = Depends(get_optional_tenant),
    days:       int = Query(30),
    group_by:   str = Query("vendor", description="vendor | model | tier | total"),
    db: Session = Depends(get_db),
):
    """
    Daily AI spend time series for sparklines and area charts.
    Returns one series per group_by value over the last N days.
    """
    s, e = _days_range(days)

    # Build the group dimension
    dim_col = {
        "vendor": FocusCost.x_ai_vendor,
        "model":  FocusCost.x_ai_model,
        "tier":   FocusCost.x_ai_tier,
        "total":  func.literal("total"),
    }.get(group_by, FocusCost.x_ai_vendor)

    rows = db.query(
        FocusCost.billing_period_start.label("date"),
        dim_col.label("group"),
        func.sum(FocusCost.billed_cost).label("cost"),
        func.sum(FocusCost.x_input_tokens + FocusCost.x_output_tokens).label("tokens"),
    ).filter(
        FocusCost.tenant_id == tenant_id,
        FocusCost.billing_period_start >= s,
        FocusCost.billing_period_start <= e,
        FocusCost.x_ai_vendor != "",
    ).group_by(
        FocusCost.billing_period_start, dim_col
    ).order_by(FocusCost.billing_period_start).all()

    # Pivot into series
    series: dict[str, list] = {}
    for r in rows:
        g = r.group or "unknown"
        if g not in series:
            series[g] = []
        series[g].append({
            "date":   r.date,
            "cost":   round(float(r.cost or 0), 2),
            "tokens": int(r.tokens or 0),
        })

    return {
        "period": {"start": s, "end": e, "days": days},
        "group_by": group_by,
        "series": [{"group": k, "data": v} for k, v in series.items()],
    }


# ─────────────────────────────────────────────────────────────────────────────
# 8. Manual SKU Classification
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/classify")
def classify_sku(
    tenant_id:   str = Depends(get_optional_tenant),
    provider:    str = Query(...),
    service:     str = Query(...),
    sku_pattern: str = Query(...),
    ai_type:     str = Query(...),
    ai_vendor:   str = Query(...),
    ai_model:    str = Query(...),
    cost_unit:   str = Query("tokens"),
    token_type:  str = Query(""),
    price_per_1m:float = Query(0.0),
    db: Session = Depends(get_db),
):
    """Manually add or update an AI SKU classification rule."""
    existing = db.query(AIServiceClassification).filter(
        AIServiceClassification.tenant_id == tenant_id,
        AIServiceClassification.provider  == provider,
        AIServiceClassification.service   == service,
        AIServiceClassification.sku_pattern == sku_pattern,
    ).one_or_none()

    if existing:
        existing.ai_type    = ai_type
        existing.ai_vendor  = ai_vendor
        existing.ai_model   = ai_model
        existing.cost_unit  = cost_unit
        existing.token_type = token_type
        existing.price_per_1m = price_per_1m
        existing.updated_at = utcnow()
        db.commit()
        return {"status": "updated", "id": existing.id}

    cls = AIServiceClassification(
        id=new_id(), tenant_id=tenant_id,
        provider=provider, service=service, sku_pattern=sku_pattern,
        ai_type=ai_type, ai_vendor=ai_vendor, ai_model=ai_model,
        cost_unit=cost_unit, token_type=token_type, price_per_1m=price_per_1m,
    )
    db.add(cls)
    db.commit()
    return {"status": "created", "id": cls.id}
