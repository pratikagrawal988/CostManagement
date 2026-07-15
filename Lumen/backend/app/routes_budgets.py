"""
Budget management — Phase 13.

- GET    /api/budgets            → budgets with live actuals, utilization, forecast, alert status
- POST   /api/budgets            → create (budgets:write)
- PATCH  /api/budgets/{id}       → update (budgets:write)
- DELETE /api/budgets/{id}       → delete (budgets:write)
- GET    /api/budgets/{id}/history → per-month actual vs budget

Actuals are computed live from FocusCost (effective_cost), scoped by the
budget's optional provider / service_category / sub_account filters.
"""

from __future__ import annotations

import calendar
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from .auth import TokenPayload
from .database import get_db
from .models import Budget, FocusCost, new_id, utcnow
from .rbac import record_audit, require_permission

router = APIRouter(prefix="/api/budgets", tags=["budgets"])

VALID_PERIODS = {"monthly", "quarterly", "annual"}


# ── Schemas ───────────────────────────────────────────────────────────────────

class BudgetRequest(BaseModel):
    name: str
    amount: float
    period: str = "monthly"
    currency: str = "USD"
    provider_name: str = ""       # "" = all providers
    service_category: str = ""    # "" = all categories
    sub_account_id: str = ""      # "" = all accounts
    alert_thresholds: list[float] = [80.0, 100.0]
    owner_email: str = ""
    enabled: bool = True


class BudgetPatch(BaseModel):
    name: Optional[str] = None
    amount: Optional[float] = None
    period: Optional[str] = None
    provider_name: Optional[str] = None
    service_category: Optional[str] = None
    sub_account_id: Optional[str] = None
    alert_thresholds: Optional[list[float]] = None
    owner_email: Optional[str] = None
    enabled: Optional[bool] = None


# ── Period helpers ────────────────────────────────────────────────────────────

