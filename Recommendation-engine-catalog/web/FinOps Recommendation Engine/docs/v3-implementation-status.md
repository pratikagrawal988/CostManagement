# FinOps Recommendation Engine — v3.0.0 Implementation Status

> Generated: 2026-04-10 | Covers: Configuration Console prototype (`index.html`)

---

## 1. What Was Delivered

### 1.1 Data Model Expansion

| Area | Before (v2.2) | After (v3.0) |
|------|---------------|--------------|
| **Resource types** | 7 (vm, rds, block_disk, object_storage, container, serverless, network) | **15** — added: gpu_compute, nat_gateway, nosql_db, cache_redis, data_warehouse, k8s_node, snapshot_backup, elastic_ip |
| **Advisory rules** | 12 sample recommendations | **50** covering all 15 resource types with balanced action types (shutdown, rightsize, configure), rec types (cost_saving, performance, security, governance), severities, and complexities |
| **Categories** | 7 | **10** — added: Analytics, Security, Serverless |
| **Mock data templates** | 4 resource types | **15** — every resource type has at least 2 sample records for simulation |
| **CSP API catalog** | 14 namespaces across 4 CSPs | **28** — expanded to cover NAT Gateway, DynamoDB/Cosmos, ElastiCache/Redis, Redshift/Synapse/BigQuery, and OCI equivalents |
| **FinOps Observability** | 5 Elasticsearch index templates | **7** — added gpu_metrics, expanded existing templates |
| **Failure reasons** | 11 entries | **19** — added GPU DCGM, cross-account NAT, Global Table, AMI reference, PDB, DNS dependency, reserved node |

### 1.2 Simulation Framework

- **Per-rule simulation** (`SimulateModal`): Enhanced engine with resource-type-aware rule evaluation. Supports all action types and differentiates cost_saving from security/governance outcomes.
- **Run Now** (`RunNowModal`): Updated to use `resolveResourceType()` for correct mock data selection.
- **Batch Simulation** (new tab): Runs all 50 rules against mock data in sequence, reporting pass/fail/N/A per rule, total advisories generated, suppression counts, and estimated savings. Coverage breakdowns by resource type, severity, and rec type.

### 1.3 Lifecycle & Governance Fixes

| Issue | Fix |
|-------|-----|
| **Approval → Active transition** | "Run Now → Activate" button on approved recs transitions status to `active` after first production run (per spec §9.1) |
| **Disable / Re-enable** | Active recs now have a "⏸ Disable" button; disabled recs show "▶ Re-enable" |
| **Schedule management** | Replaced "Set Schedule — coming soon" with full schedule UI: frequency (hourly/daily/weekly/monthly), execution window, timezone, enable/disable toggle |
| **Audit Trail** | New "Audit" tab on every recommendation showing immutable event log: created, submitted, approved, activated, execution_completed |
| **Connection Health read-only** | Removed "Register New Source" action button; replaced with read-only indicator per product design §2 |

### 1.4 Navigation & Views

- **Customer Advisories** view: Previously dead code — now wired into navigation and accessible from the top bar.
- **Batch Simulation** view: New tab for bulk testing all advisory rules.
- Total navigation items: 10 (Dashboard, Recommendations, Production Monitor, Connection Health, Aggregation Engine, Failure Analysis, Product Catalog, Integrations, Batch Simulation, Customer Advisories).

### 1.5 Data Consistency Fixes

- **730h → 720h**: Product Catalog SKU cost calculations now use 720 hours/month (30d × 24h) consistently across the app, matching requirements.
- **Subcategory → Resource Type mapping**: Added `SUBCATEGORY_TO_RT` resolver so simulation selects correct mock data for every recommendation category.

---

## 2. Architecture: What Exists vs What's Needed for Production SaaS

### 2.1 Current State (Prototype)

```
┌─────────────────────────────────────────────────────┐
│  Single-file React SPA (index.html, ~5200 lines)     │
│  In-browser state • No backend • No persistence       │
│  Mock data constants • setTimeout-based simulation     │
│  No auth • No multi-tenant isolation                   │
└─────────────────────────────────────────────────────┘
```

### 2.2 Target State (Production SaaS)

