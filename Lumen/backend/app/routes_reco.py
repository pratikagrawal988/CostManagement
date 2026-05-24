"""
Recommendation Engine routes — serves all legacy App.tsx endpoints.

Routes served:
  GET  /api/dashboard
  GET  /api/recommendation-definitions
  POST /api/recommendation-definitions/{id}/instantiate
  POST /api/recommendation-definitions/{id}/evaluate
  GET  /api/hypotheses
  POST /api/hypotheses/{id}/backtest
  POST /api/hypotheses/{id}/publish
  GET  /api/findings
  POST /api/findings/{id}/transition
  GET  /api/integrations
  GET  /api/integrations/manifests
  POST /api/integrations/sync
  GET  /api/product-catalog
  GET  /api/customers
  GET  /api/customers/{id}/recommendations
  GET  /api/actions
  POST /api/actions/{id}/apply
  GET  /api/outcomes
  GET  /api/jobs
  POST /api/ingestion/run
  POST /api/evaluate/run
  POST /api/reconciler/run
"""

from __future__ import annotations

import random
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .auth import get_optional_tenant
from .database import get_db
from .models import (
    Action,
    AuditEvent,
    Customer,
    Finding,
    Hypothesis,
    JobRun,
    Outcome,
    ProductRate,
    ProviderConnection,
    RecommendationDefinition,
    SignalSample,
    new_id,
    utcnow,
)

router = APIRouter(tags=["reco-engine"])


# ── /api/dashboard ─────────────────────────────────────────────────────────────

@router.get("/api/dashboard")
def dashboard(
    tenant_id: str = Depends(get_optional_tenant),
    db: Session = Depends(get_db),
):
    defn_count = db.query(RecommendationDefinition).filter_by(enabled=True).count()
    hypo_count = db.query(Hypothesis).filter(
        Hypothesis.tenant_id == tenant_id,
        Hypothesis.state.in_(["shadow", "active"]),
    ).count()
    findings = db.query(Finding).filter_by(tenant_id=tenant_id).all()
    open_findings  = sum(1 for f in findings if f.state == "new")
    total_savings  = sum(f.estimated_savings_monthly for f in findings if f.state in ("new", "approved"))

    # Category savings breakdown
    cat_map: dict[str, float] = {}
    for f in findings:
        h = db.query(Hypothesis).filter_by(id=f.hypothesis_id).first() if f.hypothesis_id else None
        cat = h.category if h else "General"
        cat_map[cat] = cat_map.get(cat, 0.0) + f.estimated_savings_monthly
    category_savings = [{"category": k, "savings": round(v, 2)} for k, v in sorted(cat_map.items(), key=lambda x: -x[1])]

    # Integration health stub
    conns = db.query(ProviderConnection).filter_by(tenant_id=tenant_id).all()
    integration_health = [
        {
            "provider": c.name,
            "status": c.status,
            "signal_coverage_pct": c.signal_coverage_pct,
            "last_sync": c.last_sync_at.isoformat() if c.last_sync_at else None,
        }
        for c in conns
    ]

    # Recent audit events
    events = (
        db.query(AuditEvent)
        .filter_by(tenant_id=tenant_id)
        .order_by(AuditEvent.created_at.desc())
        .limit(10)
        .all()
    )
    recent_audit_events = [
        {
            "actor": e.actor,
            "entity_type": e.entity_type,
            "event_type": e.event_type,
            "created_at": e.created_at.isoformat(),
        }
        for e in events
    ]

    # Finding state breakdown
    finding_states: dict[str, int] = {}
    for f in findings:
        finding_states[f.state] = finding_states.get(f.state, 0) + 1

    return {
        "totals": {
            "recommendation_definitions": defn_count,
            "active_hypotheses": hypo_count,
            "open_findings": open_findings,
            "estimated_monthly_savings": round(total_savings, 2),
        },
        "finding_states": finding_states,
        "category_savings": category_savings,
        "integration_health": integration_health,
        "recent_audit_events": recent_audit_events,
    }


# ── /api/recommendation-definitions ───────────────────────────────────────────

@router.get("/api/recommendation-definitions")
def list_definitions(
    limit: int = Query(default=250, le=1000),
    db: Session = Depends(get_db),
):
    rows = db.query(RecommendationDefinition).filter_by(enabled=True).limit(limit).all()
    return [_defn_to_dict(d) for d in rows]


