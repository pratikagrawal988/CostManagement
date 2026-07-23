"""
Databricks cost dashboard — DBU consumption, job/pipeline cost, cluster
utilization/idle waste, and reconciliation against the underlying CSP infra
cost (Databricks bills DBUs for the platform layer separately from what the
cloud provider bills for the VMs it provisions on your behalf).

Endpoints:
  GET /api/databricks/overview        — top-line KPI strip
  GET /api/databricks/dbu-cost        — DBU cost time series + breakdowns
  GET /api/databricks/jobs            — per-job cost/success-rate summary
  GET /api/databricks/clusters        — cluster inventory + utilization/idle
  GET /api/databricks/reconciliation  — DBU cost vs. CSP infra cost, per cluster/provider
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .auth import TokenPayload
from .database import get_db
from .models import (
    DatabricksCluster, DatabricksClusterUtilization, DatabricksJobRun,
    DatabricksUsageRecord, FocusCost,
)
from .rbac import require_permission

router = APIRouter(prefix="/api/databricks", tags=["databricks"])

# Below this average CPU utilization (and idle > active hours), a cluster is
# flagged as a waste/optimization candidate on the dashboard.
WASTEFUL_UTIL_THRESHOLD_PCT = 35.0


def _window(days: int) -> tuple[str, str]:
    end = date.today()
    start = end - timedelta(days=days - 1)
    return start.isoformat(), end.isoformat()


def _window_datetimes(days: int) -> tuple[datetime, datetime]:
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    return start, end


def _clusters_by_id(db: Session, tenant_id: str) -> dict[str, DatabricksCluster]:
    return {c.cluster_id: c for c in db.query(DatabricksCluster).filter(DatabricksCluster.tenant_id == tenant_id).all()}


# ── Overview ───────────────────────────────────────────────────────────────────

@router.get("/overview")
def overview(
    days: int = Query(30, ge=1, le=365),
    current: TokenPayload = Depends(require_permission("databricks:read")),
    db: Session = Depends(get_db),
):
    start, end = _window(days)
    start_dt, end_dt = _window_datetimes(days)
    tenant_id = current.tenant_id

    usage = db.query(DatabricksUsageRecord).filter(
        DatabricksUsageRecord.tenant_id == tenant_id,
        DatabricksUsageRecord.usage_date >= start, DatabricksUsageRecord.usage_date <= end,
    ).all()
    total_dbu_cost = round(sum(u.dbu_cost for u in usage), 2)
    total_dbu_quantity = round(sum(u.dbu_quantity for u in usage), 1)

    infra_rows = db.query(FocusCost).filter(
        FocusCost.tenant_id == tenant_id, FocusCost.resource_type == "DatabricksNode",
        FocusCost.billing_period_start >= start, FocusCost.billing_period_start <= end,
    ).all()
    total_infra_cost = round(sum(f.effective_cost for f in infra_rows), 2)

    util = db.query(DatabricksClusterUtilization).filter(
        DatabricksClusterUtilization.tenant_id == tenant_id,
        DatabricksClusterUtilization.date >= start, DatabricksClusterUtilization.date <= end,
    ).all()
    total_idle_cost = round(sum(u.idle_cost for u in util), 2)
    total_active_hours = sum(u.active_hours for u in util)
    total_idle_hours = sum(u.idle_hours for u in util)

    jobs = db.query(DatabricksJobRun).filter(
        DatabricksJobRun.tenant_id == tenant_id,
        DatabricksJobRun.start_time >= start_dt, DatabricksJobRun.start_time <= end_dt,
    ).all()
    total_jobs = len(jobs)
    failed_jobs = sum(1 for j in jobs if j.status == "failed")
    job_success_rate = round(100.0 * (total_jobs - failed_jobs) / total_jobs, 1) if total_jobs else 100.0

    clusters = db.query(DatabricksCluster).filter(DatabricksCluster.tenant_id == tenant_id).all()
    workspaces = {c.workspace_id for c in clusters}

    true_total = round(total_dbu_cost + total_infra_cost, 2)
    markup_pct = round(100.0 * total_dbu_cost / total_infra_cost, 1) if total_infra_cost else 0.0

    return {
        "window": {"start": start, "end": end, "days": days},
        "dbu_cost": total_dbu_cost,
        "dbu_quantity": total_dbu_quantity,
        "infra_cost": total_infra_cost,
        "true_total_cost": true_total,
        "platform_markup_pct": markup_pct,
        "idle_cost": total_idle_cost,
        "idle_hours": round(total_idle_hours, 1),
        "active_hours": round(total_active_hours, 1),
        "utilization_pct": round(100.0 * total_active_hours / (total_active_hours + total_idle_hours), 1) if (total_active_hours + total_idle_hours) else 0.0,
        "job_runs": total_jobs,
        "job_failures": failed_jobs,
        "job_success_rate_pct": job_success_rate,
        "cluster_count": len(clusters),
        "workspace_count": len(workspaces),
    }


# ── DBU cost breakdown ────────────────────────────────────────────────────────

@router.get("/dbu-cost")
def dbu_cost(
    days: int = Query(30, ge=1, le=365),
    current: TokenPayload = Depends(require_permission("databricks:read")),
    db: Session = Depends(get_db),
):
    start, end = _window(days)
    tenant_id = current.tenant_id
    clusters = _clusters_by_id(db, tenant_id)

    usage = db.query(DatabricksUsageRecord).filter(
        DatabricksUsageRecord.tenant_id == tenant_id,
        DatabricksUsageRecord.usage_date >= start, DatabricksUsageRecord.usage_date <= end,
    ).all()

    by_day: dict[str, float] = defaultdict(float)
    by_sku: dict[str, float] = defaultdict(float)
    by_cluster_type: dict[str, float] = defaultdict(float)
    by_workspace: dict[str, float] = defaultdict(float)

    for u in usage:
        by_day[u.usage_date] += u.dbu_cost
        by_sku[u.sku_name] += u.dbu_cost
        cluster = clusters.get(u.cluster_id)
        by_cluster_type[cluster.cluster_type if cluster else "unknown"] += u.dbu_cost
        by_workspace[cluster.workspace_name if cluster else u.workspace_id] += u.dbu_cost

    return {
        "window": {"start": start, "end": end},
        "timeseries": [{"date": d, "cost": round(c, 2)} for d, c in sorted(by_day.items())],
        "by_sku": [{"sku_name": k, "cost": round(v, 2)} for k, v in sorted(by_sku.items(), key=lambda kv: -kv[1])],
        "by_cluster_type": [{"cluster_type": k, "cost": round(v, 2)} for k, v in sorted(by_cluster_type.items(), key=lambda kv: -kv[1])],
        "by_workspace": [{"workspace": k, "cost": round(v, 2)} for k, v in sorted(by_workspace.items(), key=lambda kv: -kv[1])],
    }


# ── Jobs ──────────────────────────────────────────────────────────────────────

@router.get("/jobs")
def jobs_summary(
    days: int = Query(30, ge=1, le=365),
    current: TokenPayload = Depends(require_permission("databricks:read")),
    db: Session = Depends(get_db),
):
    start_dt, end_dt = _window_datetimes(days)
    tenant_id = current.tenant_id

    runs = db.query(DatabricksJobRun).filter(
        DatabricksJobRun.tenant_id == tenant_id,
        DatabricksJobRun.start_time >= start_dt, DatabricksJobRun.start_time <= end_dt,
    ).all()

    by_job: dict[str, dict] = {}
    for r in runs:
        entry = by_job.setdefault(r.job_name, {
            "job_name": r.job_name, "run_count": 0, "success_count": 0, "failed_count": 0,
            "total_cost": 0.0, "total_duration_seconds": 0,
        })
        entry["run_count"] += 1
        entry["total_cost"] += r.dbu_cost
        entry["total_duration_seconds"] += r.duration_seconds
        if r.status == "failed":
            entry["failed_count"] += 1
        elif r.status == "success":
            entry["success_count"] += 1

    jobs = []
    for j in by_job.values():
        j["total_cost"] = round(j["total_cost"], 2)
        j["success_rate_pct"] = round(100.0 * j["success_count"] / j["run_count"], 1) if j["run_count"] else 0.0
        j["avg_duration_seconds"] = round(j["total_duration_seconds"] / j["run_count"], 0) if j["run_count"] else 0
        jobs.append(j)
    jobs.sort(key=lambda j: -j["total_cost"])

    return {
        "window_days": days,
        "total_runs": len(runs),
        "total_failures": sum(j["failed_count"] for j in jobs),
        "jobs": jobs,
    }


# ── Clusters ──────────────────────────────────────────────────────────────────

@router.get("/clusters")
def clusters_inventory(
    days: int = Query(30, ge=1, le=365),
    wasteful_only: bool = Query(False),
    current: TokenPayload = Depends(require_permission("databricks:read")),
    db: Session = Depends(get_db),
):
    start, end = _window(days)
    tenant_id = current.tenant_id

    clusters = db.query(DatabricksCluster).filter(DatabricksCluster.tenant_id == tenant_id).all()

    usage_by_cluster: dict[str, float] = defaultdict(float)
    for u in db.query(DatabricksUsageRecord).filter(
        DatabricksUsageRecord.tenant_id == tenant_id,
        DatabricksUsageRecord.usage_date >= start, DatabricksUsageRecord.usage_date <= end,
    ).all():
        usage_by_cluster[u.cluster_id] += u.dbu_cost

    infra_by_cluster: dict[str, float] = defaultdict(float)
    for f in db.query(FocusCost).filter(
        FocusCost.tenant_id == tenant_id, FocusCost.resource_type == "DatabricksNode",
        FocusCost.billing_period_start >= start, FocusCost.billing_period_start <= end,
    ).all():
        cid = (f.tags or {}).get("DatabricksClusterId", "")
        if cid:
            infra_by_cluster[cid] += f.effective_cost

    util_by_cluster: dict[str, dict] = defaultdict(lambda: {"cpu": [], "active": 0.0, "idle": 0.0, "idle_cost": 0.0})
    for u in db.query(DatabricksClusterUtilization).filter(
        DatabricksClusterUtilization.tenant_id == tenant_id,
        DatabricksClusterUtilization.date >= start, DatabricksClusterUtilization.date <= end,
    ).all():
        e = util_by_cluster[u.cluster_id]
        e["cpu"].append(u.avg_cpu_utilization_pct)
        e["active"] += u.active_hours
        e["idle"] += u.idle_hours
        e["idle_cost"] += u.idle_cost

    items = []
    for c in clusters:
        u = util_by_cluster.get(c.cluster_id, {"cpu": [], "active": 0.0, "idle": 0.0, "idle_cost": 0.0})
        avg_cpu = round(sum(u["cpu"]) / len(u["cpu"]), 1) if u["cpu"] else 0.0
        dbu_cost = round(usage_by_cluster.get(c.cluster_id, 0.0), 2)
        infra_cost = round(infra_by_cluster.get(c.cluster_id, 0.0), 2)
        wasteful = avg_cpu < WASTEFUL_UTIL_THRESHOLD_PCT and u["idle"] > u["active"]

        items.append({
            "cluster_id": c.cluster_id, "cluster_name": c.cluster_name,
            "workspace_name": c.workspace_name, "cloud_provider": c.cloud_provider, "region": c.region,
            "cluster_type": c.cluster_type, "node_type_id": c.node_type_id, "num_workers": c.num_workers,
            "tags": c.tags, "auto_terminate": c.auto_terminate,
            "dbu_cost": dbu_cost, "infra_cost": infra_cost, "true_total_cost": round(dbu_cost + infra_cost, 2),
            "avg_cpu_utilization_pct": avg_cpu,
            "active_hours": round(u["active"], 1), "idle_hours": round(u["idle"], 1),
            "idle_cost": round(u["idle_cost"], 2),
            "wasteful": wasteful,
        })

    if wasteful_only:
        items = [i for i in items if i["wasteful"]]
    items.sort(key=lambda i: -i["true_total_cost"])

    return {"window": {"start": start, "end": end}, "count": len(items), "clusters": items}


# ── Reconciliation ─────────────────────────────────────────────────────────────

@router.get("/reconciliation")
def reconciliation(
    days: int = Query(30, ge=1, le=365),
    group_by: str = Query("cluster", description="cluster | provider | workspace"),
    current: TokenPayload = Depends(require_permission("databricks:read")),
    db: Session = Depends(get_db),
):
    """
    Marries the Databricks platform-fee layer (DBU cost) against the
    underlying CSP infra cost (EC2/VM instances Databricks provisions) so the
    true total cost per cluster/provider/workspace is visible in one place —
    the two normally live in entirely separate billing systems.
    """
    start, end = _window(days)
    tenant_id = current.tenant_id
    clusters = _clusters_by_id(db, tenant_id)

    usage_by_cluster: dict[str, float] = defaultdict(float)
    for u in db.query(DatabricksUsageRecord).filter(
        DatabricksUsageRecord.tenant_id == tenant_id,
        DatabricksUsageRecord.usage_date >= start, DatabricksUsageRecord.usage_date <= end,
    ).all():
        usage_by_cluster[u.cluster_id] += u.dbu_cost

    infra_by_cluster: dict[str, float] = defaultdict(float)
    for f in db.query(FocusCost).filter(
        FocusCost.tenant_id == tenant_id, FocusCost.resource_type == "DatabricksNode",
        FocusCost.billing_period_start >= start, FocusCost.billing_period_start <= end,
    ).all():
        cid = (f.tags or {}).get("DatabricksClusterId", "")
        if cid:
            infra_by_cluster[cid] += f.effective_cost

    def _key_for(cluster_id: str) -> str:
        c = clusters.get(cluster_id)
        if not c:
            return cluster_id
        if group_by == "provider":
            return c.cloud_provider
        if group_by == "workspace":
            return c.workspace_name
        return c.cluster_name

    grouped: dict[str, dict] = defaultdict(lambda: {"dbu_cost": 0.0, "infra_cost": 0.0})
    all_cluster_ids = set(usage_by_cluster) | set(infra_by_cluster)
    for cid in all_cluster_ids:
        key = _key_for(cid)
        grouped[key]["dbu_cost"] += usage_by_cluster.get(cid, 0.0)
        grouped[key]["infra_cost"] += infra_by_cluster.get(cid, 0.0)

    rows = []
    for key, v in grouped.items():
        dbu_cost = round(v["dbu_cost"], 2)
        infra_cost = round(v["infra_cost"], 2)
        rows.append({
            "group": key, "dbu_cost": dbu_cost, "infra_cost": infra_cost,
            "true_total_cost": round(dbu_cost + infra_cost, 2),
            "platform_markup_pct": round(100.0 * dbu_cost / infra_cost, 1) if infra_cost else 0.0,
        })
    rows.sort(key=lambda r: -r["true_total_cost"])

    total_dbu = round(sum(r["dbu_cost"] for r in rows), 2)
    total_infra = round(sum(r["infra_cost"] for r in rows), 2)

    return {
        "window": {"start": start, "end": end}, "group_by": group_by,
        "total_dbu_cost": total_dbu, "total_infra_cost": total_infra,
        "total_true_cost": round(total_dbu + total_infra, 2),
        "overall_markup_pct": round(100.0 * total_dbu / total_infra, 1) if total_infra else 0.0,
        "rows": rows,
    }