```
┌──────────────┐   ┌──────────────┐   ┌──────────────┐
│ Config Console│   │  Execution   │   │ Cost Advisory │
│  (this app)  │──▶│  Pipeline    │──▶│   Portal     │
│  React SPA   │   │  (backend)   │   │  (end-user)  │
└──────────────┘   └──────────────┘   └──────────────┘
       │                   │                   │
       ▼                   ▼                   ▼
  ┌─────────┐    ┌──────────────┐    ┌─────────────┐
  │ REST API│    │ Job Scheduler│    │ Customer DB │
  │ + Auth  │    │ (cron/K8s)   │    │ + Advisory  │
  └─────────┘    └──────────────┘    │   Store     │
                        │            └─────────────┘
              ┌─────────┴─────────┐
              │  CSP APIs │ Obs   │
              │  Billing  │ K8s   │
              └───────────────────┘
```

---

## 3. Critical Gaps for Production

### 3.1 Backend & Persistence (CRITICAL)

- **No REST API**: All state is in-memory JavaScript. Requires API layer (Node/Python/Go) with OpenAPI spec.
- **No database**: Recommendation configs, advisory results, audit events, run history — all need durable storage (PostgreSQL recommended).
- **No job scheduler**: Requires cron-like service (Kubernetes CronJob, Temporal, or Celery Beat) to execute recommendations per configured schedule.
- **No real CSP integration**: API calls to CloudWatch, Azure Monitor, GCP Monitoring, OCI Monitoring are mocked. Production needs credential-managed polling with circuit breakers.

### 3.2 Security & Multi-Tenancy (CRITICAL)

- **No authentication**: SSO/OIDC integration needed (Azure AD, Okta, Auth0).
- **No RBAC**: Platform Admin vs Approver roles not enforced. Approval identity is free-text.
- **No tenant isolation**: Customer data must be scoped with row-level security.
- **No secret management**: CSP credentials stored as JS objects, not in vault (AWS Secrets Manager, Azure Key Vault, HashiCorp Vault).

### 3.3 Advisory Lifecycle (MAJOR)

- **No deduplication engine**: Unique key `(recommendation_id, customer_id, resource_id)` not enforced. `generateAdvisoryData` creates new IDs daily.
- **No priority/conflict resolution**: Requirements §8 says shutdown overrides rightsize for same resource — not implemented.
- **No `resolved` state transition**: Advisories should auto-resolve when metric returns above threshold.
- **No suppression rules**: Customer-level and resource-level suppression UI and storage missing.

### 3.4 Operational (MAJOR)

- **No circuit breaker**: CSP API failures should trip circuit breakers (requirements §5.3).
- **No alerting/notifications**: Slack/Teams/email notifications for pipeline failures, SLA breaches, high-severity advisories.
- **No rate limiting**: CSP API rate limits (requirements v3 + csp-native-api.md) not enforced in client code.
- **No metric freshness checks**: Should reject stale data (>4h old) per requirements §10.

### 3.5 Minor / Nice-to-Have

- **Sparklines**: Production Monitor uses `Math.random` — should use real 7-day trend data.
- **Version history**: Recommendation config changes should be versioned (git-like).
- **Export/import recommendations**: Bulk CSV/JSON export for recommendation configs.
- **Dark/light theme**: Currently dark-only.

---

## 4. CSP Integration — Detailed Gap Analysis

### 4.1 What's Documented

| CSP | API | Auth | Documented In |
|-----|-----|------|---------------|
| AWS | CloudWatch `GetMetricData` | IAM Role ARN + External ID | csp-native-api.md §1 |
| Azure | Monitor Metrics API | Service Principal (Client ID + Secret + Tenant) | csp-native-api.md §2 |
| GCP | Cloud Monitoring `timeSeries.list` | Service Account JSON key | csp-native-api.md §3 |
| OCI | Monitoring `SummarizeMetricsData` | User OCID + Key fingerprint + PEM | csp-native-api.md §4 |

### 4.2 What's Implemented in UI

- Integrations view has credential forms for all 4 CSPs with correct field sets.
- Two-stage test connection flow (auth test → sample metric pull) is documented but mock.
- CSP_API_CATALOG provides namespace/field definitions for metric selection in the wizard.

### 4.3 What's Missing

- **No real HTTP client**: All API calls are `setTimeout` stubs.
- **Additional APIs not integrated**: AWS Cost Explorer, AWS Trusted Advisor, AWS Compute Optimizer, Azure Advisor, Azure Cost Management, GCP Recommender — referenced in requirements but not catalogued.
- **Billing API integration**: `billing_api` data source type exists but no credential flow or catalog.
- **Kubernetes API**: `k8s_api` data source type exists but no cluster registration or kubeconfig flow.
- **Third-party tools**: Datadog, New Relic, Prometheus, Grafana — referenced in requirements as data sources but no integration UI or API specs.