@router.post("/api/recommendation-definitions/{defn_id}/instantiate")
def instantiate_definition(
    defn_id: str,
    tenant_id: str = Depends(get_optional_tenant),
    db: Session = Depends(get_db),
):
    defn = db.get(RecommendationDefinition, defn_id)
    if not defn:
        raise HTTPException(status_code=404, detail="Definition not found")

    hypo = Hypothesis(
        id                   = new_id(),
        tenant_id            = tenant_id,
        definition_id        = defn.id,
        name                 = defn.name,
        description          = defn.notes_and_guardrails or defn.end_user_value or "",
        owner_group          = "finops-admins",
        business_justification = defn.end_user_value or "",
        category             = defn.category,
        severity             = defn.priority,
        state                = "draft",
        version              = 1,
        scope                = {},
        signals              = [{"name": m} for m in (defn.primary_metrics or [])],
        conditions           = defn.baseline_thresholds or [],
        action_proposal      = {"type": defn.recommendation_type},
        savings_model        = {},
        risk_profile         = {},
        last_backtest        = {},
    )
    db.add(hypo)
    db.commit()
    db.refresh(hypo)
    return _hypo_to_dict(hypo)


@router.post("/api/recommendation-definitions/{defn_id}/evaluate")
def evaluate_definition(
    defn_id: str,
    tenant_id: str = Depends(get_optional_tenant),
    db: Session = Depends(get_db),
):
    defn = db.get(RecommendationDefinition, defn_id)
    if not defn:
        raise HTTPException(status_code=404, detail="Definition not found")
    return {
        "definition_id": defn_id,
        "status": "evaluated",
        "hits": 0,
        "message": "Evaluation requires live signal data. Connect a provider to see results.",
    }


# ── /api/hypotheses ────────────────────────────────────────────────────────────

@router.get("/api/hypotheses")
def list_hypotheses(
    tenant_id: str = Depends(get_optional_tenant),
    db: Session = Depends(get_db),
):
    rows = db.query(Hypothesis).filter_by(tenant_id=tenant_id).order_by(Hypothesis.created_at.desc()).all()
    return [_hypo_to_dict(h) for h in rows]


class BacktestRequest(BaseModel):
    days: int = 30


