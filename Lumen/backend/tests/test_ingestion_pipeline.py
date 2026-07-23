"""
End-to-end coverage for the real (non-demo-seeded) cost ingestion pipeline:
CostDetail (raw, per-provider) -> FOCUS transform -> FocusCost -> CostAggregation
-> dashboard/export API endpoints.

This is the pipeline that was found broken (schema drift against the current
ORM models) earlier this project and fixed across jobs.py/azure_jobs.py/
gcp_jobs.py/routes_cost.py. These tests pin that behavior down so a future
model change that silently breaks field mappings fails CI instead of only
being caught by manually seeded demo data (which uses a separate, always-
correct seeding path and would have masked the bug).
"""
from __future__ import annotations

import asyncio
import uuid

import pytest

from app.models import CostDetail, FocusCost, CostAggregation, utcnow
from app.settings import Settings
from app.jobs import run_focus_transform


def _cur_row(tenant_id: str, **overrides) -> dict:
    row = dict(
        id=str(uuid.uuid4()), tenant_id=tenant_id, sourced_from="cur", account_id="111122223333",
        service="Amazon Elastic Compute Cloud", sku="ABC123", region="us-east-1", resource_id=f"i-{uuid.uuid4().hex[:8]}",
        usage_start_date="2026-07-01", usage_end_date="2026-07-02", usage_quantity=24.0, usage_unit="Hrs",
        unblended_cost=12.5, blended_cost=12.5, amortised_cost=12.5, list_cost=13.0, currency="USD",
        tags={"Team": "platform", "CostCenter": "CC-100", "Environment": "prod"}, raw={"payer_account_id": "999988887777"},
        parsed_at=utcnow(),
    )
    row.update(overrides)
    return row


def _azure_row(tenant_id: str, **overrides) -> dict:
    row = dict(
        id=str(uuid.uuid4()), tenant_id=tenant_id, sourced_from="azure", account_id="sub-abc",
        service="Virtual Machines", sku="Dv3", region="eastus", resource_id=f"/rg/vm-{uuid.uuid4().hex[:8]}",
        usage_start_date="2026-07-01", usage_end_date="2026-07-01", usage_quantity=10.0, usage_unit="",
        unblended_cost=8.0, blended_cost=8.0, amortised_cost=8.0, list_cost=8.0, currency="USD",
        tags={"team": "data-eng", "cost-center": "CC-200"}, raw={}, parsed_at=utcnow(),
    )
    row.update(overrides)
    return row


def _gcp_row(tenant_id: str, **overrides) -> dict:
    row = dict(
        id=str(uuid.uuid4()), tenant_id=tenant_id, sourced_from="gcp", account_id="my-project",
        service="Compute Engine", sku="n1-standard", region="us-central1", resource_id=f"inst-{uuid.uuid4().hex[:8]}",
        usage_start_date="2026-07-01", usage_end_date="2026-07-01", usage_quantity=5.0, usage_unit="",
        unblended_cost=4.0, blended_cost=4.0, amortised_cost=4.0, list_cost=4.0, currency="USD",
        tags={}, raw={}, parsed_at=utcnow(),
    )
    row.update(overrides)
    return row


def test_aws_cur_row_transforms_to_focus_and_aggregation(db, tenant_id):
    db.add(CostDetail(**_cur_row(tenant_id)))
    db.commit()

    result = asyncio.run(run_focus_transform(Settings()))
    assert result["errors"] is None

    focus_rows = db.query(FocusCost).filter(FocusCost.tenant_id == tenant_id).all()
    assert len(focus_rows) == 1
    f = focus_rows[0]
    assert f.provider_name == "AWS"
    assert f.billed_cost == 12.5
    assert f.effective_cost == 12.5
    # Chargeback tags resolved via tags_lookup, case-insensitive
    assert f.x_team == "platform"
    assert f.x_cost_center == "CC-100"
    assert f.x_environment == "prod"

    agg_rows = db.query(CostAggregation).filter(CostAggregation.tenant_id == tenant_id).all()
    assert len(agg_rows) >= 1
    assert any(a.provider == "AWS" and a.total_cost == pytest.approx(12.5) for a in agg_rows)


