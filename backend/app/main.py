from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import timedelta
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func
from sqlalchemy.orm import Session

from .connectors.base import load_provider_manifests, sync_provider_connections
from .database import Base, engine, get_db
from .services.evaluator import compile_hypothesis_from_definition, evaluate_definition, evaluate_hypothesis
from .jobs.scheduler import audit, run_evaluator, run_metrics_ingest, run_reconciler, run_product_catalog_refresh, start_scheduler
from .models import Action, AuditEvent, Customer, Finding, Hypothesis, JobRun, Outcome, ProductRate, ProviderConnection, RecommendationDefinition, Tenant, utcnow
from .services.recommendation_service import import_catalog
from .schemas import (
    ActionOut,
    BacktestRequest,
    CustomerOut,
    DashboardOut,
    FindingOut,
    FindingTransition,
    HypothesisCreate,
    HypothesisOut,
    HypothesisUpdate,
    ImportResult,
    OutcomeOut,
    ProductRateOut,
    ProviderConnectionOut,
    PublishRequest,
    RecommendationDefinitionOut,
    TenantOut,
)
from .seed.seed_data import seed_everything
from .settings import get_settings
from .api.v1 import get_api_router


settings = get_settings()
scheduler_ref = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global scheduler_ref
    Base.metadata.create_all(bind=engine)
    if settings.seed_on_startup:
        db = next(get_db())
        try:
            await seed_everything(db, settings)
        finally:
            db.close()
    scheduler_ref = start_scheduler(settings)
    yield
    if scheduler_ref:
        scheduler_ref.shutdown(wait=False)


