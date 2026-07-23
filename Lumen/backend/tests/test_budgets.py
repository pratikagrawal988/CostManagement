"""
Coverage for routes_budgets.py: budget CRUD, actuals/utilization/forecast
computed live from FocusCost, alert status thresholds, and history — plus the
RBAC nuance that budgets:read and budgets:write have different role sets
(team_lead can read but not write; finance_manager can write, finops_engineer
cannot).
"""
from __future__ import annotations

import uuid

from app.models import FocusCost, utcnow


def _focus_row(tenant_id: str, **overrides) -> dict:
    row = dict(
        id=str(uuid.uuid4()), tenant_id=tenant_id, billing_period_start="2026-07-15",
        provider_name="AWS", service_name="Amazon Elastic Compute Cloud",
        service_category="Compute", region_id="us-east-1", region_name="us-east-1",
        resource_id=f"res-{uuid.uuid4().hex[:8]}", sub_account_id="acct-1",
        usage_quantity=1.0, usage_unit="hour", list_unit_price=1.0,
        list_cost=0.0, billed_cost=0.0, effective_cost=0.0,
        currency="USD", tags={}, transformed_at=utcnow(),
    )
    row.update(overrides)
    return row


def test_create_budget_and_actual_computed_from_focus_cost(client, auth, db, tenant_id):
    db.add(FocusCost(**_focus_row(tenant_id, effective_cost=500.0)))
    db.commit()

    create = client.post("/api/budgets", headers=auth("finance_manager"), json={
        "name": "Compute budget", "amount": 1000.0, "period": "monthly", "provider_name": "AWS",
    })
    assert create.status_code == 201, create.text
    assert create.json()["actual"] == 500.0
    assert create.json()["utilization_pct"] == 50.0
    assert create.json()["status"] == "ok"

    listed = client.get("/api/budgets?anchor=2026-07-15", headers=auth("analyst"))
    assert listed.status_code == 200
    budgets = listed.json()["budgets"]
    assert len(budgets) == 1
    assert budgets[0]["actual"] == 500.0


def test_budget_scoped_to_provider_excludes_other_providers(client, auth, db, tenant_id):
    db.add(FocusCost(**_focus_row(tenant_id, provider_name="AWS", effective_cost=200.0)))
    db.add(FocusCost(**_focus_row(tenant_id, provider_name="Azure", effective_cost=999.0,
                                   resource_id=f"az-{uuid.uuid4().hex[:8]}")))
    db.commit()

    create = client.post("/api/budgets", headers=auth("admin"), json={
        "name": "AWS only", "amount": 1000.0, "period": "monthly", "provider_name": "AWS",
    })
    assert create.status_code == 201
    assert create.json()["actual"] == 200.0  # Azure spend must not leak in


def test_budget_status_thresholds(client, auth, db, tenant_id):
    db.add(FocusCost(**_focus_row(tenant_id, effective_cost=95.0)))
    db.commit()

    over = client.post("/api/budgets", headers=auth("admin"), json={
        "name": "Nearly blown", "amount": 100.0, "period": "monthly", "alert_thresholds": [80.0, 100.0],
    })
    assert over.status_code == 201
    assert over.json()["status"] == "warning"  # 95% >= 80% warn threshold, < 100%

    listed = client.get("/api/budgets?anchor=2026-07-15", headers=auth("admin"))
    assert any(a["status"] == "warning" for a in listed.json()["alerts"])


def test_patch_and_delete_budget(client, auth, db, tenant_id):
    create = client.post("/api/budgets", headers=auth("admin"),
                          json={"name": "To edit", "amount": 500.0, "period": "monthly"})
    budget_id = create.json()["id"]

    patched = client.patch(f"/api/budgets/{budget_id}", headers=auth("admin"), json={"amount": 750.0})
    assert patched.status_code == 200
    assert patched.json()["amount"] == 750.0

    deleted = client.delete(f"/api/budgets/{budget_id}", headers=auth("admin"))
    assert deleted.status_code == 200
    assert deleted.json()["status"] == "deleted"

    missing = client.patch(f"/api/budgets/{budget_id}", headers=auth("admin"), json={"amount": 1.0})
    assert missing.status_code == 404


def test_budget_history_returns_requested_months(client, auth, db, tenant_id):
    db.add(FocusCost(**_focus_row(tenant_id, effective_cost=100.0)))
    db.commit()

    create = client.post("/api/budgets", headers=auth("admin"),
                          json={"name": "History test", "amount": 300.0, "period": "monthly"})
    budget_id = create.json()["id"]

    history = client.get(f"/api/budgets/{budget_id}/history?months=3", headers=auth("analyst"))
    assert history.status_code == 200
    assert len(history.json()["months"]) == 3


def test_create_budget_rejects_invalid_period_and_amount(client, auth):
    bad_period = client.post("/api/budgets", headers=auth("admin"),
                              json={"name": "X", "amount": 100.0, "period": "weekly"})
    assert bad_period.status_code == 400

    bad_amount = client.post("/api/budgets", headers=auth("admin"),
                              json={"name": "X", "amount": -5.0, "period": "monthly"})
    assert bad_amount.status_code == 400


# ── RBAC nuance: read and write have different role sets ─────────────────────

def test_team_lead_can_read_but_not_write_budgets(client, auth):
    listed = client.get("/api/budgets", headers=auth("team_lead"))
    assert listed.status_code == 200

    created = client.post("/api/budgets", headers=auth("team_lead"),
                           json={"name": "X", "amount": 100.0, "period": "monthly"})
    assert created.status_code == 403


def test_finops_engineer_cannot_write_budgets_despite_reading_credentials(client, auth):
    """finops_engineer has credentials:write but NOT budgets:write — these are
    deliberately different permission sets and shouldn't bleed into each other."""
    created = client.post("/api/budgets", headers=auth("finops_engineer"),
                           json={"name": "X", "amount": 100.0, "period": "monthly"})
    assert created.status_code == 403