def _period_window(period: str, anchor: date) -> tuple[str, str]:
    """Return (start, end) ISO dates of the period containing `anchor`."""
    if period == "annual":
        return f"{anchor.year}-01-01", f"{anchor.year}-12-31"
    if period == "quarterly":
        q0 = 3 * ((anchor.month - 1) // 3) + 1
        qend = q0 + 2
        last = calendar.monthrange(anchor.year, qend)[1]
        return f"{anchor.year}-{q0:02d}-01", f"{anchor.year}-{qend:02d}-{last:02d}"
    last = calendar.monthrange(anchor.year, anchor.month)[1]
    return f"{anchor.year}-{anchor.month:02d}-01", f"{anchor.year}-{anchor.month:02d}-{last:02d}"


def _latest_data_month(db: Session, tenant_id: str) -> Optional[date]:
    """Most recent month that actually has cost rows (demo data may lag today)."""
    latest = (
        db.query(func.max(FocusCost.billing_period_start))
        .filter(FocusCost.tenant_id == tenant_id)
        .scalar()
    )
    if not latest:
        return None
    try:
        return date.fromisoformat(str(latest)[:10])
    except ValueError:
        return None


def _actual_for(db: Session, tenant_id: str, b: Budget, start: str, end: str) -> float:
    q = db.query(func.coalesce(func.sum(FocusCost.effective_cost), 0.0)).filter(
        FocusCost.tenant_id == tenant_id,
        FocusCost.billing_period_start >= start,
        FocusCost.billing_period_start <= end,
    )
    if b.provider_name:
        q = q.filter(FocusCost.provider_name == b.provider_name)
    if b.service_category:
        q = q.filter(FocusCost.service_category == b.service_category)
    if b.sub_account_id:
        q = q.filter(FocusCost.sub_account_id == b.sub_account_id)
    return float(q.scalar() or 0.0)


def _status(utilization: float, thresholds: list[float]) -> str:
    if utilization >= 100.0:
        return "over"
    warn = min((t for t in (thresholds or [80.0]) if t < 100.0), default=80.0)
    return "warning" if utilization >= warn else "ok"


def _fmt(db: Session, tenant_id: str, b: Budget, anchor: date) -> dict:
    start, end = _period_window(b.period, anchor)
    actual = _actual_for(db, tenant_id, b, start, end)
    utilization = (actual / b.amount * 100.0) if b.amount else 0.0

    # Simple run-rate forecast within the period
    period_start = date.fromisoformat(start)
    period_end = date.fromisoformat(end)
    total_days = (period_end - period_start).days + 1
    elapsed = min(max((anchor - period_start).days + 1, 1), total_days)
    forecast = actual / elapsed * total_days if elapsed else actual

    return {
        "id": b.id,
        "name": b.name,
        "period": b.period,
        "amount": b.amount,
        "currency": b.currency,
        "scope": {
            "provider_name": b.provider_name,
            "service_category": b.service_category,
            "sub_account_id": b.sub_account_id,
        },
        "alert_thresholds": b.alert_thresholds or [],
        "owner_email": b.owner_email,
        "enabled": b.enabled,
        "window": {"start": start, "end": end},
        "actual": round(actual, 2),
        "utilization_pct": round(utilization, 1),
        "forecast_eop": round(forecast, 2),
        "forecast_pct": round((forecast / b.amount * 100.0) if b.amount else 0.0, 1),
        "status": _status(utilization, b.alert_thresholds or []),
        "created_at": b.created_at.isoformat(),
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("")
def list_budgets(
    current: TokenPayload = Depends(require_permission("budgets:read")),
    anchor: str = Query("latest", description="'latest' (most recent month with cost data), 'today', or YYYY-MM-DD"),
    db: Session = Depends(get_db),
):
    budgets = (
        db.query(Budget)
        .filter(Budget.tenant_id == current.tenant_id)
        .order_by(Budget.created_at)
        .all()
    )

    if anchor == "today":
        anchor_date = date.today()
    elif anchor == "latest":
        anchor_date = _latest_data_month(db, current.tenant_id) or date.today()
    else:
        try:
            anchor_date = date.fromisoformat(anchor)
        except ValueError:
            raise HTTPException(400, "anchor must be 'latest', 'today', or YYYY-MM-DD")

    items = [_fmt(db, current.tenant_id, b, anchor_date) for b in budgets]
    return {
        "count": len(items),
        "anchor": anchor_date.isoformat(),
        "alerts": [i for i in items if i["enabled"] and i["status"] in ("warning", "over")],
        "budgets": items,
    }


@router.post("", status_code=201)
def create_budget(
    req: BudgetRequest,
    current: TokenPayload = Depends(require_permission("budgets:write")),
    db: Session = Depends(get_db),
):
    if req.period not in VALID_PERIODS:
        raise HTTPException(400, f"period must be one of {sorted(VALID_PERIODS)}")
    if req.amount <= 0:
        raise HTTPException(400, "amount must be positive")
    if any(t <= 0 or t > 200 for t in req.alert_thresholds):
        raise HTTPException(400, "alert thresholds must be percentages in (0, 200]")

    b = Budget(
        id=new_id(),
        tenant_id=current.tenant_id,
        name=req.name.strip() or "Untitled budget",
        amount=req.amount,
        period=req.period,
        currency=req.currency,
        provider_name=req.provider_name,
        service_category=req.service_category,
        sub_account_id=req.sub_account_id,
        alert_thresholds=sorted(req.alert_thresholds),
        owner_email=req.owner_email,
        enabled=req.enabled,
    )
    db.add(b)
    db.commit()
    db.refresh(b)

    record_audit(db, current, action="budget.create", resource_type="budget",
                 resource_id=b.id, detail={"name": b.name, "amount": b.amount, "period": b.period})
    return _fmt(db, current.tenant_id, b, _latest_data_month(db, current.tenant_id) or date.today())


@router.patch("/{budget_id}")
def update_budget(
    budget_id: str,
    req: BudgetPatch,
    current: TokenPayload = Depends(require_permission("budgets:write")),
    db: Session = Depends(get_db),
):
    b = db.query(Budget).filter(
        Budget.id == budget_id, Budget.tenant_id == current.tenant_id
    ).one_or_none()
    if not b:
        raise HTTPException(404, "Budget not found")

    changes = {}
    for field in ("name", "amount", "period", "provider_name", "service_category",
                  "sub_account_id", "alert_thresholds", "owner_email", "enabled"):
        val = getattr(req, field)
        if val is not None:
            if field == "period" and val not in VALID_PERIODS:
                raise HTTPException(400, f"period must be one of {sorted(VALID_PERIODS)}")
            if field == "amount" and val <= 0:
                raise HTTPException(400, "amount must be positive")
            changes[field] = {"from": getattr(b, field), "to": val}
            setattr(b, field, val)

    b.updated_at = utcnow()
    db.commit()
    db.refresh(b)

    record_audit(db, current, action="budget.update", resource_type="budget",
                 resource_id=b.id, detail={"name": b.name, "changes": {k: str(v) for k, v in changes.items()}})
    return _fmt(db, current.tenant_id, b, _latest_data_month(db, current.tenant_id) or date.today())


@router.delete("/{budget_id}")
def delete_budget(
    budget_id: str,
    current: TokenPayload = Depends(require_permission("budgets:write")),
    db: Session = Depends(get_db),
):
    b = db.query(Budget).filter(
        Budget.id == budget_id, Budget.tenant_id == current.tenant_id
    ).one_or_none()
    if not b:
        raise HTTPException(404, "Budget not found")
    name = b.name
    db.delete(b)
    db.commit()
    record_audit(db, current, action="budget.delete", resource_type="budget",
                 resource_id=budget_id, detail={"name": name})
    return {"status": "deleted", "id": budget_id}


@router.get("/{budget_id}/history")
def budget_history(
    budget_id: str,
    months: int = Query(6, ge=1, le=24),
    current: TokenPayload = Depends(require_permission("budgets:read")),
    db: Session = Depends(get_db),
):
    b = db.query(Budget).filter(
        Budget.id == budget_id, Budget.tenant_id == current.tenant_id
    ).one_or_none()
    if not b:
        raise HTTPException(404, "Budget not found")

    end_anchor = _latest_data_month(db, current.tenant_id) or date.today()
    out = []
    y, m = end_anchor.year, end_anchor.month
    for _ in range(months):
        anchor = date(y, m, 1)
        start, end = _period_window("monthly", anchor)
        actual = _actual_for(db, current.tenant_id, b, start, end)
        monthly_amount = b.amount if b.period == "monthly" else (
            b.amount / 3 if b.period == "quarterly" else b.amount / 12
        )
        out.append({
            "month": f"{y}-{m:02d}",
            "actual": round(actual, 2),
            "budget": round(monthly_amount, 2),
            "utilization_pct": round(actual / monthly_amount * 100.0, 1) if monthly_amount else 0.0,
        })
        m -= 1
        if m == 0:
            y, m = y - 1, 12
    out.reverse()
    return {"budget_id": b.id, "name": b.name, "months": out}
