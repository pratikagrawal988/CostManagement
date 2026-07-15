"""
Cost-based recommendation evaluator — Phase 14.

Scans FOCUS cost data with rule-based detectors and generates Finding rows
that flow into the existing tracking workflow (findings → actions → outcomes).

POST /api/recommendations/evaluate-costs   (recommendations:write)
GET  /api/recommendations/summary          (recommendations:read)

Detectors:
  commitment_coverage  — on-demand Compute spend per provider with no commitment
                         discounts → recommend RI / Savings Plan / CUD.
  rightsizing          — steady-state, high-cost Compute resources → downsize.
  unused_commitments   — commitment discounts with Unused status → waste.
"""

from __future__ import annotations

import statistics
from collections import defaultdict
from datetime import date, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from .auth import TokenPayload
from .database import get_db
from .models import Customer, Finding, FocusCost, new_id, utcnow
from .rbac import record_audit, require_permission

router = APIRouter(prefix="/api/recommendations", tags=["recommendations"])

WINDOW_DAYS = 30
COMMITMENT_SAVINGS_RATE = 0.28   # typical 1-yr no-upfront SP/RI discount
RIGHTSIZE_SAVINGS_RATE = 0.20    # one-size-down estimate
MIN_COMMITMENT_MONTHLY = 500.0   # ignore providers below this on-demand spend
MIN_RIGHTSIZE_MONTHLY = 300.0    # ignore resources below this monthly cost
STEADY_CV = 0.20                 # coefficient of variation → "steady" workload
MAX_RIGHTSIZE_FINDINGS = 10


def _default_customer(db: Session, tenant_id: str) -> Customer:
    cust = db.query(Customer).filter(Customer.tenant_id == tenant_id).first()
    if not cust:
        cust = Customer(id=new_id(), tenant_id=tenant_id, name="Default")
        db.add(cust)
        db.commit()
    return cust


def _open_finding_keys(db: Session, tenant_id: str) -> set[tuple[str, str]]:
    """(resource_id, detector) pairs that already have a non-closed finding."""
    rows = db.query(Finding).filter(
        Finding.tenant_id == tenant_id,
        Finding.state.notin_(["closed", "dismissed", "resolved"]),
    ).all()
    return {(f.resource_id, (f.evidence or {}).get("detector", "")) for f in rows}


def _window_start() -> str:
    return (date.today() - timedelta(days=WINDOW_DAYS)).isoformat()


# ── Detectors ─────────────────────────────────────────────────────────────────

def detect_commitment_coverage(db: Session, tenant_id: str) -> list[dict]:
    """On-demand Compute spend by provider with zero commitment coverage."""
    rows = (
        db.query(
            FocusCost.provider_name,
            func.sum(FocusCost.effective_cost).label("ondemand"),
        )
        .filter(
            FocusCost.tenant_id == tenant_id,
            FocusCost.charge_period_start >= _window_start(),
            FocusCost.service_category == "Compute",
            FocusCost.pricing_category == "Standard",
        )
        .group_by(FocusCost.provider_name)
        .all()
    )
    committed = dict(
        db.query(
            FocusCost.provider_name,
            func.sum(FocusCost.effective_cost),
        )
        .filter(
            FocusCost.tenant_id == tenant_id,
            FocusCost.charge_period_start >= _window_start(),
            FocusCost.service_category == "Compute",
            FocusCost.pricing_category != "Standard",
        )
        .group_by(FocusCost.provider_name)
        .all()
    )

    plans = {"AWS": "Compute Savings Plan / Reserved Instances",
             "Azure": "Azure Reservations / Savings Plan",
             "Google Cloud": "Committed Use Discounts (CUD)"}

    out = []
    for provider, ondemand in rows:
        monthly = float(ondemand or 0.0) * (30.0 / WINDOW_DAYS)
        commit = float(committed.get(provider, 0.0))
        coverage = commit / (commit + float(ondemand)) * 100.0 if (commit + float(ondemand)) else 0.0
        if monthly < MIN_COMMITMENT_MONTHLY or coverage > 60.0:
            continue
        out.append({
            "detector": "commitment_coverage",
            "resource_id": f"{provider.lower().replace(' ', '-')}-compute-fleet",
            "resource_type": "ComputeFleet",
            "provider": provider,
            "priority": "P1" if monthly > 10000 else "P2",
            "savings": round(monthly * COMMITMENT_SAVINGS_RATE, 2),
            "evidence": {
                "detector": "commitment_coverage",
                "window_days": WINDOW_DAYS,
                "ondemand_monthly": round(monthly, 2),
                "commitment_coverage_pct": round(coverage, 1),
                "assumed_discount_rate": COMMITMENT_SAVINGS_RATE,
            },
            "proposed_action": {
                "type": "purchase_commitment",
                "title": f"Purchase {plans.get(provider, 'a commitment plan')} for steady-state compute",
                "description": (
                    f"{provider} compute is running {round(monthly):,} USD/month on-demand with "
                    f"{coverage:.0f}% commitment coverage. Committing the steady-state baseline at a "
                    f"~{int(COMMITMENT_SAVINGS_RATE*100)}% discount saves an estimated "
                    f"{round(monthly * COMMITMENT_SAVINGS_RATE):,} USD/month."
                ),
            },
        })
    return out


