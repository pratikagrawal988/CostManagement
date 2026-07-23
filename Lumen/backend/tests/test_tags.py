"""
Coverage for the tag management feature (routes_tags.py): policy CRUD,
resource inventory + compliance scoring, key/value normalization with bulk
apply, and missing-tag prediction with approve/reject — plus the feedback
loop where an approved override is picked up by a later FOCUS transform run
(apply_tag_overrides in jobs.py), so a prediction/normalization approved
today keeps applying to cost data ingested tomorrow.
"""
from __future__ import annotations

import asyncio
import uuid

from app.models import CostDetail, FocusCost, utcnow
from app.settings import Settings
from app.jobs import run_focus_transform


def _focus_row(tenant_id: str, **overrides) -> dict:
    row = dict(
        id=str(uuid.uuid4()), tenant_id=tenant_id, billing_period_start="2026-07-01",
        provider_name="AWS", service_name="Amazon Elastic Compute Cloud",
        region_id="us-east-1", region_name="us-east-1",
        resource_id=f"res-{uuid.uuid4().hex[:8]}", resource_name="",
        sub_account_id="acct-1", usage_quantity=1.0, usage_unit="hour",
        list_unit_price=1.0, list_cost=10.0, billed_cost=10.0, effective_cost=10.0,
        currency="USD", tags={}, x_team="", x_cost_center="", x_environment="", x_app_id="",
        transformed_at=utcnow(),
    )
    row.update(overrides)
    row["resource_name"] = row["resource_name"] or row["resource_id"]
    return row


# ── Policy ────────────────────────────────────────────────────────────────────

def test_get_policy_auto_creates_default(client, auth):
    r = client.get("/api/tags/policy", headers=auth("analyst"))
    assert r.status_code == 200
    keys = {k["key"] for k in r.json()["required_keys"]}
    assert {"Team", "CostCenter"}.issubset(keys)


def test_put_policy_replaces_required_keys(client, auth):
    payload = {"required_keys": [
        {"key": "Owner", "level": "required", "description": "Owning engineer", "allowed_values": []},
    ]}
    r = client.put("/api/tags/policy", json=payload, headers=auth("admin"))
    assert r.status_code == 200, r.text

    r = client.get("/api/tags/policy", headers=auth("admin"))
    keys = [k["key"] for k in r.json()["required_keys"]]
    assert keys == ["Owner"]


def test_put_policy_rejects_invalid_level(client, auth):
    payload = {"required_keys": [{"key": "X", "level": "mandatory", "description": "", "allowed_values": []}]}
    r = client.put("/api/tags/policy", json=payload, headers=auth("admin"))
    assert r.status_code == 400


# ── Resource inventory + compliance ───────────────────────────────────────────

def test_resource_inventory_flags_missing_required_tags(client, auth, db, tenant_id):
    # Pin the policy to exactly Team + CostCenter (required, no allowed_values
    # constraint) so this test doesn't depend on the default policy's shape.
    client.put("/api/tags/policy", headers=auth("admin"), json={"required_keys": [
        {"key": "Team", "level": "required", "description": "", "allowed_values": []},
        {"key": "CostCenter", "level": "required", "description": "", "allowed_values": []},
    ]})

    db.add(FocusCost(**_focus_row(tenant_id, resource_id="tagged-1",
                                   tags={"Team": "platform", "CostCenter": "CC-100"},
                                   x_team="platform", x_cost_center="CC-100")))
    db.add(FocusCost(**_focus_row(tenant_id, resource_id="untagged-1")))
    db.commit()

    r = client.get("/api/tags/resources?days=365", headers=auth("analyst"))
    assert r.status_code == 200
    by_id = {x["resource_id"]: x for x in r.json()["resources"]}
    assert by_id["tagged-1"]["status"] == "compliant"
    assert by_id["untagged-1"]["status"] == "non_compliant"
    assert set(by_id["untagged-1"]["missing_required"]) == {"Team", "CostCenter"}


def test_compliance_summary_computes_cost_at_risk(client, auth, db, tenant_id):
    db.add(FocusCost(**_focus_row(tenant_id, resource_id="tagged-2", billed_cost=10.0, effective_cost=10.0,
                                   tags={"Team": "platform", "CostCenter": "CC-100"},
                                   x_team="platform", x_cost_center="CC-100")))
    db.add(FocusCost(**_focus_row(tenant_id, resource_id="untagged-2", billed_cost=25.0, effective_cost=25.0)))
    db.commit()

    r = client.get("/api/tags/compliance/summary?days=365", headers=auth("analyst"))
    assert r.status_code == 200
    body = r.json()
    assert body["total_resources"] == 2
    assert body["non_compliant"] == 1
    assert body["cost_at_risk"] == 25.0