---

## 5. Recommendation Coverage Matrix

### 5.1 By Resource Type (15 types, 50 rules)

| Resource Type | Rules | Action Types | Example |
|--------------|-------|-------------|---------|
| vm | 6 | shutdown, rightsize | R001 Idle VM, R029 VM Gen Upgrade |
| gpu_compute | 3 | shutdown, rightsize | R003 GPU Idle, R006 GPU Spot |
| rds | 3 | shutdown, rightsize | R030 Idle RDS, R032 Over-Provisioned Storage |
| nosql_db | 3 | shutdown, rightsize | R009 DynamoDB Idle, R011 Cosmos RU Opt |
| cache_redis | 2 | shutdown, rightsize | R012 Idle Redis, R013 Over-Provisioned |
| data_warehouse | 3 | shutdown, rightsize | R015 Idle Redshift, R016 BigQuery Slot |
| block_disk | 3 | shutdown, rightsize | R018 Orphaned Disk, R034 EBS Type Opt |
| object_storage | 2 | archive, rightsize | R022 Lifecycle, R005 Oversized Bucket |
| container | 3 | rightsize | R014 Over-Provisioned Pod, R036 HPA Misconfig |
| k8s_node | 3 | rightsize | R019 Over-Provisioned Node, R020 Autoscaling |
| serverless | 2 | rightsize, shutdown | R038 Lambda Memory, R039 Unused Functions |
| network | 3 | shutdown, rightsize | R040 Unused LB, R041 Cross-AZ, R073 Egress |
| nat_gateway | 2 | shutdown, rightsize | R007 Idle NAT, R008 Over-Provisioned NAT |
| snapshot_backup | 3 | shutdown, rightsize, governance | R023 Orphaned Snap, R024 Stale AMI |
| elastic_ip | 2 | shutdown | R026 Unattached EIP, R027 Idle Public IP |

### 5.2 By Advisory Type

| Type | Count |
|------|-------|
| cost_saving | 40 |
| security | 2 |
| governance | 3 |
| performance | 5 (via existing rules) |

### 5.3 By Severity

| Severity | Count |
|----------|-------|
| Top | 12 |
| High | 17 |
| Medium | 12 |
| Low | 9 |

---

## 6. Next Steps (Prioritized)

### Phase 1 — Backend Foundation (4-6 weeks)

1. Stand up REST API with OpenAPI spec for recommendation CRUD, run triggers, advisory reads.
2. PostgreSQL schema for recommendations, runs, advisories, audit events, customers.
3. Job scheduler integration (Temporal or K8s CronJob) with execution window support.
4. Authentication gateway (OIDC/SAML) and RBAC middleware.

### Phase 2 — Real CSP Integration (4-6 weeks)

5. AWS CloudWatch client with IAM role assumption and rate limiting.
6. Azure Monitor client with Service Principal auth.
7. GCP Cloud Monitoring client with service account.
8. OCI Monitoring client with API key signing.
9. Circuit breaker and retry logic per CSP.
10. Credential vault integration (secret management).

### Phase 3 — Advisory Lifecycle (3-4 weeks)

11. Deduplication engine with `(rec_id, customer_id, resource_id)` composite key.
12. Priority/conflict resolver (shutdown > rightsize > configure for same resource).
13. Auto-resolve when metrics return to healthy.
14. Suppression rules (customer-level, resource-level, time-based).
15. Notification channels (Slack, Teams, email, webhook).

### Phase 4 — Cost Advisory Portal (4-6 weeks)

16. Separate end-user application for viewing and acting on advisories.
17. Customer-scoped dashboard with savings summary, trend charts.
18. Advisory detail with action workflow (accept, dismiss, snooze).
19. Integration with ticketing systems (Jira, ServiceNow).

---

## 7. Files Modified in This Session

| File | Changes |
|------|---------|
| `index.html` | 15 resource types, 50 recommendations, 15 mock data templates, enhanced CSP API catalog, batch simulation view, audit trail, schedule management, approval→active transition, disable/enable, customer advisory wiring, data consistency fixes |
| `docs/v3-implementation-status.md` | This document (new) |
