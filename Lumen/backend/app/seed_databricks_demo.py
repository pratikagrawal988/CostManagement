"""
Databricks demo data generator — DBU cost, job runs, cluster utilization, and
the matching "underlying CSP infra" FocusCost rows needed to reconcile the
two cost layers (Databricks bills DBUs for the platform separately from what
AWS/Azure bills for the VMs it provisions on your behalf).

Run via seed_everything() on startup — idempotent, mirrors the pattern in
seed_focus_csp.py / seed_ai_demo.py.
"""
from __future__ import annotations

import random
from datetime import date, timedelta
from typing import List

from sqlalchemy.orm import Session

from .models import (
    DatabricksCluster, DatabricksUsageRecord, DatabricksJobRun,
    DatabricksClusterUtilization, FocusCost, new_id, utcnow,
)

SEED_DAYS = 60

TEAMS = ["platform", "product", "data-science", "growth", "infra"]
COST_CENTERS = ["CC-1010", "CC-2020", "CC-3030", "CC-4040"]

# sku_name -> ($/DBU, cluster_type)
SKU_RATES = {
    "STANDARD_ALL_PURPOSE_COMPUTE": 0.55,
    "STANDARD_JOBS_COMPUTE":        0.30,
    "PREMIUM_JOBS_COMPUTE":         0.40,
    "STANDARD_SQL_COMPUTE":         0.70,
    "DLT_CORE_COMPUTE":             0.36,
}
CLUSTER_TYPE_SKU = {
    "all_purpose":  "STANDARD_ALL_PURPOSE_COMPUTE",
    "job":          "STANDARD_JOBS_COMPUTE",
    "sql_warehouse":"STANDARD_SQL_COMPUTE",
    "dlt":          "DLT_CORE_COMPUTE",
}

# node_type_id -> ($/node-hr underlying CSP infra cost, provider)
NODE_TYPES = {
    "aws":   [("i3.xlarge", 0.312), ("r5.2xlarge", 0.504), ("m5.xlarge", 0.192), ("c5.4xlarge", 0.680)],
    "azure": [("Standard_DS4_v2", 0.38), ("Standard_E8s_v3", 0.57), ("Standard_D4s_v3", 0.192)],
}

WORKSPACES = [
    ("ws-prod-analytics", "prod-analytics",  "aws",   "us-east-1"),
    ("ws-ml-platform",    "ml-platform",     "aws",   "us-west-2"),
    ("ws-data-eng",       "data-eng-azure",  "azure", "eastus"),
    ("ws-bi-reporting",   "bi-reporting",    "aws",   "us-east-1"),
]

# (cluster_type, is_wasteful) — wasteful clusters run interactive all_purpose
# clusters that idle overnight/weekends without auto-terminate discipline.
CLUSTER_DEFS = [
    ("all_purpose",  True),
    ("all_purpose",  True),
    ("all_purpose",  False),
    ("job",          False),
    ("job",          False),
    ("job",          False),
    ("sql_warehouse",False),
    ("sql_warehouse",False),
    ("dlt",          False),
]

JOB_NAMES = [
    "nightly_revenue_rollup", "customer_churn_features", "clickstream_etl",
    "fraud_model_training", "inventory_sync", "marketing_attribution",
    "data_quality_checks", "product_analytics_agg",
]


def _rng(seed_key: str) -> random.Random:
    return random.Random(abs(hash(seed_key)) % (2**31))


def _clusters_for_seed(tenant_id: str) -> List[dict]:
    clusters = []
    cid = 0
    for ws_id, ws_name, provider, region in WORKSPACES:
        node_choices = NODE_TYPES[provider]
        for i, (ctype, wasteful) in enumerate(CLUSTER_DEFS):
            cid += 1
            node_type, infra_rate = node_choices[cid % len(node_choices)]
            team = TEAMS[cid % len(TEAMS)]
            clusters.append({
                "cluster_id": f"{ws_id}-cl-{i:02d}",
                "cluster_name": f"{ws_name}-{ctype}-{i:02d}",
                "workspace_id": ws_id,
                "workspace_name": ws_name,
                "cloud_provider": provider,
                "region": region,
                "cluster_type": ctype,
                "node_type_id": node_type,
                "infra_rate": infra_rate,
                "num_workers": {"all_purpose": 4, "job": 8, "sql_warehouse": 2, "dlt": 6}[ctype],
                "team": team,
                "cost_center": COST_CENTERS[cid % len(COST_CENTERS)],
                "wasteful": wasteful,
            })
    return clusters


