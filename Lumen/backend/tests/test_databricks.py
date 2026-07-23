"""
Coverage for routes_databricks.py: DBU cost overview/breakdown, job cost
summary, cluster utilization/idle detection, and the CSP-infra reconciliation
endpoint that marries the Databricks platform fee (DBU cost) against the
underlying cloud compute cost it rides on.
"""
from __future__ import annotations

import uuid
from datetime import timedelta

from app.models import (
    DatabricksCluster, DatabricksClusterUtilization, DatabricksJobRun,
    DatabricksUsageRecord, FocusCost, utcnow,
)

TODAY = utcnow().date().isoformat()


def _seed_one_cluster(db, tenant_id, *, cluster_type="all_purpose", provider="AWS",
                       dbu_cost=100.0, infra_cost=200.0, avg_cpu=60.0, active=8.0, idle=1.0, idle_cost=5.0):
    cluster_id = f"cl-{uuid.uuid4().hex[:8]}"
    db.add(DatabricksCluster(
        id=str(uuid.uuid4()), tenant_id=tenant_id, cluster_id=cluster_id, cluster_name=f"test-{cluster_id}",
        workspace_id="ws-1", workspace_name="test-workspace", cloud_provider=provider.lower(),
        region="us-east-1", cluster_type=cluster_type, node_type_id="i3.xlarge", num_workers=4,
        tags={"team": "platform"}, auto_terminate=True,
    ))
    db.add(DatabricksUsageRecord(
        id=str(uuid.uuid4()), tenant_id=tenant_id, cluster_id=cluster_id, workspace_id="ws-1",
        sku_name="STANDARD_ALL_PURPOSE_COMPUTE", usage_date=TODAY,
        dbu_quantity=50.0, dbu_unit_price=dbu_cost / 50.0 if dbu_cost else 0.0, dbu_cost=dbu_cost,
    ))
    db.add(DatabricksClusterUtilization(
        id=str(uuid.uuid4()), tenant_id=tenant_id, cluster_id=cluster_id, date=TODAY,
        avg_cpu_utilization_pct=avg_cpu, avg_memory_utilization_pct=avg_cpu, active_hours=active,
        idle_hours=idle, idle_cost=idle_cost,
    ))
    db.add(FocusCost(
        id=str(uuid.uuid4()), tenant_id=tenant_id, billing_period_start=TODAY,
        provider_name=provider, service_name="Amazon EC2 (Databricks-managed)", service_category="Analytics",
        region_id="us-east-1", region_name="us-east-1", resource_id=f"databricks/{cluster_id}/nodes",
        resource_name=f"test-{cluster_id}", resource_type="DatabricksNode", sub_account_id="ws-1",
        usage_quantity=32.0, usage_unit="Hrs", list_unit_price=1.0, list_cost=infra_cost,
        billed_cost=infra_cost, effective_cost=infra_cost, currency="USD",
        tags={"team": "platform", "DatabricksClusterId": cluster_id},
        x_team="platform", transformed_at=utcnow(),
    ))
    db.commit()
    return cluster_id


def _seed_job_run(db, tenant_id, cluster_id, *, job_name="test_job", status="success", dbu_cost=10.0, duration=600):
    db.add(DatabricksJobRun(
        id=str(uuid.uuid4()), tenant_id=tenant_id, job_id=f"job-{job_name}", job_name=job_name,
        run_id=str(uuid.uuid4()), cluster_id=cluster_id, workspace_id="ws-1", run_type="scheduled",
        status=status, start_time=utcnow() - timedelta(hours=1), duration_seconds=duration, dbu_cost=dbu_cost,
        tags={"team": "platform"},
    ))
    db.commit()


def test_overview_computes_true_total_and_markup(client, auth, db, tenant_id):
    _seed_one_cluster(db, tenant_id, dbu_cost=100.0, infra_cost=200.0)

    r = client.get("/api/databricks/overview?days=7", headers=auth("analyst"))
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["dbu_cost"] == 100.0
    assert body["infra_cost"] == 200.0
    assert body["true_total_cost"] == 300.0
    assert body["platform_markup_pct"] == 50.0
    assert body["cluster_count"] == 1