def detect_rightsizing(db: Session, tenant_id: str) -> list[dict]:
    """Steady-state, high-cost Compute resources — candidates to size down."""
    rows = (
        db.query(
            FocusCost.resource_id,
            FocusCost.resource_name,
            FocusCost.provider_name,
            FocusCost.region_name,
            FocusCost.sub_account_id,
            func.substr(FocusCost.charge_period_start, 1, 10).label("day"),
            func.sum(FocusCost.effective_cost).label("cost"),
        )
        .filter(
            FocusCost.tenant_id == tenant_id,
            FocusCost.charge_period_start >= _window_start(),
            FocusCost.service_category == "Compute",
            FocusCost.resource_id != "",
        )
        .group_by(
            FocusCost.resource_id, FocusCost.resource_name, FocusCost.provider_name,
            FocusCost.region_name, FocusCost.sub_account_id, "day",
        )
        .all()
    )

    daily = defaultdict(list)
    meta = {}
    for r in rows:
        daily[r.resource_id].append(float(r.cost or 0.0))
        meta[r.resource_id] = r

    out = []
    for rid, costs in daily.items():
        if len(costs) < 7:
            continue
        mean = statistics.fmean(costs)
        monthly = mean * 30.0
        if monthly < MIN_RIGHTSIZE_MONTHLY:
            continue
        cv = (statistics.pstdev(costs) / mean) if mean else 1.0
        if cv > STEADY_CV:
            continue
        m = meta[rid]
        out.append({
            "detector": "rightsizing",
            "resource_id": rid,
            "resource_type": "VM",
            "provider": m.provider_name,
            "region": m.region_name or "",
            "account_id": m.sub_account_id or "",
            "priority": "P2" if monthly < 2000 else "P1",
            "savings": round(monthly * RIGHTSIZE_SAVINGS_RATE, 2),
            "evidence": {
                "detector": "rightsizing",
                "window_days": WINDOW_DAYS,
                "avg_daily_cost": round(mean, 2),
                "monthly_cost": round(monthly, 2),
                "cost_variability_cv": round(cv, 3),
                "assumed_savings_rate": RIGHTSIZE_SAVINGS_RATE,
            },
            "proposed_action": {
                "type": "rightsize",
                "title": f"Rightsize {m.resource_name or rid}",
                "description": (
                    f"Steady-state cost profile (CV {cv:.2f}) at {round(monthly):,} USD/month suggests "
                    f"headroom; one size down saves an estimated "
                    f"{round(monthly * RIGHTSIZE_SAVINGS_RATE):,} USD/month."
                ),
            },
        })
    out.sort(key=lambda f: -f["savings"])
    return out[:MAX_RIGHTSIZE_FINDINGS]