def seed_databricks_demo(db: Session, tenant_id: str = "tenant-demo", days: int = SEED_DAYS, force: bool = False) -> dict:
    existing = db.query(DatabricksCluster).filter(DatabricksCluster.tenant_id == tenant_id).first()
    if existing and not force:
        return {"status": "skipped", "reason": "Databricks demo data already present"}

    if existing and force:
        db.query(DatabricksClusterUtilization).filter(DatabricksClusterUtilization.tenant_id == tenant_id).delete(synchronize_session=False)
        db.query(DatabricksJobRun).filter(DatabricksJobRun.tenant_id == tenant_id).delete(synchronize_session=False)
        db.query(DatabricksUsageRecord).filter(DatabricksUsageRecord.tenant_id == tenant_id).delete(synchronize_session=False)
        db.query(DatabricksCluster).filter(DatabricksCluster.tenant_id == tenant_id).delete(synchronize_session=False)
        db.query(FocusCost).filter(
            FocusCost.tenant_id == tenant_id, FocusCost.service_category == "Analytics",
            FocusCost.resource_type == "DatabricksNode",
        ).delete(synchronize_session=False)
        db.commit()

    cluster_defs = _clusters_for_seed(tenant_id)
    today = date.today()
    start_day = today - timedelta(days=days - 1)

    for cdef in cluster_defs:
        db.add(DatabricksCluster(
            id=new_id(), tenant_id=tenant_id, cluster_id=cdef["cluster_id"], cluster_name=cdef["cluster_name"],
            workspace_id=cdef["workspace_id"], workspace_name=cdef["workspace_name"],
            cloud_provider=cdef["cloud_provider"], region=cdef["region"], cluster_type=cdef["cluster_type"],
            node_type_id=cdef["node_type_id"], num_workers=cdef["num_workers"],
            tags={"team": cdef["team"], "cost_center": cdef["cost_center"], "project": cdef["workspace_name"]},
            auto_terminate=not cdef["wasteful"],
        ))
    db.commit()

    usage_rows, util_rows, job_rows, infra_rows = [], [], [], []
    job_cursor = 0

    for day_offset in range(days):
        d = start_day + timedelta(days=day_offset)
        iso = d.isoformat()
        is_weekend = d.weekday() >= 5
        growth = 1.0 + (day_offset * 0.0008)

        for cdef in cluster_defs:
            rng = _rng(f"{cdef['cluster_id']}:{iso}")
            sku = CLUSTER_TYPE_SKU[cdef["cluster_type"]]
            dbu_rate = SKU_RATES[sku]

            # Active/idle hour split — wasteful clusters barely reduce overnight/weekend hours.
            if cdef["wasteful"]:
                active_hours = rng.uniform(4, 8) if not is_weekend else rng.uniform(1, 3)
                idle_hours = 24 - active_hours - rng.uniform(0, 1)
            else:
                base_active = {"all_purpose": 9, "job": 3, "sql_warehouse": 6, "dlt": 4}[cdef["cluster_type"]]
                active_hours = base_active * (0.5 if is_weekend else 1.0) * rng.uniform(0.85, 1.15)
                idle_hours = max(0.0, rng.uniform(0.5, 2.0))

            total_hours = active_hours + idle_hours
            # Calibrated so the DBU platform fee lands ~30-55% on top of the
            # underlying CSP infra cost — realistic Databricks markup range,
            # not a multiple of it.
            dbu_per_node_hour = rng.uniform(0.30, 0.50)
            dbu_quantity = round(total_hours * cdef["num_workers"] * dbu_per_node_hour * growth, 3)
            dbu_cost = round(dbu_quantity * dbu_rate, 4)
            idle_cost = round(idle_hours * cdef["num_workers"] * dbu_per_node_hour * dbu_rate, 4)

            usage_rows.append(DatabricksUsageRecord(
                id=new_id(), tenant_id=tenant_id, cluster_id=cdef["cluster_id"], workspace_id=cdef["workspace_id"],
                sku_name=sku, usage_date=iso, dbu_quantity=dbu_quantity, dbu_unit_price=dbu_rate, dbu_cost=dbu_cost,
            ))
            util_rows.append(DatabricksClusterUtilization(
                id=new_id(), tenant_id=tenant_id, cluster_id=cdef["cluster_id"], date=iso,
                avg_cpu_utilization_pct=round(rng.uniform(15, 35) if cdef["wasteful"] else rng.uniform(45, 78), 1),
                avg_memory_utilization_pct=round(rng.uniform(20, 40) if cdef["wasteful"] else rng.uniform(40, 70), 1),
                active_hours=round(active_hours, 2), idle_hours=round(idle_hours, 2), idle_cost=idle_cost,
            ))

            # Underlying CSP infra cost for the nodes backing this cluster —
            # billed by the cloud provider, separate from the DBU platform fee.
            infra_cost = round(total_hours * cdef["num_workers"] * cdef["infra_rate"] * growth, 4)
            infra_rows.append(FocusCost(
                id=new_id(), tenant_id=tenant_id,
                billing_account_id=f"{cdef['cloud_provider']}-databricks-hosted",
                billing_period_start=iso, billing_period_end=(d + timedelta(days=1)).isoformat(),
                charge_period_start=f"{iso}T00:00:00Z", charge_category="Usage",
                invoice_issuer_name="Amazon Web Services" if cdef["cloud_provider"] == "aws" else "Microsoft",
                provider_name="AWS" if cdef["cloud_provider"] == "aws" else "Azure",
                publisher_name="Amazon" if cdef["cloud_provider"] == "aws" else "Microsoft",
                service_name="Amazon EC2 (Databricks-managed)" if cdef["cloud_provider"] == "aws" else "Virtual Machines (Databricks-managed)",
                service_category="Analytics", sku_id=cdef["node_type_id"], region_id=cdef["region"], region_name=cdef["region"],
                resource_id=f"databricks/{cdef['cluster_id']}/nodes", resource_name=cdef["cluster_name"],
                resource_type="DatabricksNode", resource_status="Running",
                sub_account_id=cdef["workspace_id"], sub_account_name=cdef["workspace_name"],
                pricing_category="Standard", pricing_quantity=round(total_hours * cdef["num_workers"], 3),
                pricing_unit="Hrs", usage_quantity=round(total_hours * cdef["num_workers"], 3), usage_unit="Hrs",
                list_unit_price=round(cdef["infra_rate"] * 1.05, 6), list_cost=round(infra_cost * 1.05, 4),
                billed_cost=infra_cost, effective_cost=infra_cost, currency="USD",
                tags={"team": cdef["team"], "cost_center": cdef["cost_center"], "DatabricksClusterId": cdef["cluster_id"],
                      "managed_by": "databricks"},
                x_team=cdef["team"], x_cost_center=cdef["cost_center"], x_environment="production",
                transformed_at=utcnow(),
            ))

            # Job runs — only for job-type clusters, a handful of named jobs per day.
            if cdef["cluster_type"] == "job":
                n_runs = rng.randint(1, 3)
                for _ in range(n_runs):
                    job_cursor += 1
                    job_name = JOB_NAMES[job_cursor % len(JOB_NAMES)]
                    duration = rng.randint(180, 5400)
                    failed = rng.random() < 0.08
                    run_dbu_cost = round((duration / 3600) * cdef["num_workers"] * dbu_per_node_hour * dbu_rate, 4)
                    job_rows.append(DatabricksJobRun(
                        id=new_id(), tenant_id=tenant_id, job_id=f"job-{job_name}",
                        job_name=job_name, run_id=new_id(), cluster_id=cdef["cluster_id"],
                        workspace_id=cdef["workspace_id"], run_type=rng.choice(["scheduled", "scheduled", "manual"]),
                        status="failed" if failed else "success",
                        start_time=utcnow() - timedelta(days=days - day_offset),
                        duration_seconds=duration, dbu_cost=run_dbu_cost,
                        tags={"team": cdef["team"], "pipeline_owner": cdef["team"]},
                    ))

        if len(usage_rows) >= 2000:
            db.bulk_save_objects(usage_rows); usage_rows = []
            db.bulk_save_objects(util_rows); util_rows = []
            db.bulk_save_objects(infra_rows); infra_rows = []
            db.bulk_save_objects(job_rows); job_rows = []
            db.flush()

    if usage_rows: db.bulk_save_objects(usage_rows)
    if util_rows: db.bulk_save_objects(util_rows)
    if infra_rows: db.bulk_save_objects(infra_rows)
    if job_rows: db.bulk_save_objects(job_rows)
    db.commit()

    return {
        "status": "seeded", "clusters": len(cluster_defs), "days": days,
        "workspaces": len(WORKSPACES),
    }