def test_azure_row_transforms_with_mixed_case_tags(db, tenant_id):
    db.add(CostDetail(**_azure_row(tenant_id)))
    db.commit()

    result = asyncio.run(run_focus_transform(Settings()))
    assert result["errors"] is None or all("azure" not in e.lower() for e in result["errors"])

    focus_rows = db.query(FocusCost).filter(FocusCost.tenant_id == tenant_id, FocusCost.provider_name == "Azure").all()
    assert len(focus_rows) == 1
    f = focus_rows[0]
    assert f.billed_cost == 8.0
    # lower-case "team"/"cost-center" keys must still resolve via tags_lookup
    assert f.x_team == "data-eng"
    assert f.x_cost_center == "CC-200"


def test_gcp_row_transforms_with_no_tags(db, tenant_id):
    db.add(CostDetail(**_gcp_row(tenant_id)))
    db.commit()

    result = asyncio.run(run_focus_transform(Settings()))

    focus_rows = db.query(FocusCost).filter(FocusCost.tenant_id == tenant_id, FocusCost.provider_name == "GCP").all()
    assert len(focus_rows) == 1
    f = focus_rows[0]
    assert f.billed_cost == 4.0
    assert f.x_team == ""  # no tags supplied — must not crash, must default cleanly


def test_all_three_providers_together_produce_isolated_aggregations(db, tenant_id):
    db.add(CostDetail(**_cur_row(tenant_id)))
    db.add(CostDetail(**_azure_row(tenant_id)))
    db.add(CostDetail(**_gcp_row(tenant_id)))
    db.commit()

    asyncio.run(run_focus_transform(Settings()))

    providers = {f.provider_name for f in db.query(FocusCost).filter(FocusCost.tenant_id == tenant_id).all()}
    assert providers == {"AWS", "Azure", "GCP"}

    total_cost = sum(a.total_cost for a in db.query(CostAggregation).filter(CostAggregation.tenant_id == tenant_id).all())
    assert total_cost == pytest.approx(12.5 + 8.0 + 4.0)


def test_dashboard_endpoints_reflect_ingested_data(client, auth, db, tenant_id):
    db.add(CostDetail(**_cur_row(tenant_id)))
    db.commit()
    asyncio.run(run_focus_transform(Settings()))

    headers = auth("analyst")

    daily = client.get("/api/cost/daily", headers=headers)
    assert daily.status_code == 200, daily.text
    assert daily.json()["count"] >= 1
    assert any(row["total_cost"] == pytest.approx(12.5) for row in daily.json()["data"])

    summary = client.get("/api/cost/summary", headers=headers)
    assert summary.status_code == 200
    assert summary.json()["total_cost"] == pytest.approx(12.5)

    export = client.post("/api/cost/focus/export", headers=headers)
    assert export.status_code == 200, export.text
    body = export.json()
    assert body["record_count"] >= 1
    assert "platform" in body["csv_content"]   # x_team survives into the CSV
    assert "CC-100" in body["csv_content"]     # x_cost_center survives into the CSV


def test_focus_transform_is_idempotent_on_rerun(db, tenant_id):
    """Running the transform twice over the same CostDetail rows must upsert,
    not duplicate, FocusCost rows."""
    db.add(CostDetail(**_cur_row(tenant_id)))
    db.commit()

    asyncio.run(run_focus_transform(Settings()))
    first_count = db.query(FocusCost).filter(FocusCost.tenant_id == tenant_id).count()

    asyncio.run(run_focus_transform(Settings()))
    second_count = db.query(FocusCost).filter(FocusCost.tenant_id == tenant_id).count()

    assert first_count == 1
    assert second_count == 1