def test_resources_endpoint_requires_read_permission(client, auth):
    r = client.get("/api/tags/resources", headers=auth("viewer"))
    assert r.status_code == 403


# ── Key normalization ──────────────────────────────────────────────────────────

def test_key_normalization_suggests_and_merges_variants(client, auth, db, tenant_id):
    db.add(FocusCost(**_focus_row(tenant_id, resource_id="r1", tags={"team": "data-eng"})))
    db.add(FocusCost(**_focus_row(tenant_id, resource_id="r2", tags={"team": "data-eng"})))
    db.add(FocusCost(**_focus_row(tenant_id, resource_id="r3", tags={"Team": "platform"})))
    db.commit()

    suggest = client.get("/api/tags/normalize/keys?days=365", headers=auth("analyst"))
    assert suggest.status_code == 200
    suggestions = suggest.json()["suggestions"]
    assert len(suggestions) == 1
    variant_keys = {v["key"] for v in suggestions[0]["variants"]}
    assert variant_keys == {"team", "Team"}

    apply = client.post("/api/tags/normalize/keys/apply", headers=auth("admin"), json={
        "canonical_key": "Team", "aliases": ["team"], "bulk_apply": True,
    })
    assert apply.status_code == 200, apply.text
    assert apply.json()["rows_changed"] == 2

    # Rows that had "team" now have "Team" instead, nothing left unmerged
    again = client.get("/api/tags/normalize/keys?days=365", headers=auth("analyst"))
    assert again.json()["count"] == 0


def test_key_normalization_requires_write_permission(client, auth):
    r = client.post("/api/tags/normalize/keys/apply", headers=auth("analyst"),
                     json={"canonical_key": "Team", "aliases": ["team"]})
    assert r.status_code == 403


# ── Value normalization ────────────────────────────────────────────────────────

def test_value_normalization_suggests_and_merges_synonyms(client, auth, db, tenant_id):
    db.add(FocusCost(**_focus_row(tenant_id, resource_id="v1", tags={"Environment": "prod"}, x_environment="prod")))
    db.add(FocusCost(**_focus_row(tenant_id, resource_id="v2", tags={"Environment": "PROD"}, x_environment="PROD")))
    db.add(FocusCost(**_focus_row(tenant_id, resource_id="v3", tags={"Environment": "production"}, x_environment="production")))
    db.commit()

    suggest = client.get("/api/tags/normalize/values?key=Environment&days=365", headers=auth("analyst"))
    assert suggest.status_code == 200
    suggestions = suggest.json()["suggestions"]
    assert len(suggestions) == 1
    assert suggestions[0]["canonical_value_suggestion"] == "production"

    apply = client.post("/api/tags/normalize/values/apply", headers=auth("admin"), json={
        "tag_key": "Environment", "canonical_value": "production", "aliases": ["prod", "PROD"], "bulk_apply": True,
    })
    assert apply.status_code == 200, apply.text
    assert apply.json()["rows_changed"] == 2

    after = client.get("/api/tags/resources?days=365", headers=auth("analyst"))
    envs = {r["chargeback"]["Environment"] for r in after.json()["resources"] if r["resource_id"] in ("v1", "v2", "v3")}
    assert envs == {"production"}


# ── Prediction ─────────────────────────────────────────────────────────────────

def test_prediction_generate_uses_sibling_majority(client, auth, db, tenant_id):
    # Three EC2/us-east-1 siblings tagged Team=platform, one untagged sibling.
    for i in range(3):
        db.add(FocusCost(**_focus_row(tenant_id, resource_id=f"sib-{i}",
                                       tags={"Team": "platform"}, x_team="platform")))
    db.add(FocusCost(**_focus_row(tenant_id, resource_id="sib-missing")))
    db.commit()

    gen = client.post("/api/tags/predictions/generate", headers=auth("admin"),
                       json={"tag_keys": ["Team"], "days": 365})
    assert gen.status_code == 200, gen.text
    assert gen.json()["created"] == 1

    preds = client.get("/api/tags/predictions?status=pending", headers=auth("analyst"))
    assert preds.status_code == 200
    rows = preds.json()["predictions"]
    assert len(rows) == 1
    p = rows[0]
    assert p["resource_id"] == "sib-missing"
    assert p["predicted_value"] == "platform"
    assert p["method"] == "sibling_majority"
    assert p["confidence"] == 1.0