def detect_unused_commitments(db: Session, tenant_id: str) -> list[dict]:
    """Commitment discounts billed but flagged Unused."""
    rows = (
        db.query(
            FocusCost.commitment_discount_id,
            FocusCost.commitment_discount_name,
            FocusCost.provider_name,
            func.sum(FocusCost.effective_cost).label("waste"),
        )
        .filter(
            FocusCost.tenant_id == tenant_id,
            FocusCost.charge_period_start >= _window_start(),
            FocusCost.commitment_discount_status == "Unused",
        )
        .group_by(
            FocusCost.commitment_discount_id,
            FocusCost.commitment_discount_name,
            FocusCost.provider_name,
        )
        .all()
    )
    out = []
    for r in rows:
        monthly = float(r.waste or 0.0) * (30.0 / WINDOW_DAYS)
        if monthly < 50:
            continue
        out.append({
            "detector": "unused_commitments",
            "resource_id": r.commitment_discount_id or "unknown-commitment",
            "resource_type": "CommitmentDiscount",
            "provider": r.provider_name,
            "priority": "P1",
            "savings": round(monthly, 2),
            "evidence": {
                "detector": "unused_commitments",
                "window_days": WINDOW_DAYS,
                "unused_monthly": round(monthly, 2),
                "commitment_name": r.commitment_discount_name,
            },
            "proposed_action": {
                "type": "exchange_or_apply_commitment",
                "title": f"Recover unused commitment {r.commitment_discount_name or r.commitment_discount_id}",
                "description": f"{round(monthly):,} USD/month of committed spend is going unused — "
                               f"exchange, resell, or shift eligible workloads onto it.",
            },
        })
    return out


DETECTORS = [detect_commitment_coverage, detect_rightsizing, detect_unused_commitments]


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/evaluate-costs")
def evaluate_costs(
    current: TokenPayload = Depends(require_permission("recommendations:write")),
    db: Session = Depends(get_db),
):
    """Run all cost detectors; create findings (deduped against open ones)."""
    tenant_id = current.tenant_id
    customer = _default_customer(db, tenant_id)
    existing = _open_finding_keys(db, tenant_id)

    created, skipped = [], 0
    for detector in DETECTORS:
        for c in detector(db, tenant_id):
            key = (c["resource_id"], c["detector"])
            if key in existing:
                skipped += 1
                continue
            f = Finding(
                id=new_id(),
                tenant_id=tenant_id,
                customer_id=customer.id,
                resource_id=c["resource_id"],
                resource_type=c["resource_type"],
                provider=c["provider"],
                account_id=c.get("account_id", ""),
                region=c.get("region", ""),
                state="new",
                priority=c["priority"],
                evidence=c["evidence"],
                proposed_action=c["proposed_action"],
                estimated_savings_monthly=c["savings"],
                confidence_lower=round(c["savings"] * 0.7, 2),
                confidence_upper=round(c["savings"] * 1.15, 2),
            )
            db.add(f)
            existing.add(key)
            created.append({
                "id": f.id, "detector": c["detector"], "resource_id": f.resource_id,
                "provider": f.provider, "priority": f.priority,
                "estimated_savings_monthly": f.estimated_savings_monthly,
                "title": c["proposed_action"]["title"],
            })
    db.commit()

    total = round(sum(c["estimated_savings_monthly"] for c in created), 2)
    record_audit(db, current, action="recommendations.evaluate", resource_type="findings",
                 resource_id="batch", detail={"created": len(created), "skipped_existing": skipped,
                                              "estimated_savings_monthly": total})
    return {
        "status": "ok",
        "created": len(created),
        "skipped_existing": skipped,
        "estimated_savings_monthly": total,
        "findings": created,
    }


@router.get("/summary")
def recommendations_summary(
    current: TokenPayload = Depends(require_permission("recommendations:read")),
    db: Session = Depends(get_db),
):
    rows = db.query(Finding).filter(Finding.tenant_id == current.tenant_id).all()
    by_state, by_detector = defaultdict(int), defaultdict(float)
    for f in rows:
        by_state[f.state] += 1
        by_detector[(f.evidence or {}).get("detector", "other")] += f.estimated_savings_monthly
    open_savings = sum(
        f.estimated_savings_monthly for f in rows
        if f.state not in ("closed", "dismissed", "resolved")
    )
    return {
        "total_findings": len(rows),
        "by_state": dict(by_state),
        "savings_by_detector": {k: round(v, 2) for k, v in by_detector.items()},
        "open_estimated_savings_monthly": round(open_savings, 2),
    }
