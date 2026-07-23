from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from operator import eq, ge, gt, le, lt, ne
from typing import Any, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from .models import Finding, Hypothesis, ProductRate, RecommendationDefinition, SignalSample, utcnow


OPERATORS = {"<": lt, "<=": le, ">": gt, ">=": ge, "==": eq, "!=": ne}


def _as_aware(dt: Optional[datetime]) -> Optional[datetime]:
    """Normalize to a tz-aware (UTC) datetime.

    SQLite doesn't preserve timezone info even for ``DateTime(timezone=True)``
    columns, so values round-tripped through it come back naive. Postgres
    (production) round-trips them tz-aware already. Assume naive == UTC (all
    writes go through ``utcnow()``) so comparisons/subtraction never raise
    "can't compare/subtract offset-naive and offset-aware datetimes".
    """
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)

ACTION_RESOURCE_HINTS = {
    "Shutdown": "vm",
    "RightsizeSku": "vm",
    "SchedulePause": "vm",
    "TierMove": "storage",
    "DeleteOrphan": "volume",
    "VolumeTypeSwap": "volume",
    "CommitmentReview": "vm",
    "TagFix": "resource",
    "BudgetReview": "budget",
    "ModelRoute": "ai_gateway",
    "SpotReview": "vm",
    "LicenseReview": "license",
}