app = FastAPI(title="FinOps Recommendation Engine", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API v1 routes (cost, AWS, Azure, GCP, health, etc.)
api_router = get_api_router()
app.include_router(api_router)

DbSession = Annotated[Session, Depends(get_db)]


@app.get("/health")
def health(db: DbSession) -> dict:
    return {
        "status": "ok",
        "definitions": db.query(RecommendationDefinition).count(),
        "hypotheses": db.query(Hypothesis).count(),
        "findings": db.query(Finding).count(),
        "scheduler": bool(scheduler_ref),
    }


@app.get("/api/tenants", response_model=list[TenantOut])
def list_tenants(db: DbSession):
    return db.query(Tenant).order_by(Tenant.name).all()


@app.get("/api/customers", response_model=list[CustomerOut])
def list_customers(db: DbSession, tenant_id: str = "tenant-demo"):
    return db.query(Customer).filter(Customer.tenant_id == tenant_id).order_by(Customer.name).all()


@app.get("/api/dashboard", response_model=DashboardOut)
def dashboard(db: DbSession, tenant_id: str = "tenant-demo"):
    total_savings = db.query(func.coalesce(func.sum(Finding.estimated_savings_monthly), 0)).filter(Finding.tenant_id == tenant_id).scalar()
    finding_states = dict(
        db.query(Finding.state, func.count(Finding.id)).filter(Finding.tenant_id == tenant_id).group_by(Finding.state).all()
    )
    category_rows = (
        db.query(RecommendationDefinition.category, func.coalesce(func.sum(Finding.estimated_savings_monthly), 0))
        .join(Finding, Finding.definition_id == RecommendationDefinition.id, isouter=True)
        .filter((Finding.tenant_id == tenant_id) | (Finding.tenant_id.is_(None)))
        .group_by(RecommendationDefinition.category)
        .order_by(func.coalesce(func.sum(Finding.estimated_savings_monthly), 0).desc())
        .limit(8)
        .all()
    )
    integrations = db.query(ProviderConnection).filter(ProviderConnection.tenant_id == tenant_id).all()
    audit_events = (
        db.query(AuditEvent).filter(AuditEvent.tenant_id == tenant_id).order_by(AuditEvent.created_at.desc()).limit(10).all()
    )
    return {
        "totals": {
            "recommendation_definitions": db.query(RecommendationDefinition).count(),
            "hypotheses": db.query(Hypothesis).filter(Hypothesis.tenant_id == tenant_id).count(),
            "active_hypotheses": db.query(Hypothesis).filter(Hypothesis.tenant_id == tenant_id, Hypothesis.state == "active").count(),
            "findings": db.query(Finding).filter(Finding.tenant_id == tenant_id).count(),
            "actions": db.query(Action).filter(Action.tenant_id == tenant_id).count(),
            "estimated_monthly_savings": round(float(total_savings or 0), 2),
        },
        "finding_states": finding_states,
        "category_savings": [{"category": row[0] or "Other", "savings": round(float(row[1] or 0), 2)} for row in category_rows],
        "integration_health": [
            {
                "provider_id": item.provider_id,
                "name": item.name,
                "status": item.status,
                "credential_status": item.credential_status,
                "coverage": item.signal_coverage_pct,
                "cost": item.estimated_monthly_cost,
            }
            for item in integrations
        ],
        "recent_audit_events": [
            {
                "actor": event.actor,
                "entity_type": event.entity_type,
                "entity_id": event.entity_id,
                "event_type": event.event_type,
                "created_at": event.created_at.isoformat(),
            }
            for event in audit_events
        ],
    }


@app.get("/api/recommendation-definitions", response_model=list[RecommendationDefinitionOut])
def list_recommendation_definitions(
    db: DbSession,
    category: str | None = None,
    provider: str | None = None,
    priority: str | None = None,
    action_type: str | None = None,
    search: str | None = None,
    limit: int = Query(100, le=1000),
    offset: int = 0,
):
    query = db.query(RecommendationDefinition)
    if category:
        query = query.filter(RecommendationDefinition.category == category)
    if provider:
        query = query.filter(RecommendationDefinition.provider_scope.ilike(f"%{provider}%"))
    if priority:
        query = query.filter(RecommendationDefinition.priority == priority)
    if action_type:
        query = query.filter(RecommendationDefinition.recommendation_type == action_type)
    if search:
        query = query.filter(RecommendationDefinition.name.ilike(f"%{search}%"))
    return query.order_by(RecommendationDefinition.priority, RecommendationDefinition.id).offset(offset).limit(limit).all()


@app.post("/api/recommendation-definitions/import", response_model=ImportResult)
async def import_recommendations(db: DbSession, file: UploadFile | None = File(default=None)):
    if file:
        temp_path = Path("/tmp") / f"finops-{file.filename}"
        temp_path.write_bytes(await file.read())
        result = import_catalog(db, temp_path)
    else:
        result = import_catalog(db, settings.resolve_config_path(settings.catalog_path))
    return result


@app.post("/api/recommendation-definitions/{definition_id}/instantiate", response_model=HypothesisOut)
def instantiate_definition(definition_id: str, db: DbSession, tenant_id: str = "tenant-demo"):
    definition = db.get(RecommendationDefinition, definition_id)
    if not definition:
        raise HTTPException(status_code=404, detail="Recommendation definition not found")
    hypothesis = compile_hypothesis_from_definition(definition, tenant_id)
    db.add(hypothesis)
    db.commit()
    db.refresh(hypothesis)
    audit(db, tenant_id, "system", "hypothesis", hypothesis.id, "created_from_definition", {"definition_id": definition_id})
    return hypothesis


@app.get("/api/hypotheses", response_model=list[HypothesisOut])
def list_hypotheses(db: DbSession, tenant_id: str = "tenant-demo", state: str | None = None):
    query = db.query(Hypothesis).filter(Hypothesis.tenant_id == tenant_id)
    if state:
        query = query.filter(Hypothesis.state == state)
    return query.order_by(Hypothesis.updated_at.desc()).all()


@app.post("/api/hypotheses", response_model=HypothesisOut)
def create_hypothesis(payload: HypothesisCreate, db: DbSession):
    hypothesis = Hypothesis(**payload.model_dump())
    db.add(hypothesis)
    db.commit()
    db.refresh(hypothesis)
    audit(db, hypothesis.tenant_id, "user", "hypothesis", hypothesis.id, "created", {"name": hypothesis.name})
    return hypothesis


@app.get("/api/hypotheses/{hypothesis_id}", response_model=HypothesisOut)
def get_hypothesis(hypothesis_id: str, db: DbSession):
    hypothesis = db.get(Hypothesis, hypothesis_id)
    if not hypothesis:
        raise HTTPException(status_code=404, detail="Hypothesis not found")
    return hypothesis


@app.patch("/api/hypotheses/{hypothesis_id}", response_model=HypothesisOut)
def update_hypothesis(hypothesis_id: str, payload: HypothesisUpdate, db: DbSession):
    hypothesis = db.get(Hypothesis, hypothesis_id)
    if not hypothesis:
        raise HTTPException(status_code=404, detail="Hypothesis not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(hypothesis, key, value)
    hypothesis.version += 1
    db.commit()
    db.refresh(hypothesis)
    audit(db, hypothesis.tenant_id, "user", "hypothesis", hypothesis.id, "updated", {"version": hypothesis.version})
    return hypothesis


@app.post("/api/hypotheses/{hypothesis_id}/backtest")
def backtest_hypothesis(hypothesis_id: str, payload: BacktestRequest, db: DbSession):
    hypothesis = db.get(Hypothesis, hypothesis_id)
    if not hypothesis:
        raise HTTPException(status_code=404, detail="Hypothesis not found")
    result = evaluate_hypothesis(db, hypothesis, days=payload.days, persist=payload.persist_findings)
    hypothesis.last_backtest = result
    db.commit()
    audit(db, hypothesis.tenant_id, "system", "hypothesis", hypothesis.id, "backtest_completed", result)
    return result


@app.post("/api/hypotheses/{hypothesis_id}/publish", response_model=HypothesisOut)
def publish_hypothesis(hypothesis_id: str, payload: PublishRequest, db: DbSession):
    hypothesis = db.get(Hypothesis, hypothesis_id)
    if not hypothesis:
        raise HTTPException(status_code=404, detail="Hypothesis not found")
    if payload.target_state in {"shadow", "active"}:
        backtest = hypothesis.last_backtest or {}
        if not payload.override_reason and (backtest.get("coverage_pct", 0) < 90 or backtest.get("hit_count", 0) < 1):
            raise HTTPException(status_code=422, detail="Backtest gate failed; provide override_reason to publish anyway")
    hypothesis.state = payload.target_state
    db.commit()
    db.refresh(hypothesis)
    audit(
        db,
        hypothesis.tenant_id,
        payload.actor,
        "hypothesis",
        hypothesis.id,
        f"published_{payload.target_state}",
        {"override_reason": payload.override_reason},
    )
    return hypothesis


@app.post("/api/evaluate/run")
async def run_active_evaluator():
    return {"findings": await run_evaluator(settings)}


@app.get("/api/findings", response_model=list[FindingOut])
def list_findings(db: DbSession, tenant_id: str = "tenant-demo", customer_id: str | None = None, state: str | None = None):
    query = db.query(Finding).filter(Finding.tenant_id == tenant_id)
    if customer_id:
        query = query.filter(Finding.customer_id == customer_id)
    if state:
        query = query.filter(Finding.state == state)
    return query.order_by(Finding.created_at.desc()).limit(500).all()


@app.post("/api/findings/{finding_id}/transition", response_model=FindingOut)
def transition_finding(finding_id: str, payload: FindingTransition, db: DbSession):
    finding = db.get(Finding, finding_id)
    if not finding:
        raise HTTPException(status_code=404, detail="Finding not found")
    finding.state = payload.state
    finding.suppression_reason = payload.reason if payload.state in {"dismissed", "snoozed"} else finding.suppression_reason
    if payload.state == "approved":
        action = Action(
            tenant_id=finding.tenant_id,
            finding_id=finding.id,
            action_type=finding.proposed_action.get("type", "ManualReview"),
            delivery_channel=payload.delivery_channel,
            status="approved",
            approver_group=finding.owner_group,
            approved_at=utcnow(),
            payload={
                "resource_id": finding.resource_id,
                "estimated_savings_monthly": finding.estimated_savings_monthly,
                "baseline_cost": finding.estimated_savings_monthly * 2,
                "finding": finding.evidence,
            },
        )
        db.add(action)
    db.commit()
    db.refresh(finding)
    audit(db, finding.tenant_id, payload.actor, "finding", finding.id, f"finding_{payload.state}", {"reason": payload.reason})
    return finding


@app.get("/api/actions", response_model=list[ActionOut])
def list_actions(db: DbSession, tenant_id: str = "tenant-demo"):
    return db.query(Action).filter(Action.tenant_id == tenant_id).order_by(Action.created_at.desc()).all()


@app.post("/api/actions/{action_id}/apply", response_model=ActionOut)
def apply_action(action_id: str, db: DbSession, actor: str = "system"):
    action = db.get(Action, action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")
    action.status = "applied"
    action.applied_at = utcnow()
    finding = db.get(Finding, action.finding_id)
    if finding:
        finding.state = "applied"
    db.commit()
    db.refresh(action)
    audit(db, action.tenant_id, actor, "action", action.id, "action_applied", {})
    return action


@app.get("/api/outcomes", response_model=list[OutcomeOut])
def list_outcomes(db: DbSession, tenant_id: str = "tenant-demo"):
    return db.query(Outcome).filter(Outcome.tenant_id == tenant_id).order_by(Outcome.created_at.desc()).all()


@app.post("/api/reconciler/run")
async def run_reconciler_now():
    return {"outcomes": await run_reconciler(settings)}


@app.get("/api/integrations", response_model=list[ProviderConnectionOut])
def list_integrations(db: DbSession, tenant_id: str = "tenant-demo"):
    return db.query(ProviderConnection).filter(ProviderConnection.tenant_id == tenant_id).order_by(ProviderConnection.category, ProviderConnection.name).all()


@app.get("/api/integrations/manifests")
def integration_manifests():
    manifests = load_provider_manifests(settings.resolve_config_path(settings.provider_registry_path))
    return [manifest.__dict__ for manifest in manifests]


@app.post("/api/integrations/sync", response_model=list[ProviderConnectionOut])
async def sync_integrations(db: DbSession, tenant_id: str = "tenant-demo"):
    manifests = load_provider_manifests(settings.resolve_config_path(settings.provider_registry_path))
    return await sync_provider_connections(db, tenant_id, manifests)


@app.post("/api/ingestion/run")
async def run_ingestion_now():
    return {"records": await run_metrics_ingest(settings)}


@app.get("/api/product-catalog", response_model=list[ProductRateOut])
def product_catalog(
    db: DbSession,
    provider: str | None = None,
    resource_type: str | None = None,
    region: str | None = None,
    search: str | None = None,
):
    query = db.query(ProductRate)
    if provider:
        query = query.filter(ProductRate.provider == provider)
    if resource_type:
        query = query.filter(ProductRate.resource_type == resource_type)
    if region:
        query = query.filter(ProductRate.region == region)
    if search:
        query = query.filter(ProductRate.sku.ilike(f"%{search}%"))
    return query.order_by(ProductRate.provider, ProductRate.resource_type, ProductRate.rate).limit(500).all()


@app.get("/api/product-catalog/compare")
def compare_rates(db: DbSession, source_sku: str, target_sku: str, provider: str | None = None):
    query = db.query(ProductRate).filter(ProductRate.sku.in_([source_sku, target_sku]))
    if provider:
        query = query.filter(ProductRate.provider == provider)
    rows = query.all()
    by_sku = {row.sku: row for row in rows}
    source = by_sku.get(source_sku)
    target = by_sku.get(target_sku)
    if not source or not target:
        raise HTTPException(status_code=404, detail="Source or target SKU not found")
    compatible = source.compatibility_group == target.compatibility_group
    monthly_delta = max(0, source.rate - target.rate) * 720
    return {
        "source": source,
        "target": target,
        "compatible": compatible,
        "monthly_savings": round(monthly_delta, 2),
        "confidence_band": {"lower": round(monthly_delta * 0.75, 2), "upper": round(monthly_delta * 1.25, 2)},
        "snapshot_id": source.snapshot_id,
    }


@app.get("/api/customers/{customer_id}/recommendations")
def customer_recommendations(customer_id: str, db: DbSession, tenant_id: str = "tenant-demo"):
    customer = db.get(Customer, customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    findings = (
        db.query(Finding)
        .filter(Finding.tenant_id == tenant_id, Finding.customer_id == customer_id)
        .order_by(Finding.estimated_savings_monthly.desc())
        .all()
    )
    return {
        "customer": CustomerOut.model_validate(customer),
        "findings": [FindingOut.model_validate(finding) for finding in findings],
        "estimated_monthly_savings": round(sum(f.estimated_savings_monthly for f in findings), 2),
    }


@app.get("/api/jobs")
def list_jobs(db: DbSession):
    runs = db.query(JobRun).order_by(JobRun.started_at.desc()).limit(100).all()
    schedule_jobs = []
    if scheduler_ref:
        schedule_jobs = [{"id": job.id, "next_run_time": str(job.next_run_time), "trigger": str(job.trigger)} for job in scheduler_ref.get_jobs()]
    return {
        "schedules": schedule_jobs,
        "runs": [
            {
                "job_name": run.job_name,
                "status": run.status,
                "started_at": run.started_at.isoformat(),
                "finished_at": run.finished_at.isoformat() if run.finished_at else None,
                "records_processed": run.records_processed,
                "details": run.details,
            }
            for run in runs
        ],
    }


@app.post("/api/recommendation-definitions/{definition_id}/evaluate")
def evaluate_definition_now(definition_id: str, db: DbSession, tenant_id: str = "tenant-demo", persist: bool = True):
    definition = db.get(RecommendationDefinition, definition_id)
    if not definition:
        raise HTTPException(status_code=404, detail="Recommendation definition not found")
    return evaluate_definition(db, tenant_id, definition, persist=persist)


@app.post("/api/product-catalog/refresh")
async def refresh_product_catalog(provider: str | None = None):
    """Manually trigger product catalog refresh for AWS, Azure, and GCP."""
    result = await run_product_catalog_refresh(settings)
    if provider:
        filtered_result = {
            k: v for k, v in result.get("results", {}).items()
            if k.lower() == provider.lower()
        }
        if not filtered_result:
            raise HTTPException(status_code=404, detail=f"Provider {provider} not found")
        return {
            "status": "success",
            "provider": provider,
            "details": filtered_result.get(provider.lower(), {}),
        }
    return result
