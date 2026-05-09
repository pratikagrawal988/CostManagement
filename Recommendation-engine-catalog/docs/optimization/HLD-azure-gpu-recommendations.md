# HLD: Azure GPU Compute Recommendations (Onboarding + Ingestion + Advisory)

## 1. Purpose
Deliver **cost recommendations** (optimization opportunities) for **Azure GPU compute** (VM/AKS/AML/Batch) by onboarding customer access, ingesting required telemetry, and running a rules engine to produce cost recommendations with **explainable evidence**.

This HLD describes the production architecture (the current repo contains a UI prototype only).

## 2. Goals
- Onboard Azure access (tenant/subscriptions) and credentials securely.
- Pull inventory metadata and time-series metrics needed for GPU cost optimization.
- Normalize metrics and compute recommendations using **backend-configured** rules (FinOps/FinOps policy; not customer self-serve UI settings).
- Provide a UI that shows recommendation **status/gating**, **estimated savings**, and a **“metrics used”** evidence view.
- Provide operational observability and a supportable runbook.

## 3. Non-goals (initial release)
- Fully automated remediation (e.g., resize VM, change node pools) without customer approval.
- Full cross-cloud GPU parity in V1 (Azure-only).
- Guarantee GPU utilization availability without customer telemetry enablement (platform will show partial coverage).

## 4. Supported resources (scope)
- **Azure Virtual Machines** (GPU families: NC/ND/NV/NVads, etc.)
- **AKS** GPU node pools (where GPU metrics are exported)
- **Azure Machine Learning** compute clusters / compute instances (job/activity metadata)
- **Azure Batch** pools (job/task metadata)

## 5. High-level architecture

### 5.1 Components
- **UI (Web App)**
  - Azure connection onboarding wizard
  - GPU metrics readiness dashboard (health/coverage/blockers)
  - GPU compute recommendations list + evidence viewer
- **Platform API**
  - CRUD for connections, secrets references
  - Connection validation endpoint
  - Endpoints for readiness, recommendations, and evidence retrieval
- **Secret Store**
  - Stores encrypted secrets or Key Vault references
  - Rotations/expiry metadata
- **Scheduler / Workers**
  - Inventory sync job
  - Metrics pull job
  - Recommendation evaluation job
- **Inventory Store**
  - Canonical resource catalog keyed by Azure resourceId
  - Enriched with SKU metadata, tags, and service classification
- **Metrics Store**
  - Time-series metric storage (normalized schema)
  - Dimensions for service/workload identification
- **Rules Engine**
  - Evaluates recommendation rules
  - Produces recommendation records + evidence payloads
- **Recommendation Store**
  - Stores recommendations, status, savings estimate, and evidence references
- **Observability**
  - Logs, traces, metrics for ingestion and evaluation pipelines

### 5.2 Data flow (high level)
1. User enters onboarding details (tenant/subscriptions/SP creds).
2. Platform validates: token → inventory sample → metrics sample.
3. Scheduler runs inventory and metrics pulls periodically.
4. Normalizer converts raw telemetry into internal schema.
5. Rules engine evaluates and stores recommendations + evidence.
6. UI fetches and displays recommendations; evidence view shows metrics used.

## 6. Trust, security, and permissions
- **Least privilege**:
  - Minimum roles: `Reader` + `Monitoring Reader` on subscription scope.
  - Additional roles only if platform config automation is enabled.
- **Secret handling**:
  - Prefer **Key Vault reference**; otherwise store secrets encrypted.
  - Never echo secrets back to UI.
- **Tenant isolation**:
  - Partition all data by customer/org/tenant.
  - Ensure resourceId scoping in all queries.

## 7. Readiness and gating model
Readiness is a first-class concept to prevent noisy/incorrect recommendations:
- **Not onboarded**: no connection exists.
- **Disconnected**: auth failure or missing permissions.
- **Degraded**: partial metrics coverage or insufficient history.
- **Connected**: sufficient history + sufficient coverage.

UI must show:
- coverage stats: `resourcesWithGpuMetrics/totalGpuResources`
- blocking items (missing GPU metrics, insufficient history, missing permissions)
- which recommendation types are available vs blocked

## 8. Recommendations (types)
At minimum, support the following **cost recommendation** types with evidence:
- Rightsize/change GPU SKU
- Idle shutdown/deallocate
- Enable autoscale / scale-to-zero
- Use Spot for interruptible workloads
- Commitments (Savings Plan / RI)
- AKS bin-packing/scheduling
- Move always-on VM to job-native pattern
- Cleanup orphan artifacts (disks/snapshots)

## 9. Key milestones (implementation)
- M0: UI onboarding flow + connection entity model
- M1: Validation endpoint + readiness computation
- M2: Inventory sync pipeline
- M3: Metrics pull pipeline + normalization
- M4: Rules engine + evidence model + recommendation store
- M5: UI recommendations list + evidence viewer + gating
- M6: Operational dashboards + alerts + runbooks

## 10. SLIs / SLOs (suggested)
- Ingestion freshness: latest metrics pull within **≤ 60 min** of schedule.
- Inventory freshness: inventory sync within **≤ 24 hours**.
- Recommendation freshness: recommendations evaluated within **≤ 2 hours** after metrics ingestion.
- API p95 latency: list recommendations **< 500ms** (cached/indexed).
- Data correctness: evidence links to exact metric windows used.

## 11. Risks and mitigations
- **GPU util not available in Azure Monitor by default**:
  - Mitigation: readiness shows coverage; allow partial recommendations; document telemetry requirements.
- **API throttling/limits**:
  - Mitigation: adaptive backoff; batching; caching; staggered schedules.
- **Credential expiry**:
  - Mitigation: detect and alert; show “credential expiring soon”; support rotation.