def test_dbu_cost_breakdown_by_sku_and_workspace(client, auth, db, tenant_id):
    _seed_one_cluster(db, tenant_id, dbu_cost=80.0)

    r = client.get("/api/databricks/dbu-cost?days=7", headers=auth("analyst"))
    assert r.status_code == 200
    body = r.json()
    assert any(s["sku_name"] == "STANDARD_ALL_PURPOSE_COMPUTE" for s in body["by_sku"])
    assert any(w["workspace"] == "test-workspace" for w in body["by_workspace"])
    assert sum(t["cost"] for t in body["timeseries"]) == 80.0


def test_jobs_summary_computes_success_rate(client, auth, db, tenant_id):
    cluster_id = _seed_one_cluster(db, tenant_id, cluster_type="job")
    _seed_job_run(db, tenant_id, cluster_id, job_name="etl_job", status="success", dbu_cost=10.0)
    _seed_job_run(db, tenant_id, cluster_id, job_name="etl_job", status="success", dbu_cost=10.0)
    _seed_job_run(db, tenant_id, cluster_id, job_name="etl_job", status="failed", dbu_cost=5.0)

    r = client.get("/api/databricks/jobs?days=7", headers=auth("analyst"))
    assert r.status_code == 200
    body = r.json()
    assert body["total_runs"] == 3
    job = next(j for j in body["jobs"] if j["job_name"] == "etl_job")
    assert job["run_count"] == 3
    assert job["failed_count"] == 1
    assert round(job["success_rate_pct"], 1) == 66.7
    assert job["total_cost"] == 25.0


def test_clusters_flags_wasteful_idle_clusters(client, auth, db, tenant_id):
    _seed_one_cluster(db, tenant_id, avg_cpu=20.0, active=2.0, idle=10.0, idle_cost=50.0)  # wasteful
    _seed_one_cluster(db, tenant_id, avg_cpu=70.0, active=10.0, idle=1.0, idle_cost=2.0)   # healthy

    r = client.get("/api/databricks/clusters?days=7", headers=auth("analyst"))
    assert r.status_code == 200
    body = r.json()
    assert body["count"] == 2
    wasteful = [c for c in body["clusters"] if c["wasteful"]]
    assert len(wasteful) == 1
    assert wasteful[0]["idle_cost"] == 50.0

    only = client.get("/api/databricks/clusters?days=7&wasteful_only=true", headers=auth("analyst"))
    assert only.json()["count"] == 1


def test_reconciliation_groups_by_provider(client, auth, db, tenant_id):
    _seed_one_cluster(db, tenant_id, provider="AWS", dbu_cost=60.0, infra_cost=120.0)
    _seed_one_cluster(db, tenant_id, provider="Azure", dbu_cost=40.0, infra_cost=80.0)

    r = client.get("/api/databricks/reconciliation?days=7&group_by=provider", headers=auth("analyst"))
    assert r.status_code == 200
    body = r.json()
    assert body["total_dbu_cost"] == 100.0
    assert body["total_infra_cost"] == 200.0
    assert body["total_true_cost"] == 300.0
    groups = {row["group"]: row for row in body["rows"]}
    assert groups["aws"]["true_total_cost"] == 180.0
    assert groups["azure"]["true_total_cost"] == 120.0


def test_databricks_endpoints_require_read_permission(client, auth):
    r = client.get("/api/databricks/overview", headers=auth("viewer"))
    assert r.status_code == 403


def test_databricks_isolated_per_tenant(client, auth, db, tenant_id):
    """A second tenant's Databricks data must not leak into this tenant's view."""
    _seed_one_cluster(db, tenant_id, dbu_cost=100.0, infra_cost=100.0)

    other_tenant = f"tenant-other-{uuid.uuid4().hex[:8]}"
    from app.models import Tenant
    db.add(Tenant(id=other_tenant, name="Other"))
    db.commit()
    _seed_one_cluster(db, other_tenant, dbu_cost=9999.0, infra_cost=9999.0)

    r = client.get("/api/databricks/overview?days=7", headers=auth("analyst"))
    assert r.json()["dbu_cost"] == 100.0
    assert r.json()["cluster_count"] == 1