def days_from_window(window: str, default: int = 14) -> int:
    if not window:
        return default
    digits = "".join(ch for ch in window if ch.isdigit())
    if not digits:
        return default
    value = int(digits)
    if "h" in window:
        return max(1, value // 24)
    return max(1, value)


def compile_hypothesis_from_definition(definition: RecommendationDefinition, tenant_id: str) -> Hypothesis:
    return Hypothesis(
        tenant_id=tenant_id,
        definition_id=definition.id,
        name=definition.name,
        description=definition.notes_and_guardrails or definition.basic_engine_support,
        owner_group="finops-admins",
        business_justification=f"Imported from {definition.id}; {definition.end_user_value} customer value.",
        category=definition.category,
        severity=definition.priority,
        scope={"providers": [definition.provider_scope], "environment": "all"},
        signals=definition.primary_metrics,
        conditions=definition.baseline_thresholds,
        action_proposal={
            "type": definition.recommendation_type,
            "delivery_channels": ["manual", "itsm"],
            "guardrails": definition.notes_and_guardrails,
        },
        savings_model={
            "dependency": definition.product_catalog_dependency,
            "compatibility_group": definition.compatibility_group,
            "basis": "product_catalog_rate_delta",
        },
        risk_profile={"complexity": definition.implementation_complexity, "value": definition.end_user_value},
    )


def evaluate_hypothesis(db: Session, hypothesis: Hypothesis, days: int | None = None, persist: bool = True) -> dict[str, Any]:
    window_days = days or max(days_from_window(hypothesis.last_backtest.get("window", "")), 14)
    since = utcnow() - timedelta(days=window_days)
    samples = (
        db.query(SignalSample)
        .filter(SignalSample.tenant_id == hypothesis.tenant_id, SignalSample.sampled_at >= since)
        .all()
    )
    grouped: dict[tuple[str, str], list[SignalSample]] = defaultdict(list)
    for sample in samples:
        if provider_in_scope(sample.provider, hypothesis.scope):
            grouped[(sample.customer_id, sample.resource_id)].append(sample)

    findings: list[dict[str, Any]] = []
    suppressed = 0
    missing_metric_count = 0
    for (customer_id, resource_id), resource_samples in grouped.items():
        sample_by_signal = latest_by_signal(resource_samples)
        evaluation = evaluate_conditions(hypothesis.conditions, sample_by_signal)
        missing_metric_count += len(evaluation["missing"])
        if not evaluation["matched"]:
            continue
        representative = resource_samples[0]
        pricing = price_resource(db, representative)
        estimated = estimate_savings(hypothesis, pricing, representative)
        if estimated <= 0 and requires_positive_savings(hypothesis):
            suppressed += 1
            continue
        finding_payload = {
            "tenant_id": hypothesis.tenant_id,
            "customer_id": customer_id,
            "hypothesis_id": hypothesis.id,
            "definition_id": hypothesis.definition_id,
            "resource_id": resource_id,
            "resource_type": representative.resource_type,
            "provider": representative.provider,
            "account_id": representative.account_id,
            "region": representative.region,
            "priority": hypothesis.severity,
            "owner_group": hypothesis.owner_group,
            "evidence": {
                "matched_conditions": evaluation["matched_conditions"],
                "missing_signals": evaluation["missing"],
                "lookback_days": window_days,
                "sample_count": len(resource_samples),
            },
            "proposed_action": hypothesis.action_proposal,
            "estimated_savings_monthly": round(estimated, 2),
            "confidence_lower": round(estimated * 0.75, 2),
            "confidence_upper": round(estimated * 1.25, 2),
            "pricing_snapshot_id": pricing.get("snapshot_id", ""),
        }
        findings.append(finding_payload)
        if persist:
            upsert_finding(db, finding_payload)
    if persist:
        db.commit()
    coverage = 0 if not grouped else round(max(0, 100 - (missing_metric_count / max(1, len(grouped)) * 8)), 2)
    return {
        "hypothesis_id": hypothesis.id,
        "window_days": window_days,
        "coverage_pct": min(100, coverage),
        "hit_count": len(findings),
        "distinct_resources": len({f["resource_id"] for f in findings}),
        "estimated_savings_monthly": round(sum(f["estimated_savings_monthly"] for f in findings), 2),
        "suppressed_findings": suppressed,
        "missing_metric_count": missing_metric_count,
        "findings": findings[:100],
    }


def evaluate_definition(db: Session, tenant_id: str, definition: RecommendationDefinition, persist: bool = True) -> dict[str, Any]:
    hypothesis = compile_hypothesis_from_definition(definition, tenant_id)
    db.add(hypothesis)
    db.flush()
    result = evaluate_hypothesis(db, hypothesis, days=days_from_window(definition.lookback_window), persist=persist)
    hypothesis.last_backtest = result
    if persist:
        db.commit()
    return result


def evaluate_conditions(conditions: list[dict[str, Any]], sample_by_signal: dict[str, SignalSample]) -> dict[str, Any]:
    if not conditions:
        return {"matched": True, "matched_conditions": [], "missing": []}
    matched_conditions = []
    missing = []
    for condition in conditions:
        signal = condition.get("signal") or condition.get("metric")
        operator = condition.get("operator", "<")
        target = float(condition.get("value", 0))
        sample = sample_by_signal.get(signal)
        if not sample:
            missing.append(signal)
            return {"matched": False, "matched_conditions": matched_conditions, "missing": missing}
        op = OPERATORS.get(operator)
        if not op or not op(float(sample.value), target):
            return {"matched": False, "matched_conditions": matched_conditions, "missing": missing}
        matched_conditions.append(
            {
                "signal": signal,
                "operator": operator,
                "threshold": target,
                "observed": sample.value,
                "unit": sample.unit,
                "sampled_at": sample.sampled_at.isoformat(),
            }
        )
    return {"matched": True, "matched_conditions": matched_conditions, "missing": missing}


def latest_by_signal(samples: list[SignalSample]) -> dict[str, SignalSample]:
    latest: dict[str, SignalSample] = {}
    for sample in samples:
        current = latest.get(sample.signal_name)
        if current is None or sample.sampled_at > current.sampled_at:
            latest[sample.signal_name] = sample
    return latest


def provider_in_scope(provider: str, scope: dict[str, Any]) -> bool:
    providers = [str(item).upper() for item in scope.get("providers", [])]
    if not providers or "FINOPS" in providers or "ALL" in providers:
        return True
    return provider.upper() in providers


def price_resource(db: Session, sample: SignalSample) -> dict[str, Any]:
    rate = (
        db.query(ProductRate)
        .filter(
            func.lower(ProductRate.provider) == sample.provider.lower(),
            ProductRate.sku == sample.sku,
        )
        .first()
    )
    if not rate:
        rate = db.query(ProductRate).filter(func.lower(ProductRate.provider) == sample.provider.lower()).first()
    if not rate:
        return {
            "current_rate": 0.0,
            "target_rate": 0.0,
            "snapshot_id": "",
            "stale": False,
            "days_old": 0,
        }

    # Check if pricing is stale
    stale_after = _as_aware(rate.stale_after)
    effective_at = _as_aware(rate.effective_at)
    is_stale = stale_after is not None and stale_after < utcnow()
    days_old = (utcnow() - effective_at).days if effective_at else 0

    cheaper = (
        db.query(ProductRate)
        .filter(
            ProductRate.provider == rate.provider,
            ProductRate.resource_type == rate.resource_type,
            ProductRate.compatibility_group == rate.compatibility_group,
            ProductRate.rate < rate.rate,
        )
        .order_by(ProductRate.rate.desc())
        .first()
    )
    return {
        "current_rate": rate.rate,
        "target_rate": cheaper.rate if cheaper else rate.rate * 0.5,
        "snapshot_id": rate.snapshot_id,
        "current_sku": rate.sku,
        "target_sku": cheaper.sku if cheaper else "",
        "stale": is_stale,
        "days_old": days_old,
    }


def estimate_savings(hypothesis: Hypothesis, pricing: dict[str, Any], sample: SignalSample) -> float:
    action_type = hypothesis.action_proposal.get("type", "")
    current = float(pricing.get("current_rate", 0))
    target = float(pricing.get("target_rate", 0))
    if action_type == "Shutdown":
        return current * 720
    if action_type in {"RightsizeSku", "TierMove", "VolumeTypeSwap", "ModelRoute"}:
        return max(0, current - target) * 720
    if action_type == "DeleteOrphan":
        return max(current * 720, 8.0)
    if action_type in {"CommitmentReview", "SpotReview"}:
        return max(current * 720 * 0.18, 25.0)
    if action_type in {"TagFix", "BudgetReview", "LicenseReview"}:
        return max(sample.value * 0.05, 10.0)
    return max(current * 720 * 0.1, 5.0)


def requires_positive_savings(hypothesis: Hypothesis) -> bool:
    return hypothesis.action_proposal.get("type") not in {"TagFix", "BudgetReview"}


def upsert_finding(db: Session, payload: dict[str, Any]) -> Finding:
    existing = (
        db.query(Finding)
        .filter(
            Finding.tenant_id == payload["tenant_id"],
            Finding.hypothesis_id == payload["hypothesis_id"],
            Finding.resource_id == payload["resource_id"],
            Finding.state.in_(["new", "snoozed", "approved"]),
        )
        .one_or_none()
    )
    if existing:
        for key, value in payload.items():
            setattr(existing, key, value)
        return existing
    finding = Finding(**payload)
    db.add(finding)
    return finding