def test_prediction_approve_writes_override_and_reflects_in_inventory(client, auth, db, tenant_id):
    for i in range(3):
        db.add(FocusCost(**_focus_row(tenant_id, resource_id=f"sib2-{i}",
                                       tags={"Team": "platform"}, x_team="platform")))
    db.add(FocusCost(**_focus_row(tenant_id, resource_id="sib2-missing")))
    db.commit()

    client.post("/api/tags/predictions/generate", headers=auth("admin"), json={"tag_keys": ["Team"], "days": 365})
    preds = client.get("/api/tags/predictions?status=pending", headers=auth("analyst")).json()["predictions"]
    pred = next(p for p in preds if p["resource_id"] == "sib2-missing")

    approve = client.post(f"/api/tags/predictions/{pred['id']}/approve", headers=auth("admin"))
    assert approve.status_code == 200, approve.text

    inventory = client.get("/api/tags/resources?days=365", headers=auth("analyst")).json()["resources"]
    row = next(r for r in inventory if r["resource_id"] == "sib2-missing")
    assert row["chargeback"]["Team"] == "platform"

    # Re-approving (already applied) must be rejected, not silently repeated
    reapprove = client.post(f"/api/tags/predictions/{pred['id']}/approve", headers=auth("admin"))
    assert reapprove.status_code == 409


def test_prediction_reject_leaves_resource_non_compliant(client, auth, db, tenant_id):
    for i in range(3):
        db.add(FocusCost(**_focus_row(tenant_id, resource_id=f"sib3-{i}",
                                       tags={"Team": "platform"}, x_team="platform")))
    db.add(FocusCost(**_focus_row(tenant_id, resource_id="sib3-missing")))
    db.commit()

    client.post("/api/tags/predictions/generate", headers=auth("admin"), json={"tag_keys": ["Team"], "days": 365})
    preds = client.get("/api/tags/predictions?status=pending", headers=auth("analyst")).json()["predictions"]
    pred = next(p for p in preds if p["resource_id"] == "sib3-missing")

    reject = client.post(f"/api/tags/predictions/{pred['id']}/reject", headers=auth("admin"))
    assert reject.status_code == 200

    inventory = client.get("/api/tags/resources?days=365", headers=auth("analyst")).json()["resources"]
    row = next(r for r in inventory if r["resource_id"] == "sib3-missing")
    assert row["chargeback"]["Team"] == ""
    assert row["status"] == "non_compliant"


def test_predictions_generate_requires_write_permission(client, auth):
    r = client.post("/api/tags/predictions/generate", headers=auth("analyst"), json={"tag_keys": ["Team"]})
    assert r.status_code == 403


# ── Override feedback into future ingestion ──────────────────────────────────

def test_approved_override_applies_to_future_cost_detail_ingestion(client, auth, db, tenant_id):
    """An override approved today (from a prediction or normalization) must be
    picked up automatically the next time raw cost data for that same
    resource_id is ingested and transformed — not just in the read-time view."""
    resource_id = f"persist-{uuid.uuid4().hex[:8]}"
    for i in range(3):
        db.add(FocusCost(**_focus_row(tenant_id, resource_id=f"sib4-{i}",
                                       tags={"Team": "platform"}, x_team="platform")))
    db.add(FocusCost(**_focus_row(tenant_id, resource_id=resource_id)))
    db.commit()

    client.post("/api/tags/predictions/generate", headers=auth("admin"), json={"tag_keys": ["Team"], "days": 365})
    preds = client.get("/api/tags/predictions?status=pending", headers=auth("analyst")).json()["predictions"]
    pred = next(p for p in preds if p["resource_id"] == resource_id)
    client.post(f"/api/tags/predictions/{pred['id']}/approve", headers=auth("admin"))

    # New raw CostDetail row for the SAME resource_id, with no Team tag at all —
    # simulates the next day's ingestion before the override existed.
    db.add(CostDetail(
        id=str(uuid.uuid4()), tenant_id=tenant_id, sourced_from="cur", account_id="111122223333",
        service="Amazon Elastic Compute Cloud", sku="XYZ", region="us-east-1", resource_id=resource_id,
        usage_start_date="2026-07-02", usage_end_date="2026-07-03", usage_quantity=24.0, usage_unit="Hrs",
        unblended_cost=5.0, blended_cost=5.0, amortised_cost=5.0, list_cost=5.0, currency="USD",
        tags={}, raw={}, parsed_at=utcnow(),
    ))
    db.commit()

    asyncio.run(run_focus_transform(Settings()))

    new_focus = db.query(FocusCost).filter(
        FocusCost.tenant_id == tenant_id, FocusCost.resource_id == resource_id,
        FocusCost.billing_period_start == "2026-07-02",
    ).one_or_none()
    assert new_focus is not None
    assert new_focus.x_team == "platform"  # override applied automatically, no manual re-tagging needed
