"""
Tag management — policy, normalization, and prediction (Phase 14).

Endpoints:
  GET    /api/tags/policy                      → tenant tag policy (auto-created empty)
  PUT    /api/tags/policy                       → replace required/recommended keys
  GET    /api/tags/resources                    → resource inventory + compliance status
  GET    /api/tags/compliance/summary           → tenant-wide compliance scorecard
  GET    /api/tags/normalize/keys               → clustered key-variant suggestions
  POST   /api/tags/normalize/keys/apply         → save alias + bulk rewrite matching rows
  GET    /api/tags/normalize/values             → clustered value-variant suggestions for a key
  POST   /api/tags/normalize/values/apply       → save alias + bulk rewrite matching rows
  POST   /api/tags/predictions/generate         → run heuristics, store TagPrediction rows
  GET    /api/tags/predictions                  → list predictions
  POST   /api/tags/predictions/{id}/approve     → write ResourceTagOverride, mark applied
  POST   /api/tags/predictions/{id}/reject      → mark rejected

Resource inventory and predictions are computed from FocusCost (the FOCUS-
normalized cost table) — the same data source dashboards already use — with
ResourceTagOverride layered on top so approved/normalized values are
reflected immediately, without waiting for the next ingestion cycle.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from .auth import TokenPayload
from .database import get_db
from .models import (
    FocusCost, ResourceTagOverride, TagKeyAlias, TagPolicy, TagPrediction,
    TagValueAlias, new_id, utcnow,
)
from .rbac import record_audit, require_permission

router = APIRouter(prefix="/api/tags", tags=["tags"])

CHARGEBACK_KEYS = ["Team", "CostCenter", "Environment", "AppId"]
_X_COL_FOR_KEY = {
    "Team": "x_team", "CostCenter": "x_cost_center",
    "Environment": "x_environment", "AppId": "x_app_id",
}


# ── Normalization helpers ─────────────────────────────────────────────────────

def _norm_form(s: str) -> str:
    """Collapse a raw string to a comparable normalized form: lowercase,
    separators unified, punctuation stripped."""
    s = (s or "").strip().lower()
    s = re.sub(r"[\s\-_]+", "_", s)
    s = re.sub(r"[^a-z0-9_]", "", s)
    return s


def _default_window(days: int = 30) -> tuple[str, str]:
    end = date.today()
    start = end - timedelta(days=days)
    return start.isoformat(), end.isoformat()


# ── Schemas ───────────────────────────────────────────────────────────────────

class TagKeyDef(BaseModel):
    key: str
    level: str = "required"        # required | recommended
    description: str = ""
    allowed_values: list[str] = []


class TagPolicyRequest(BaseModel):
    required_keys: list[TagKeyDef]


class KeyAliasApplyRequest(BaseModel):
    canonical_key: str
    aliases: list[str]
    bulk_apply: bool = True


class ValueAliasApplyRequest(BaseModel):
    tag_key: str
    canonical_value: str
    aliases: list[str]
    bulk_apply: bool = True


class PredictionGenerateRequest(BaseModel):
    tag_keys: list[str] = []   # empty = all policy required/recommended keys
    days: int = 30


# ── Policy ────────────────────────────────────────────────────────────────────

def _get_or_create_policy(db: Session, tenant_id: str) -> TagPolicy:
    p = db.query(TagPolicy).filter(TagPolicy.tenant_id == tenant_id).one_or_none()
    if not p:
        p = TagPolicy(id=new_id(), tenant_id=tenant_id, required_keys=[
            {"key": "Team", "level": "required", "description": "Owning team", "allowed_values": []},
            {"key": "CostCenter", "level": "required", "description": "Chargeback cost center", "allowed_values": []},
            {"key": "Environment", "level": "recommended", "description": "Deployment environment",
             "allowed_values": ["production", "staging", "development"]},
        ])
        db.add(p)
        db.commit()
        db.refresh(p)
    return p


@router.get("/policy")
def get_policy(
    current: TokenPayload = Depends(require_permission("tags:read")),
    db: Session = Depends(get_db),
):
    p = _get_or_create_policy(db, current.tenant_id)
    return {
        "id": p.id,
        "required_keys": p.required_keys,
        "updated_at": p.updated_at.isoformat(),
    }


@router.put("/policy")
def set_policy(
    req: TagPolicyRequest,
    current: TokenPayload = Depends(require_permission("tags:write")),
    db: Session = Depends(get_db),
):
    for k in req.required_keys:
        if k.level not in ("required", "recommended"):
            raise HTTPException(400, "level must be 'required' or 'recommended'")
    p = _get_or_create_policy(db, current.tenant_id)
    p.required_keys = [k.model_dump() for k in req.required_keys]
    p.updated_at = utcnow()
    db.commit()
    db.refresh(p)
    record_audit(db, current, action="tag_policy.update", resource_type="tag_policy",
                 resource_id=p.id, detail={"keys": [k.key for k in req.required_keys]})
    return {"status": "updated", "required_keys": p.required_keys}


# ── Resource inventory ────────────────────────────────────────────────────────

def _fetch_resource_rows(db: Session, tenant_id: str, start: str, end: str) -> list[FocusCost]:
    return (
        db.query(FocusCost)
        .filter(
            FocusCost.tenant_id == tenant_id,
            FocusCost.billing_period_start >= start,
            FocusCost.billing_period_start <= end,
            FocusCost.resource_id != "",
        )
        .all()
    )


def _overrides_by_resource(db: Session, tenant_id: str) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = defaultdict(dict)
    for o in db.query(ResourceTagOverride).filter(ResourceTagOverride.tenant_id == tenant_id).all():
        out[o.resource_id][o.tag_key] = o.tag_value
    return out


def _build_inventory(db: Session, tenant_id: str, start: str, end: str) -> list[dict]:
    rows = _fetch_resource_rows(db, tenant_id, start, end)
    overrides = _overrides_by_resource(db, tenant_id)

    by_resource: dict[str, dict] = {}
    for r in rows:
        entry = by_resource.get(r.resource_id)
        if entry is None:
            entry = {
                "resource_id": r.resource_id,
                "resource_name": r.resource_name or r.resource_id,
                "provider": r.provider_name,
                "service": r.service_name,
                "region": r.region_name,
                "sub_account_id": r.sub_account_id,
                "tags": dict(r.tags or {}),
                "chargeback": {
                    "Team": r.x_team, "CostCenter": r.x_cost_center,
                    "Environment": r.x_environment, "AppId": r.x_app_id,
                },
                "total_cost": 0.0,
                "_latest": r.transformed_at,
            }
            by_resource[r.resource_id] = entry
        entry["total_cost"] += float(r.effective_cost or 0.0)
        if r.transformed_at and (entry["_latest"] is None or r.transformed_at > entry["_latest"]):
            entry["_latest"] = r.transformed_at
            entry["tags"] = dict(r.tags or {})
            entry["chargeback"] = {
                "Team": r.x_team, "CostCenter": r.x_cost_center,
                "Environment": r.x_environment, "AppId": r.x_app_id,
            }

    # Layer overrides on top (applied predictions / normalization / manual edits)
    for resource_id, entry in by_resource.items():
        ov = overrides.get(resource_id, {})
        for key, value in ov.items():
            entry["tags"][key] = value
            if key in entry["chargeback"]:
                entry["chargeback"][key] = value
        entry.pop("_latest", None)

    return list(by_resource.values())


def _compliance_status(entry: dict, policy_keys: list[dict]) -> dict:
    missing_required, missing_recommended = [], []
    chargeback = entry["chargeback"]
    for k in policy_keys:
        key, level = k["key"], k.get("level", "required")
        val = chargeback.get(key) or entry["tags"].get(key, "")
        allowed = k.get("allowed_values") or []
        ok = bool(val) and (not allowed or val in allowed)
        if not ok:
            (missing_required if level == "required" else missing_recommended).append(key)
    if missing_required:
        status = "non_compliant"
    elif missing_recommended:
        status = "partial"
    else:
        status = "compliant"
    return {"status": status, "missing_required": missing_required, "missing_recommended": missing_recommended}


@router.get("/resources")
def list_resources(
    days: int = Query(30, ge=1, le=365),
    status_filter: Optional[str] = Query(None, alias="status", description="compliant|partial|non_compliant"),
    provider: Optional[str] = Query(None),
    q: Optional[str] = Query(None, description="search resource id/name"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=10, le=500),
    current: TokenPayload = Depends(require_permission("tags:read")),
    db: Session = Depends(get_db),
):
    start, end = _default_window(days)
    policy = _get_or_create_policy(db, current.tenant_id)
    inventory = _build_inventory(db, current.tenant_id, start, end)

    items = []
    for entry in inventory:
        comp = _compliance_status(entry, policy.required_keys)
        if provider and entry["provider"] != provider:
            continue
        if q and q.lower() not in entry["resource_id"].lower() and q.lower() not in entry["resource_name"].lower():
            continue
        if status_filter and comp["status"] != status_filter:
            continue
        items.append({
            "resource_id": entry["resource_id"],
            "resource_name": entry["resource_name"],
            "provider": entry["provider"],
            "service": entry["service"],
            "region": entry["region"],
            "total_cost": round(entry["total_cost"], 2),
            "tags": entry["tags"],
            "chargeback": entry["chargeback"],
            **comp,
        })

    items.sort(key=lambda i: i["total_cost"], reverse=True)
    total = len(items)
    start_idx = (page - 1) * page_size
    page_items = items[start_idx:start_idx + page_size]

    return {
        "count": total,
        "page": page, "page_size": page_size,
        "window": {"start": start, "end": end},
        "resources": page_items,
    }


@router.get("/compliance/summary")
def compliance_summary(
    days: int = Query(30, ge=1, le=365),
    current: TokenPayload = Depends(require_permission("tags:read")),
    db: Session = Depends(get_db),
):
    start, end = _default_window(days)
    policy = _get_or_create_policy(db, current.tenant_id)
    inventory = _build_inventory(db, current.tenant_id, start, end)

    counts = Counter()
    cost_at_risk = 0.0
    missing_key_counts: Counter = Counter()
    missing_key_cost: defaultdict = defaultdict(float)

    for entry in inventory:
        comp = _compliance_status(entry, policy.required_keys)
        counts[comp["status"]] += 1
        if comp["status"] == "non_compliant":
            cost_at_risk += entry["total_cost"]
        for key in comp["missing_required"] + comp["missing_recommended"]:
            missing_key_counts[key] += 1
            missing_key_cost[key] += entry["total_cost"]

    total_resources = len(inventory)
    total_cost = sum(e["total_cost"] for e in inventory)

    return {
        "window": {"start": start, "end": end},
        "total_resources": total_resources,
        "compliant": counts.get("compliant", 0),
        "partial": counts.get("partial", 0),
        "non_compliant": counts.get("non_compliant", 0),
        "compliance_pct": round(100.0 * counts.get("compliant", 0) / total_resources, 1) if total_resources else 0.0,
        "total_cost": round(total_cost, 2),
        "cost_at_risk": round(cost_at_risk, 2),
        "by_missing_key": [
            {"key": k, "resource_count": missing_key_counts[k], "cost": round(missing_key_cost[k], 2)}
            for k in sorted(missing_key_counts, key=lambda k: -missing_key_cost[k])
        ],
    }


# ── Key normalization ─────────────────────────────────────────────────────────

@router.get("/normalize/keys")
def suggest_key_normalization(
    days: int = Query(90, ge=1, le=365),
    current: TokenPayload = Depends(require_permission("tags:read")),
    db: Session = Depends(get_db),
):
    """Cluster distinct raw tag keys seen in cost data by normalized form.
    Any cluster with >1 distinct raw spelling is a normalization candidate."""
    start, end = _default_window(days)
    rows = _fetch_resource_rows(db, current.tenant_id, start, end)
    existing_aliases = {
        a.alias_key: a.canonical_key
        for a in db.query(TagKeyAlias).filter(TagKeyAlias.tenant_id == current.tenant_id).all()
    }

    raw_key_counts: Counter = Counter()
    for r in rows:
        for k in (r.tags or {}):
            raw_key_counts[k] += 1

    clusters: defaultdict = defaultdict(list)
    for raw_key, count in raw_key_counts.items():
        if raw_key in existing_aliases:
            continue
        clusters[_norm_form(raw_key)].append((raw_key, count))

    suggestions = []
    for norm, variants in clusters.items():
        if len(variants) < 2:
            continue
        variants.sort(key=lambda v: -v[1])
        canonical = variants[0][0]
        suggestions.append({
            "canonical_key_suggestion": canonical,
            "variants": [{"key": v[0], "occurrences": v[1]} for v in variants],
        })
    suggestions.sort(key=lambda s: -sum(v["occurrences"] for v in s["variants"]))
    return {"count": len(suggestions), "suggestions": suggestions}


def _bulk_rewrite_key(db: Session, tenant_id: str, alias_key: str, canonical_key: str) -> int:
    """Rewrite `tags` JSON blobs in FocusCost, renaming alias_key -> canonical_key
    wherever the alias is present and canonical is absent."""
    rows = db.query(FocusCost).filter(FocusCost.tenant_id == tenant_id).all()
    changed = 0
    for r in rows:
        tags = dict(r.tags or {})
        if alias_key in tags and canonical_key not in tags:
            tags[canonical_key] = tags.pop(alias_key)
            r.tags = tags
            changed += 1
        elif alias_key in tags:
            tags.pop(alias_key, None)
            r.tags = tags
            changed += 1
    db.commit()
    return changed


@router.post("/normalize/keys/apply")
def apply_key_normalization(
    req: KeyAliasApplyRequest,
    current: TokenPayload = Depends(require_permission("tags:write")),
    db: Session = Depends(get_db),
):
    if not req.aliases:
        raise HTTPException(400, "aliases must be non-empty")
    total_changed = 0
    for alias in req.aliases:
        if alias == req.canonical_key:
            continue
        existing = db.query(TagKeyAlias).filter(
            TagKeyAlias.tenant_id == current.tenant_id, TagKeyAlias.alias_key == alias
        ).one_or_none()
        if existing:
            existing.canonical_key = req.canonical_key
        else:
            db.add(TagKeyAlias(id=new_id(), tenant_id=current.tenant_id,
                                canonical_key=req.canonical_key, alias_key=alias))
        db.commit()
        if req.bulk_apply:
            total_changed += _bulk_rewrite_key(db, current.tenant_id, alias, req.canonical_key)

    record_audit(db, current, action="tags.normalize_keys", resource_type="tag_key_alias",
                 resource_id=req.canonical_key,
                 detail={"aliases": req.aliases, "rows_changed": total_changed})
    return {"status": "applied", "canonical_key": req.canonical_key,
            "aliases": req.aliases, "rows_changed": total_changed}


# ── Value normalization ───────────────────────────────────────────────────────

_VALUE_SYNONYMS = {
    "production": {"prod", "production", "prd"},
    "staging": {"stage", "staging", "stg"},
    "development": {"dev", "development", "develop"},
    "testing": {"test", "testing", "qa"},
}


@router.get("/normalize/values")
def suggest_value_normalization(
    key: str = Query(..., description="canonical tag key, e.g. 'Environment'"),
    days: int = Query(90, ge=1, le=365),
    current: TokenPayload = Depends(require_permission("tags:read")),
    db: Session = Depends(get_db),
):
    start, end = _default_window(days)
    rows = _fetch_resource_rows(db, current.tenant_id, start, end)
    existing_aliases = {
        a.alias_value
        for a in db.query(TagValueAlias).filter(
            TagValueAlias.tenant_id == current.tenant_id, TagValueAlias.tag_key == key
        ).all()
    }

    x_col = _X_COL_FOR_KEY.get(key)
    value_counts: Counter = Counter()
    for r in rows:
        v = getattr(r, x_col, "") if x_col else ""
        v = v or (r.tags or {}).get(key, "")
        if v:
            value_counts[v] += 1

    clusters: defaultdict = defaultdict(list)
    for raw_value, count in value_counts.items():
        if raw_value in existing_aliases:
            continue
        # Prefer known synonym group; fall back to normalized-form clustering.
        canon = next((c for c, syns in _VALUE_SYNONYMS.items() if _norm_form(raw_value) in syns), None)
        clusters[canon or _norm_form(raw_value)].append((raw_value, count))

    suggestions = []
    for norm, variants in clusters.items():
        if len(variants) < 2:
            continue
        variants.sort(key=lambda v: -v[1])
        canonical = norm if norm in _VALUE_SYNONYMS else variants[0][0]
        suggestions.append({
            "canonical_value_suggestion": canonical,
            "variants": [{"value": v[0], "occurrences": v[1]} for v in variants],
        })
    suggestions.sort(key=lambda s: -sum(v["occurrences"] for v in s["variants"]))
    return {"count": len(suggestions), "tag_key": key, "suggestions": suggestions}


def _bulk_rewrite_value(db: Session, tenant_id: str, tag_key: str, alias_value: str, canonical_value: str) -> int:
    x_col = _X_COL_FOR_KEY.get(tag_key)
    rows = db.query(FocusCost).filter(FocusCost.tenant_id == tenant_id).all()
    changed = 0
    for r in rows:
        tags = dict(r.tags or {})
        row_changed = False
        if tags.get(tag_key) == alias_value:
            tags[tag_key] = canonical_value
            r.tags = tags
            row_changed = True
        if x_col and getattr(r, x_col, "") == alias_value:
            setattr(r, x_col, canonical_value)
            row_changed = True
        if row_changed:
            changed += 1
    db.commit()
    return changed


@router.post("/normalize/values/apply")
def apply_value_normalization(
    req: ValueAliasApplyRequest,
    current: TokenPayload = Depends(require_permission("tags:write")),
    db: Session = Depends(get_db),
):
    if not req.aliases:
        raise HTTPException(400, "aliases must be non-empty")
    total_changed = 0
    for alias in req.aliases:
        if alias == req.canonical_value:
            continue
        existing = db.query(TagValueAlias).filter(
            TagValueAlias.tenant_id == current.tenant_id,
            TagValueAlias.tag_key == req.tag_key,
            TagValueAlias.alias_value == alias,
        ).one_or_none()
        if existing:
            existing.canonical_value = req.canonical_value
        else:
            db.add(TagValueAlias(id=new_id(), tenant_id=current.tenant_id, tag_key=req.tag_key,
                                  canonical_value=req.canonical_value, alias_value=alias))
        db.commit()
        if req.bulk_apply:
            total_changed += _bulk_rewrite_value(db, current.tenant_id, req.tag_key, alias, req.canonical_value)

    record_audit(db, current, action="tags.normalize_values", resource_type="tag_value_alias",
                 resource_id=f"{req.tag_key}:{req.canonical_value}",
                 detail={"tag_key": req.tag_key, "aliases": req.aliases, "rows_changed": total_changed})
    return {"status": "applied", "tag_key": req.tag_key, "canonical_value": req.canonical_value,
            "aliases": req.aliases, "rows_changed": total_changed}


# ── Prediction ────────────────────────────────────────────────────────────────

def _predict_for_key(entries: list[dict], tag_key: str) -> list[dict]:
    """
    Heuristics, tried in order, first match wins:
      1. sibling_majority — most common value for this key among resources
         sharing the same service + provider + region (a "resource family").
      2. account_default   — most common value for this key across the whole
         sub_account, if a family-level signal isn't available.
    Each prediction carries a confidence score = share of the winning group
    that has that value.
    """
    missing = [e for e in entries if not (e["chargeback"].get(tag_key) or e["tags"].get(tag_key))]
    if not missing:
        return []

    def _value_of(e):
        return e["chargeback"].get(tag_key) or e["tags"].get(tag_key) or ""

    by_family: defaultdict = defaultdict(Counter)
    by_account: defaultdict = defaultdict(Counter)
    for e in entries:
        v = _value_of(e)
        if not v:
            continue
        family = (e["provider"], e["service"], e["region"])
        by_family[family][v] += 1
        by_account[e["sub_account_id"]][v] += 1

    predictions = []
    for e in missing:
        family = (e["provider"], e["service"], e["region"])
        fam_counter = by_family.get(family)
        if fam_counter:
            total = sum(fam_counter.values())
            value, count = fam_counter.most_common(1)[0]
            predictions.append({
                "resource_id": e["resource_id"], "resource_name": e["resource_name"],
                "provider": e["provider"], "service": e["service"],
                "tag_key": tag_key, "predicted_value": value,
                "confidence": round(count / total, 2),
                "method": "sibling_majority",
                "evidence": {"family": list(family), "sample_size": total, "matching": count},
            })
            continue
        acct_counter = by_account.get(e["sub_account_id"])
        if acct_counter:
            total = sum(acct_counter.values())
            value, count = acct_counter.most_common(1)[0]
            predictions.append({
                "resource_id": e["resource_id"], "resource_name": e["resource_name"],
                "provider": e["provider"], "service": e["service"],
                "tag_key": tag_key, "predicted_value": value,
                "confidence": round(0.5 * count / total, 2),  # discounted — weaker signal
                "method": "account_default",
                "evidence": {"sub_account_id": e["sub_account_id"], "sample_size": total, "matching": count},
            })
    return predictions


@router.post("/predictions/generate")
def generate_predictions(
    req: PredictionGenerateRequest,
    current: TokenPayload = Depends(require_permission("tags:write")),
    db: Session = Depends(get_db),
):
    start, end = _default_window(req.days)
    policy = _get_or_create_policy(db, current.tenant_id)
    keys = req.tag_keys or [k["key"] for k in policy.required_keys]
    inventory = _build_inventory(db, current.tenant_id, start, end)

    created, skipped = 0, 0
    for key in keys:
        for pred in _predict_for_key(inventory, key):
            existing = db.query(TagPrediction).filter(
                TagPrediction.tenant_id == current.tenant_id,
                TagPrediction.resource_id == pred["resource_id"],
                TagPrediction.tag_key == key,
            ).one_or_none()
            if existing:
                if existing.status == "pending":
                    existing.predicted_value = pred["predicted_value"]
                    existing.confidence = pred["confidence"]
                    existing.method = pred["method"]
                    existing.evidence = pred["evidence"]
                    db.commit()
                else:
                    skipped += 1
                continue
            db.add(TagPrediction(
                id=new_id(), tenant_id=current.tenant_id,
                resource_id=pred["resource_id"], resource_name=pred["resource_name"],
                provider=pred["provider"], service=pred["service"],
                tag_key=key, predicted_value=pred["predicted_value"],
                confidence=pred["confidence"], method=pred["method"], evidence=pred["evidence"],
            ))
            db.commit()
            created += 1

    record_audit(db, current, action="tags.predictions_generate", resource_type="tag_prediction",
                 detail={"tag_keys": keys, "created": created, "skipped": skipped})
    return {"status": "ok", "tag_keys": keys, "created": created, "skipped_existing": skipped}


@router.get("/predictions")
def list_predictions(
    status_filter: Optional[str] = Query(None, alias="status"),
    tag_key: Optional[str] = Query(None),
    current: TokenPayload = Depends(require_permission("tags:read")),
    db: Session = Depends(get_db),
):
    q = db.query(TagPrediction).filter(TagPrediction.tenant_id == current.tenant_id)
    if status_filter:
        q = q.filter(TagPrediction.status == status_filter)
    if tag_key:
        q = q.filter(TagPrediction.tag_key == tag_key)
    rows = q.order_by(TagPrediction.confidence.desc()).all()
    return {
        "count": len(rows),
        "predictions": [
            {
                "id": p.id, "resource_id": p.resource_id, "resource_name": p.resource_name,
                "provider": p.provider, "service": p.service, "tag_key": p.tag_key,
                "predicted_value": p.predicted_value, "confidence": p.confidence,
                "method": p.method, "evidence": p.evidence, "status": p.status,
                "created_at": p.created_at.isoformat(),
            }
            for p in rows
        ],
    }


@router.post("/predictions/{prediction_id}/approve")
def approve_prediction(
    prediction_id: str,
    current: TokenPayload = Depends(require_permission("tags:write")),
    db: Session = Depends(get_db),
):
    p = db.query(TagPrediction).filter(
        TagPrediction.id == prediction_id, TagPrediction.tenant_id == current.tenant_id
    ).one_or_none()
    if not p:
        raise HTTPException(404, "Prediction not found")
    if p.status != "pending":
        raise HTTPException(409, f"Prediction already {p.status}")

    existing_override = db.query(ResourceTagOverride).filter(
        ResourceTagOverride.tenant_id == current.tenant_id,
        ResourceTagOverride.resource_id == p.resource_id,
        ResourceTagOverride.tag_key == p.tag_key,
    ).one_or_none()
    if existing_override:
        existing_override.tag_value = p.predicted_value
        existing_override.source = "predicted"
        existing_override.applied_at = utcnow()
    else:
        db.add(ResourceTagOverride(
            id=new_id(), tenant_id=current.tenant_id, resource_id=p.resource_id,
            tag_key=p.tag_key, tag_value=p.predicted_value, source="predicted",
        ))
    p.status = "applied"
    p.resolved_at = utcnow()
    db.commit()

    record_audit(db, current, action="tags.prediction_approve", resource_type="tag_prediction",
                 resource_id=p.id, detail={"resource_id": p.resource_id, "tag_key": p.tag_key,
                                            "value": p.predicted_value})
    return {"status": "applied", "resource_id": p.resource_id, "tag_key": p.tag_key, "value": p.predicted_value}


@router.post("/predictions/{prediction_id}/reject")
def reject_prediction(
    prediction_id: str,
    current: TokenPayload = Depends(require_permission("tags:write")),
    db: Session = Depends(get_db),
):
    p = db.query(TagPrediction).filter(
        TagPrediction.id == prediction_id, TagPrediction.tenant_id == current.tenant_id
    ).one_or_none()
    if not p:
        raise HTTPException(404, "Prediction not found")
    if p.status != "pending":
        raise HTTPException(409, f"Prediction already {p.status}")
    p.status = "rejected"
    p.resolved_at = utcnow()
    db.commit()
    record_audit(db, current, action="tags.prediction_reject", resource_type="tag_prediction", resource_id=p.id)
    return {"status": "rejected"}