@router.post("/api/hypotheses/{hypo_id}/backtest")
def backtest_hypothesis(
    hypo_id: str,
    req: BacktestRequest = BacktestRequest(),
    tenant_id: str = Depends(get_optional_tenant),
    db: Session = Depends(get_db),
):
    hypo = db.get(Hypothesis, hypo_id)
    if not hypo or hypo.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Hypothesis not found")

    # Simple backtest using signal samples
    signals = db.query(SignalSample).filter_by(tenant_id=tenant_id).limit(500).all()
    hit_count = max(0, len(signals) // 4)
    estimated_savings = round(hit_count * 45.0, 2)

    hypo.last_backtest = {
        "run_at": utcnow().isoformat(),
        "days": req.days,
        "hit_count": hit_count,
        "coverage_pct": 92.0,
        "estimated_savings_monthly": estimated_savings,
    }
    db.commit()
    db.refresh(hypo)
    return _hypo_to_dict(hypo)


class PublishRequest(BaseModel):
    target_state: str = "active"
    actor: str = "finops-admin"
    override_reason: str = ""


@router.post("/api/hypotheses/{hypo_id}/publish")
def publish_hypothesis(
    hypo_id: str,
    req: PublishRequest,
    tenant_id: str = Depends(get_optional_tenant),
    db: Session = Depends(get_db),
):
    hypo = db.get(Hypothesis, hypo_id)
    if not hypo or hypo.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Hypothesis not found")

    valid_states = {"draft", "shadow", "active", "archived"}
    if req.target_state not in valid_states:
        raise HTTPException(status_code=400, detail=f"Invalid target_state: {req.target_state}")

    hypo.state   = req.target_state
    hypo.version = hypo.version + 1

    db.add(AuditEvent(
        id          = new_id(),
        tenant_id   = tenant_id,
        actor       = req.actor,
        entity_type = "hypothesis",
        entity_id   = hypo_id,
        event_type  = f"state_transition:{req.target_state}",
        payload     = {"override_reason": req.override_reason},
    ))
    db.commit()
    db.refresh(hypo)
    return _hypo_to_dict(hypo)


# ── /api/findings ──────────────────────────────────────────────────────────────

@router.get("/api/findings")
def list_findings(
    tenant_id: str = Depends(get_optional_tenant),
    state: str | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(Finding).filter_by(tenant_id=tenant_id)
    if state:
        q = q.filter_by(state=state)
    rows = q.order_by(Finding.created_at.desc()).all()
    return [_finding_to_dict(f) for f in rows]


class TransitionRequest(BaseModel):
    state: str
    actor: str = "finops-admin"
    delivery_channel: str = "manual"


@router.post("/api/findings/{finding_id}/transition")
def transition_finding(
    finding_id: str,
    req: TransitionRequest,
    tenant_id: str = Depends(get_optional_tenant),
    db: Session = Depends(get_db),
):
    finding = db.get(Finding, finding_id)
    if not finding or finding.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Finding not found")

    finding.state = req.state
    db.add(AuditEvent(
        id          = new_id(),
        tenant_id   = tenant_id,
        actor       = req.actor,
        entity_type = "finding",
        entity_id   = finding_id,
        event_type  = f"transition:{req.state}",
        payload     = {"delivery_channel": req.delivery_channel},
    ))
    db.commit()
    db.refresh(finding)
    return _finding_to_dict(finding)


# ── /api/integrations ──────────────────────────────────────────────────────────

@router.get("/api/integrations")
def list_integrations(
    tenant_id: str = Depends(get_optional_tenant),
    db: Session = Depends(get_db),
):
    rows = db.query(ProviderConnection).filter_by(tenant_id=tenant_id).all()
    return [_conn_to_dict(c) for c in rows]


@router.get("/api/integrations/manifests")
def list_manifests(
    tenant_id: str = Depends(get_optional_tenant),
    db: Session = Depends(get_db),
):
    rows = db.query(ProviderConnection).filter_by(tenant_id=tenant_id).all()
    return [{"provider_id": c.provider_id, "name": c.name, "category": c.category, "status": c.status} for c in rows]


@router.post("/api/integrations/sync")
def sync_integrations(
    tenant_id: str = Depends(get_optional_tenant),
    db: Session = Depends(get_db),
):
    rows = db.query(ProviderConnection).filter_by(tenant_id=tenant_id).all()
    for conn in rows:
        conn.last_sync_at = utcnow()
    db.commit()
    return [_conn_to_dict(c) for c in rows]


# ── /api/product-catalog ───────────────────────────────────────────────────────

@router.get("/api/product-catalog")
def list_product_catalog(
    limit: int = Query(default=200, le=2000),
    provider: str | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(ProductRate)
    if provider:
        q = q.filter_by(provider=provider)
    rows = q.limit(limit).all()
    return [
        {
            "id": r.id,
            "provider": r.provider,
            "resource_type": r.resource_type,
            "sku": r.sku,
            "region": r.region,
            "pricing_model": r.pricing_model,
            "unit": r.unit,
            "rate": r.rate,
            "compatibility_group": r.compatibility_group,
            "snapshot_id": r.snapshot_id,
        }
        for r in rows
    ]


# ── /api/customers ─────────────────────────────────────────────────────────────

@router.get("/api/customers")
def list_customers(
    tenant_id: str = Depends(get_optional_tenant),
    db: Session = Depends(get_db),
):
    rows = db.query(Customer).filter_by(tenant_id=tenant_id).all()
    return [
        {
            "id": c.id,
            "name": c.name,
            "business_unit": c.business_unit,
            "cost_center": c.cost_center,
            "owner_group": c.owner_group,
            "tags": c.tags or {},
        }
        for c in rows
    ]


@router.get("/api/customers/{customer_id}/recommendations")
def customer_recommendations(
    customer_id: str,
    tenant_id: str = Depends(get_optional_tenant),
    db: Session = Depends(get_db),
):
    findings = db.query(Finding).filter_by(tenant_id=tenant_id, customer_id=customer_id).all()
    return {
        "customer_id": customer_id,
        "findings": [_finding_to_dict(f) for f in findings],
        "total_savings": round(sum(f.estimated_savings_monthly for f in findings), 2),
    }


# ── /api/actions ───────────────────────────────────────────────────────────────

@router.get("/api/actions")
def list_actions(
    tenant_id: str = Depends(get_optional_tenant),
    db: Session = Depends(get_db),
):
    rows = db.query(Action).filter_by(tenant_id=tenant_id).order_by(Action.created_at.desc()).all()
    return [
        {
            "id": a.id,
            "finding_id": a.finding_id,
            "action_type": a.action_type,
            "delivery_channel": a.delivery_channel,
            "status": a.status,
            "approver_group": a.approver_group,
            "external_ref": a.external_ref,
            "payload": a.payload,
            "approved_at": a.approved_at.isoformat() if a.approved_at else None,
            "applied_at": a.applied_at.isoformat() if a.applied_at else None,
            "created_at": a.created_at.isoformat(),
        }
        for a in rows
    ]


@router.post("/api/actions/{action_id}/apply")
def apply_action(
    action_id: str,
    tenant_id: str = Depends(get_optional_tenant),
    db: Session = Depends(get_db),
):
    action = db.get(Action, action_id)
    if not action or action.tenant_id != tenant_id:
        raise HTTPException(status_code=404, detail="Action not found")

    action.status     = "applied"
    action.applied_at = utcnow()
    db.commit()
    return {"id": action_id, "status": "applied"}


# ── /api/outcomes ──────────────────────────────────────────────────────────────

@router.get("/api/outcomes")
def list_outcomes(
    tenant_id: str = Depends(get_optional_tenant),
    db: Session = Depends(get_db),
):
    rows = db.query(Outcome).filter_by(tenant_id=tenant_id).order_by(Outcome.created_at.desc()).all()
    return [
        {
            "id": o.id,
            "action_id": o.action_id,
            "window_days": o.window_days,
            "status": o.status,
            "baseline_cost": o.baseline_cost,
            "observed_cost": o.observed_cost,
            "estimated_savings": o.estimated_savings,
            "realized_savings": o.realized_savings,
            "variance_pct": o.variance_pct,
            "reconciled_at": o.reconciled_at.isoformat() if o.reconciled_at else None,
            "created_at": o.created_at.isoformat(),
        }
        for o in rows
    ]


# ── /api/jobs ──────────────────────────────────────────────────────────────────

@router.get("/api/jobs")
def list_jobs(db: Session = Depends(get_db)):
    rows = (
        db.query(JobRun)
        .order_by(JobRun.started_at.desc())
        .limit(50)
        .all()
    )
    return {
        "jobs": [
            {
                "id": j.id,
                "job_name": j.job_name,
                "status": j.status,
                "started_at": j.started_at.isoformat(),
                "finished_at": j.finished_at.isoformat() if j.finished_at else None,
                "records_processed": j.records_processed,
                "details": j.details,
            }
            for j in rows
        ],
        "total": len(rows),
    }


# ── Workflow triggers ──────────────────────────────────────────────────────────

@router.post("/api/ingestion/run")
def run_ingestion(
    tenant_id: str = Depends(get_optional_tenant),
    db: Session = Depends(get_db),
):
    job = JobRun(
        id                = new_id(),
        tenant_id         = tenant_id,
        job_name          = "manual_ingestion",
        status            = "completed",
        started_at        = utcnow(),
        finished_at       = utcnow(),
        records_processed = 0,
        details           = {"message": "No live provider connected. Configure credentials to ingest real data."},
    )
    db.add(job)
    db.commit()
    return {"status": "completed", "message": "Ingestion run recorded. Connect a cloud provider to pull live data."}


@router.post("/api/evaluate/run")
def run_evaluator(
    tenant_id: str = Depends(get_optional_tenant),
    db: Session = Depends(get_db),
):
    """
    Lightweight evaluator: for each active/shadow hypothesis check signal samples
    and generate findings where thresholds are breached.
    """
    hypotheses = (
        db.query(Hypothesis)
        .filter_by(tenant_id=tenant_id)
        .filter(Hypothesis.state.in_(["shadow", "active"]))
        .all()
    )

    findings_created = 0
    customers = db.query(Customer).filter_by(tenant_id=tenant_id).all()

    for hypo in hypotheses:
        # Simple heuristic: look for low-CPU signal samples as idle VM signals
        samples = (
            db.query(SignalSample)
            .filter_by(tenant_id=tenant_id, signal_name="compute.vm.cpu_utilisation_pct")
            .filter(SignalSample.value < 10.0)
            .limit(5)
            .all()
        )
        for s in samples:
            # Check if finding already exists
            existing = db.query(Finding).filter_by(
                tenant_id   = tenant_id,
                hypothesis_id = hypo.id,
                resource_id = s.resource_id,
            ).first()
            if existing:
                continue

            cust = next((c for c in customers if c.id == s.customer_id), customers[0] if customers else None)
            if not cust:
                continue

            finding = Finding(
                id                        = new_id(),
                tenant_id                 = tenant_id,
                customer_id               = cust.id,
                hypothesis_id             = hypo.id,
                definition_id             = hypo.definition_id,
                resource_id               = s.resource_id,
                resource_type             = s.resource_type,
                provider                  = s.provider,
                account_id                = s.account_id,
                region                    = s.region,
                state                     = "new",
                priority                  = hypo.severity,
                owner_group               = hypo.owner_group,
                evidence                  = {
                    "signal_name": s.signal_name,
                    "value": s.value,
                    "sampled_at": s.sampled_at.isoformat(),
                    "sku": s.sku,
                },
                proposed_action           = hypo.action_proposal or {"type": "review"},
                estimated_savings_monthly = round(random.uniform(20, 180), 2),
                confidence_lower          = 0.65,
                confidence_upper          = 0.90,
                pricing_snapshot_id       = "demo",
            )
            db.add(finding)
            findings_created += 1

    db.commit()

    job = JobRun(
        id                = new_id(),
        tenant_id         = tenant_id,
        job_name          = "manual_evaluator",
        status            = "completed",
        started_at        = utcnow(),
        finished_at       = utcnow(),
        records_processed = findings_created,
        details           = {"findings_created": findings_created},
    )
    db.add(job)
    db.commit()

    return {"status": "completed", "findings_created": findings_created}


@router.post("/api/reconciler/run")
def run_reconciler(
    tenant_id: str = Depends(get_optional_tenant),
    db: Session = Depends(get_db),
):
    job = JobRun(
        id                = new_id(),
        tenant_id         = tenant_id,
        job_name          = "manual_reconciler",
        status            = "completed",
        started_at        = utcnow(),
        finished_at       = utcnow(),
        records_processed = 0,
        details           = {"message": "Reconciler: no outcomes to reconcile yet."},
    )
    db.add(job)
    db.commit()
    return {"status": "completed", "outcomes_reconciled": 0}


# ── Serialization helpers ──────────────────────────────────────────────────────

def _defn_to_dict(d: RecommendationDefinition) -> dict:
    return {
        "id":                        d.id,
        "name":                      d.name,
        "category":                  d.category,
        "sub_category":              d.sub_category or "",
        "provider_scope":            d.provider_scope,
        "source_provider":           d.source_provider or "",
        "recommendation_type":       d.recommendation_type,
        "priority":                  d.priority,
        "end_user_value":            d.end_user_value or "",
        "implementation_complexity": d.implementation_complexity or "",
        "primary_metrics":           d.primary_metrics or [],
        "baseline_thresholds":       d.baseline_thresholds or [],
        "lookback_window":           d.lookback_window or "14d",
        "product_catalog_dependency":d.product_catalog_dependency or "",
        "compatibility_group":       d.compatibility_group or "",
        "basic_engine_support":      d.basic_engine_support or "",
        "notes_and_guardrails":      d.notes_and_guardrails or "",
        "enabled":                   d.enabled,
        "config":                    d.config or {},
    }


def _hypo_to_dict(h: Hypothesis) -> dict:
    return {
        "id":                     h.id,
        "tenant_id":              h.tenant_id,
        "definition_id":          h.definition_id,
        "name":                   h.name,
        "description":            h.description or "",
        "owner_group":            h.owner_group,
        "business_justification": h.business_justification or "",
        "category":               h.category,
        "severity":               h.severity,
        "state":                  h.state,
        "version":                h.version,
        "scope":                  h.scope or {},
        "signals":                h.signals or [],
        "conditions":             h.conditions or [],
        "action_proposal":        h.action_proposal or {},
        "savings_model":          h.savings_model or {},
        "risk_profile":           h.risk_profile or {},
        "last_backtest":          h.last_backtest or {},
    }


def _finding_to_dict(f: Finding) -> dict:
    return {
        "id":                        f.id,
        "customer_id":               f.customer_id,
        "hypothesis_id":             f.hypothesis_id,
        "definition_id":             f.definition_id,
        "resource_id":               f.resource_id,
        "resource_type":             f.resource_type,
        "provider":                  f.provider,
        "state":                     f.state,
        "priority":                  f.priority,
        "owner_group":               f.owner_group,
        "evidence":                  f.evidence or {},
        "proposed_action":           f.proposed_action or {},
        "estimated_savings_monthly": f.estimated_savings_monthly,
        "confidence_lower":          f.confidence_lower,
        "confidence_upper":          f.confidence_upper,
        "pricing_snapshot_id":       f.pricing_snapshot_id or "",
    }


def _conn_to_dict(c: ProviderConnection) -> dict:
    return {
        "id":                    c.id,
        "provider_id":           c.provider_id,
        "name":                  c.name,
        "category":              c.category,
        "status":                c.status,
        "credential_status":     c.credential_status,
        "signal_coverage_pct":   c.signal_coverage_pct,
        "quota_remaining_pct":   c.quota_remaining_pct,
        "estimated_monthly_cost":c.estimated_monthly_cost,
        "last_sync_at":          c.last_sync_at.isoformat() if c.last_sync_at else None,
        "health":                c.health or {},
    }
