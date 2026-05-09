# FinOps Recommendation Engine — Requirements Specification v3

**Version:** 3.0
**Date:** 2026-03-04
**Status:** Requirements for development handoff

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [End-to-End Flow](#2-end-to-end-flow)
3. [Entity Relationship Model](#3-entity-relationship-model)
4. [Integration & Metric Onboarding Flow](#4-integration--metric-onboarding-flow)
5. [Execution Pipeline](#5-execution-pipeline)
6. [Advisory Data Model](#6-advisory-data-model)
7. [Suppression & Deduplication](#7-suppression--deduplication)
8. [Priority & Conflict Resolution](#8-priority--conflict-resolution)
9. [Advisory Lifecycle & Update Semantics](#9-advisory-lifecycle--update-semantics)
10. [Operational Requirements](#10-operational-requirements)
11. [Audit Trail](#11-audit-trail)
12. [Integration Point Specifications](#12-integration-point-specifications)
13. [End-User Advisory Experience](#13-end-user-advisory-experience)
14. [Open Items & Future Roadmap](#14-open-items--future-roadmap)

---

## 1. System Overview

The FinOps Recommendation Engine is a **two-part system**:

| Surface | User | Purpose |
|---------|------|---------|
| **Configuration Console** (this tool) | Platform Admin / FinOps Engineering | Configure, validate, approve, and monitor recommendations |
| **Cost Advisory Portal** (separate app) | End Users (cloud customers) | View advisories, review evidence, acknowledge/act on recommendations |

The Configuration Console produces **recommendation configurations**. The **Execution Pipeline** (backend) runs these configurations against real customer data to produce **advisories**. The Cost Advisory Portal consumes advisories.

```
┌─────────────────────┐     ┌──────────────────────┐     ┌─────────────────────┐
│  Configuration      │     │  Execution Pipeline   │     │  Cost Advisory       │
│  Console (Platform) │────▶│  (Backend Engine)     │────▶│  Portal (End Users)  │
│                     │     │                       │     │                      │
│  Define recs        │     │  Fetch metrics        │     │  View advisories     │
│  Map metrics        │     │  Evaluate rules       │     │  Review evidence     │
│  Approve & test     │     │  Generate advisories  │     │  Acknowledge/act     │
│  Monitor health     │     │  Calculate savings    │     │  Filter by savings   │
└─────────────────────┘     └──────────────────────┘     └─────────────────────┘
         │                           │                            │
         │                    ┌──────┴──────┐                     │
         │                    │  Data Stores │                     │
         │                    ├─────────────┤                     │
         └───────────────────▶│ Rec Configs │                     │
                              │ Advisories  │◀────────────────────┘
                              │ Audit Log   │
                              │ Run History │
                              └─────────────┘
```

---

## 2. End-to-End Flow

This section traces the complete lifecycle from integration setup through advisory delivery. **This is the tightly stitched flow.**

### Phase 1: Integration Setup (one-time per CSP)

```
Platform Admin
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│ INTEGRATIONS TAB                                         │
│                                                          │
│  1. Select CSP (AWS / Azure / GCP / OCI)                │
│  2. Enter credentials (Role ARN, Service Principal, etc.)│
│  3. Save Credentials → stored in Vault                   │
│  4. Test Connection (2-stage):                           │
│     Stage 1: Auth check (can we authenticate?)           │
│     Stage 2: Pull sample metric for customer 636         │
│  5. On success → CSP status = "healthy"                  │
│                                                          │
│  Similarly for FinOps Observability:                    │
│  1. Configure endpoint / auth                            │
│  2. Validate Pipeline → resolve index, query, confirm    │
└─────────────────────────────────────────────────────────┘
```

**Output:** Integration state with healthy/degraded/disconnected status per source.

### Phase 2: Metric Catalog (automatic, derived from integrations)

```
Once a CSP integration is healthy:
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│ METRIC CATALOG (populated automatically)                 │
│                                                          │
│  For each CSP with status = "healthy":                   │
│    Load CSP_API_CATALOG[csp].namespaces[]               │
│      Each namespace maps to a RESOURCE TYPE:             │
│        AWS/EC2           → vm (Virtual Machine)          │
│        AWS/RDS           → rds (Relational Database)     │
│        AWS/EBS           → block_disk                    │
│        AWS/S3            → object_storage                │
│        Azure/VMs         → vm                            │
│        Azure/SQL         → rds                           │
│        ... etc.                                          │
│                                                          │
│  Each namespace has fields (metrics):                    │
│    CPUUtilization, MemoryUtilization, NetworkIn, etc.    │
│                                                          │
│  For FinOps Observability (if healthy):                 │
│    Load FINOPS_INDEX_TEMPLATES[]                        │
│      Each template maps to a RESOURCE TYPE:              │
│        vm_metrics        → vm                            │
│        k8s_pod           → container                     │
│        db_metrics        → rds                           │
│        storage_metrics   → block_disk, object_storage    │
│        network_metrics   → network                       │
│      Each template has fields (metrics)                  │
│                                                          │
│  THE BINDING: RESOURCE_TYPES[].cspNamespaces{} maps      │
│  resource type → CSP namespace.                          │
│  RESOURCE_TYPES[].obsTemplate maps resource type →       │
│  FinOps Observability index template.                   │
│                                                          │
│  So when a user selects a resource type in the wizard,   │
│  ONLY the metrics from matching namespaces/templates     │
│  are shown.                                              │
└─────────────────────────────────────────────────────────┘
```

**Key constraint:** A metric is available in the wizard ONLY IF:
1. Its source integration is healthy, AND
2. Its namespace/template maps to the selected resource type

### Phase 3: Create Recommendation (wizard)

```
Platform Admin
    │
    ▼
Step 1: Basic Info + Action Type
    │  Name, description, action type (shutdown / rightsize),
    │  recommendation type (cost_saving / performance / governance),
    │  category, subcategory
    │
    ▼
Step 2: Cloud Provider + Classification
    │  Select ONE CSP (single-select)
    │  Severity, complexity
    │
    ▼
Step 3: Resource Type & Metrics
    │  a. Select resource type (vm, rds, block_disk, etc.)
    │     → This FILTERS the available metrics to only those
    │       from namespaces/templates mapped to this resource type
    │
    │  b. Select data source (the selected CSP OR FinOps Obs)
    │     → Can only select ONE source at a time
    │     → Metrics shown are filtered by: resource type + source
    │
    │  c. Pick metrics from the filtered list
    │     → For each metric, configure:
    │       - Historical data window (e.g., 14 days)
    │       - Field name mapping (auto-suggested, editable)
    │     → Aggregation is NOT set here (set in Step 4 per rule)
    │
    ▼
Step 4: Rule Logic & Triggers
    │  Build conditions using Step 3 metrics:
    │    metric → aggregation function → operator → threshold + unit
    │  Combine with AND / OR groups
    │  Same metric can appear with different aggregations
    │    (e.g., avg(CPU) < 5% AND max(CPU) < 15%)
    │  Warning if a Step 3 metric is not used in any condition
    │
    ▼
Step 5: SKU Mapping (RIGHTSIZE only, skipped for SHUTDOWN)
    │  Define SKU groups with constraints:
    │    - Which SKUs are interchangeable
    │    - Resize direction, max delta, buffer %, family lock
    │  This determines WHICH alternative SKU gets recommended
    │
    ▼
Step 6: Savings & Benefits
    │  Read-only formula display (auto-calculated from action type)
    │  Benefit description, savings percentage estimate
    │  → Submit for Approval
    │
    ▼
Recommendation status: PENDING APPROVAL
```

### Phase 4: Approval & Validation

```
Approver reviews → clicks Approve → identity + timestamp recorded
    │
    ▼
Recommendation status: APPROVED
    │
    ├──▶ Run Now (test against customer 636 with real data)
    ├──▶ Simulate Now (test against mock data, editable)
    │
    ▼
On first successful production execution:
Recommendation status: ACTIVE
```

### Phase 5: Execution Pipeline (backend — runs on schedule)

```
Scheduler (daily default, configurable per recommendation)
    │
    ▼
For each ACTIVE recommendation:
    │
    ▼
┌─────────────────────────────────────────────────────────┐
│ EXECUTION PIPELINE                                       │
│                                                          │
│  1. SCOPE: Determine target customers                    │
│     → All customers with the selected CSP                │
│     → Each customer has N resources of the resource type │
│                                                          │
│  2. RESOURCE DISCOVERY: For each customer                │
│     → Query resource inventory for the resource type     │
│       (e.g., list all VMs for customer X on Azure)       │
│     → Get: resource_id, region, current_sku, metadata    │
│                                                          │
│  3. METRIC FETCH: For each resource                      │
│     → Pull historical metrics for the configured window  │
│     → Source: CSP API or FinOps Observability            │
│       - CSP: Use the field name from cspMappings         │
│         for the recommendation's CSP                     │
│       - Obs: Resolve index template with customer_id,    │
│         query Elasticsearch for the configured fields    │
│     → Check: sufficient data available?                  │
│       If metric history < configured window → SKIP       │
│       (this handles recently created resources)          │
│                                                          │
│  4. RULE EVALUATION: For each resource with enough data  │
│     → Apply each condition from ruleGroups:              │
│       a. Select metric data series                       │
│       b. Apply aggregation function (avg, max, p95...)   │
│          over the configured historical window           │
│       c. Compare result against threshold + operator     │
│     → Combine conditions via AND/OR logic                │
│     → Result: TRIGGERED or NOT TRIGGERED                 │
│                                                          │
│  5. SKU RECOMMENDATION (rightsize only):                 │
│     If triggered AND actionType = rightsize:             │
│     → Look up current SKU in Product Catalog             │
│     → Find the SKU group containing the current SKU      │
│     → Apply constraints (direction, max delta, buffer)   │
│     → Select the optimal alternative SKU that:           │
│       a. Meets the utilization + buffer requirement      │
│       b. Satisfies family/direction constraints          │
│       c. Has the lowest cost                             │
│     → If no valid alternative found → DO NOT generate    │
│       advisory (resource stays as-is)                    │
│                                                          │
│  6. SAVINGS CALCULATION:                                 │
│     → Shutdown: current_sku_cost_per_hr × 720            │
│     → Rightsize: (current - recommended) × 720           │
│     → If savings ≤ 0 → SUPPRESS (do not create advisory) │
│     → Performance/governance → savings = N/A             │
│                                                          │
│  7. ADVISORY GENERATION / UPDATE:                        │
│     → Check if advisory already exists for this          │
│       (recommendation_id + customer_id + resource_id)    │
│     → If EXISTS: update metric values, savings,          │
│       evidence, last_evaluated_at                        │
│     → If NOT EXISTS: create new advisory                 │
│     → If previously existed but rule no longer triggers: │
│       mark advisory as RESOLVED                          │
│                                                          │
│  8. RECORD RUN RESULTS:                                  │
│     → Log: resources_checked, advisories_generated,      │
│       advisories_updated, suppressions, failures,        │
│       duration, errors                                   │
└─────────────────────────────────────────────────────────┘
```

### Phase 6: End-User Consumption

```
End user logs into Cost Advisory Portal
    │
    ▼
Dashboard: Total savings, recommendations by category, impacted resources
    │
    ▼
Drill into category → List of advisories for their resources
    │
    ▼
Drill into advisory → Evidence (metrics used, utilization charts)
```

*The Cost Advisory Portal already has a mock UI at `web/CXP Optimization/Cost Recommendations/`.*

---

## 3. Entity Relationship Model

```
┌──────────────┐     ┌───────────────────┐     ┌──────────────────┐
│ Integration  │     │ Metric Catalog     │     │ Resource Type    │
│              │     │                    │     │                  │
│ csp_id       │──┐  │ metric_id (PK)    │  ┌──│ id (PK)          │
│ status       │  │  │ name              │  │  │ label            │
│ credentials  │  │  │ source_type       │  │  │ category         │
│ last_tested  │  └─▶│ csp_id (FK)       │  │  │ csp_namespaces{} │
└──────────────┘     │ namespace_id      │◀─┘  │ obs_template     │
                     │ unit              │     │ suggested[]      │
                     │ field_type        │     └──────────────────┘
                     │ resource_type (FK)│
                     │ description       │
                     └───────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌──────────────────┐  ┌──────────────┐  ┌───────────────────┐
│ Recommendation   │  │ Rule Group   │  │ Advisory          │
│                  │  │              │  │                    │
│ id (PK)          │  │ id (PK)      │  │ advisory_id (PK)  │
│ name             │  │ rec_id (FK)  │  │ recommendation_id  │
│ action_type      │  │ conditions[] │  │ customer_id        │
│ rec_type         │  │ connectors[] │  │ resource_id        │
│ category         │  │              │  │ current_sku        │
│ csp              │  └──────────────┘  │ recommended_sku    │
│ resource_type    │         │          │ recommended_action │
│ metrics[]        │         ▼          │ savings_30d        │
│ rule_groups[]    │  ┌──────────────┐  │ evidence{}         │
│ sku_groups[]     │  │ Condition    │  │ status             │
│ status           │  │              │  │ created_at         │
│ schedule         │  │ metric       │  │ last_evaluated_at  │
│ created_by       │  │ agg_fn       │  │ resolved_at        │
│ approved_by      │  │ operator     │  └───────────────────┘
│ ...              │  │ threshold    │
└──────────────────┘  │ threshold_unit│
                      │ window       │
                      └──────────────┘
```

### The Critical Binding: Resource Type → Metrics

This is the chain that determines which metrics appear in the wizard:

```
RESOURCE_TYPES[].cspNamespaces = {
  aws:   "AWS/EC2",              ← CSP namespace ID
  azure: "Microsoft.Compute/virtualMachines",
  gcp:   "compute.googleapis.com/instance",
  oci:   "oci_computeagent"
}

CSP_API_CATALOG[aws].namespaces[] = [
  { id: "AWS/EC2", fields: [CPUUtilization, NetworkIn, ...] }   ← metrics for VM on AWS
  { id: "AWS/RDS", fields: [CPUUtilization, DatabaseConnections, ...] }
]

When user selects:
  Resource Type = "vm" + Data Source = "Azure"
  → Look up: RESOURCE_TYPES["vm"].cspNamespaces["azure"]
     = "Microsoft.Compute/virtualMachines"
  → Filter: CSP_API_CATALOG["azure"].namespaces
     where id = "Microsoft.Compute/virtualMachines"
  → Show: those namespace's fields as available metrics

Similarly for FinOps Observability:
  Resource Type = "vm" + Data Source = "FinOps Obs"
  → Look up: RESOURCE_TYPES["vm"].obsTemplate = "vm_metrics"
  → Filter: FINOPS_INDEX_TEMPLATES where id = "vm_metrics"
  → Show: that template's fields as available metrics
```

**This binding ensures only resource-appropriate metrics are shown.**

---

## 4. Integration & Metric Onboarding Flow

### Current Metric Availability

Metrics come from two pre-built catalogs:

| Source | Catalog | Metrics are... |
|--------|---------|----------------|
| CSP Native APIs | `CSP_API_CATALOG` | Pre-defined per CSP per namespace. Namespaces map to resource types. |
| FinOps Observability | `FINOPS_INDEX_TEMPLATES` | Pre-defined per index template. Templates map to resource types. |

### Adding a New Metric (Future — Metric Onboarding)

When a new CSP metric or Observability field needs to be available:

1. **Backend team** adds the metric definition to the appropriate catalog (CSP namespace or Obs template)
2. The metric includes: name, unit, type, description, and which namespace/template it belongs to
3. Since the namespace/template is already mapped to resource types, the metric automatically appears in the wizard for the correct resource types
4. No changes needed to the wizard UI — it reads from the catalog dynamically

**Future Metric Onboarding UI** (roadmap): A form in the Integrations tab allowing platform admins to register new metrics without code changes.

### Adding a New Resource Type

1. Define the resource type: id, label, category, icon
2. Map it to CSP namespaces: `cspNamespaces: { aws: "AWS/NewService", azure: "..." }`
3. Map it to an Obs template: `obsTemplate: "new_template_id"`
4. Add suggested metrics list
5. Create the Obs index template if needed (pattern, variables, fields)

---

## 5. Execution Pipeline

### 5.1 Scheduling

| Parameter | Default | Configurable? |
|-----------|---------|---------------|
| Frequency | Daily (once per 24h) | Yes — per recommendation: daily, weekly, biweekly, monthly |
| Execution window | 02:00–06:00 UTC | System-level config |
| Timeout per recommendation run | 30 minutes | System-level config |
| Retry on failure | 3 attempts with exponential backoff | System-level config |

### 5.2 Execution Steps (Detail)

#### Step 1: Determine Scope

- Input: Active recommendation config
- The recommendation targets one CSP and one resource type
- Query the **Customer Registry** to get all customers that have the targeted CSP
- Output: List of `(customer_id, csp_account_ids[])` pairs

#### Step 2: Resource Discovery

For each customer:
- Query the CSP API or internal inventory to list resources of the target resource type
- For CSP APIs: use the `Describe*` permissions (e.g., `ec2:DescribeInstances`)
- For FinOps Obs: query the index for distinct `resource_id` values
- Collect: `resource_id`, `region`, `current_sku` (instance type), `creation_date`, `tags`
- **Minimum age check:** If `creation_date` is less than the metric window (e.g., resource created 3 days ago but metric window is 14 days) → skip this resource (insufficient history)

#### Step 3: Metric Fetch

For each resource:
- Read the recommendation's `metrics[]` config
- For each metric:
  - Determine the source field name from `cspMappings[csp]` or the Obs field name
  - Call the appropriate API:
    - **CSP API:** `GetMetricData` / equivalent with the configured time window
    - **FinOps Obs:** Elasticsearch query against the resolved index pattern
  - Result: time-series data `[(timestamp, value), ...]`
- If any required metric returns insufficient data points → skip resource, log as `insufficient_history`

#### Step 4: Rule Evaluation

For each resource with complete metric data:
- For each condition in the recommendation's `ruleGroups[]`:
  - Take the metric's time-series data
  - Apply the aggregation function (avg, max, p95, etc.) over the full window
  - Compare the aggregated value against the threshold using the specified operator
- Combine conditions within a group using inner connectors (AND/OR)
- Combine groups using outer connectors (AND/OR)
- Final result: `TRIGGERED` or `NOT_TRIGGERED`

#### Step 5: SKU Recommendation (rightsize only)

If rule triggered AND `actionType === "rightsize"`:
- Look up the resource's `current_sku` in the Product Catalog
- Find which SKU group (from Step 5 config) contains the current SKU
- Apply the group's constraints to filter candidate SKUs:
  - Direction constraint (only downsize / only upsize / both)
  - Family constraint (stay in same series)
  - Buffer: recommended SKU must have capacity >= projected utilization + buffer%
  - Max cost increase: typically 0 (no cost increase)
- From valid candidates, select the one with the **lowest cost**
- If no valid candidate → do not generate advisory for this resource

#### Step 6: Savings Calculation

| Action Type | Formula | Source |
|-------------|---------|--------|
| Shutdown | `current_sku_cost_per_hr × 720` | Product Catalog list price |
| Rightsize | `(current_cost_per_hr − recommended_cost_per_hr) × 720` | Product Catalog list price |
| Performance / Governance | N/A (shown as "—") | — |

- If `savings_30d ≤ 0` → suppress (do not create/show advisory, increment suppression counter)
- 720 hours = 30 days × 24 hours (fixed projection period)

#### Step 7: Advisory Generation / Update

For each resource where rule triggered and savings > 0:

**Lookup key:** `(recommendation_id, customer_id, resource_id)`

- **If advisory exists with this key:**
  - Update: `last_evaluated_at`, `evidence` (latest metric values), `savings_30d` (recalculated), `recommended_sku` (may change if utilization changed)
  - The `advisory_id` and `created_at` remain unchanged (same advisory, enriched data)
  - If the recommendation config was updated (new metrics, new thresholds), the updated evidence reflects the latest config

- **If no advisory exists with this key:**
  - Create new advisory with all fields (see Advisory Data Model)

- **If advisory existed previously but rule no longer triggers:**
  - Mark advisory `status = "resolved"`, set `resolved_at`
  - Resolved advisories remain queryable but are not shown to end users by default

#### Step 8: Record Run Results

After processing all customers for a recommendation:

```json
{
  "run_id": "uuid",
  "recommendation_id": "R001",
  "started_at": "2026-03-04T02:00:00Z",
  "completed_at": "2026-03-04T02:14:32Z",
  "duration_seconds": 872,
  "customers_processed": 142,
  "resources_checked": 8934,
  "advisories_created": 127,
  "advisories_updated": 2401,
  "advisories_resolved": 34,
  "suppressions": 89,
  "failures": 12,
  "failure_reasons": [
    { "type": "insufficient_history", "count": 8 },
    { "type": "metric_fetch_error", "count": 3 },
    { "type": "api_timeout", "count": 1 }
  ],
  "status": "completed"
}
```

### 5.3 Error Handling & Circuit Breaker

| Scenario | Behavior |
|----------|----------|
| Metric fetch fails for 1 resource | Skip resource, log failure, continue to next resource |
| Metric fetch fails for same resource type across a customer | Skip remaining resources of that type for this customer, try next customer |
| Same failure pattern across multiple customers simultaneously | **Circuit breaker:** stop the run, mark as `failed`, send alert to Platform Admin |
| CSP API rate limit hit | Back off with exponential delay, retry up to 3 times |
| CSP integration status = degraded/disconnected | Skip this CSP entirely, log warning |
| Execution exceeds timeout (30 min) | Terminate run, record partial results, alert admin |

**Alerting:** On circuit breaker trigger or run failure, send notification to FinOps Platform Admin via configured channel (email, Slack, etc.).

---

## 6. Advisory Data Model

### 6.1 Common Fields (all advisory types)

| Field | Type | Description |
|-------|------|-------------|
| `advisory_id` | UUID | Unique identifier, generated once, never changes |
| `recommendation_id` | FK → Recommendation | Which recommendation config generated this |
| `recommendation_name` | string | Denormalized for display |
| `customer_id` | string | Customer tenant ID |
| `resource_id` | string | Fully qualified resource identifier |
| `resource_name` | string | Human-readable name (from resource discovery) |
| `resource_type` | string | e.g., "vm", "rds", "block_disk" |
| `csp` | enum | aws / azure / gcp / oci |
| `region` | string | Cloud region |
| `subscription_id` | string | CSP subscription/account/project ID |
| `action_type` | enum | shutdown / rightsize |
| `recommendation_type` | enum | cost_saving / performance / governance |
| `category` | string | e.g., "Compute", "Storage" |
| `severity` | enum | Top / High / Medium / Low |
| `status` | enum | active / resolved |
| `created_at` | datetime | First time this advisory was generated |
| `last_evaluated_at` | datetime | Last time the pipeline processed this resource |
| `resolved_at` | datetime | Null if active; set when rule no longer triggers |

### 6.2 Shutdown Advisory

| Field | Type | Description |
|-------|------|-------------|
| `current_sku` | string | Current instance type / SKU |
| `current_cost_per_hr` | decimal | List price from Product Catalog |
| `savings_30d` | decimal | `current_cost_per_hr × 720` |
| `recommended_action` | string | "Shutdown / Deallocate" |
| `evidence` | object | Metric values that triggered the rule |
| `evidence.metrics[]` | array | `[{ name, aggregation, value, unit, window }]` |
| `evidence.rule_expression` | string | Human-readable rule that triggered |
| `evidence.evaluation_window` | string | e.g., "14 days" |

**Example:**
```json
{
  "advisory_id": "adv-001-abc",
  "recommendation_id": "R002",
  "recommendation_name": "Idle Compute Instance",
  "customer_id": "636",
  "resource_id": "i-0a3f7c8b91d2e4567",
  "resource_name": "dev-api-server-01",
  "resource_type": "vm",
  "csp": "aws",
  "region": "us-east-1",
  "subscription_id": "123456789012",
  "action_type": "shutdown",
  "recommendation_type": "cost_saving",
  "category": "Compute",
  "severity": "Top",
  "current_sku": "m5.large",
  "current_cost_per_hr": 0.096,
  "savings_30d": 69.12,
  "recommended_action": "Shutdown / Deallocate",
  "evidence": {
    "metrics": [
      { "name": "CPUUtilization", "aggregation": "avg", "value": 3.2, "unit": "%", "window": "14d" },
      { "name": "NetworkIn", "aggregation": "avg", "value": 0.4, "unit": "MB/hr", "window": "14d" },
      { "name": "NetworkOut", "aggregation": "avg", "value": 0.2, "unit": "MB/hr", "window": "14d" }
    ],
    "rule_expression": "avg(CPUUtilization) over 14d < 5% AND avg(NetworkIn) over 14d < 5 MB/hr",
    "evaluation_window": "14 days"
  },
  "status": "active",
  "created_at": "2026-02-15T02:14:00Z",
  "last_evaluated_at": "2026-03-04T02:14:32Z",
  "resolved_at": null
}
```

### 6.3 Rightsize Advisory

All fields from Shutdown, plus:

| Field | Type | Description |
|-------|------|-------------|
| `recommended_sku` | string | Target SKU from SKU group evaluation |
| `recommended_cost_per_hr` | decimal | List price of recommended SKU |
| `sku_group_id` | string | Which SKU group was used for selection |
| `recommended_action` | string | "Rightsize to {recommended_sku}" |

**Example:**
```json
{
  "advisory_id": "adv-002-def",
  "recommendation_id": "R001",
  "recommendation_name": "VM / EC2 Instance Rightsizing",
  "customer_id": "636",
  "resource_id": "i-0a3f7c8b91d2e4567",
  "resource_name": "prod-web-server-03",
  "resource_type": "vm",
  "csp": "aws",
  "region": "us-east-1",
  "subscription_id": "123456789012",
  "action_type": "rightsize",
  "recommendation_type": "cost_saving",
  "category": "Compute",
  "severity": "Top",
  "current_sku": "m5.xlarge",
  "current_cost_per_hr": 0.192,
  "recommended_sku": "m5.large",
  "recommended_cost_per_hr": 0.096,
  "savings_30d": 69.12,
  "sku_group_id": "m5_family",
  "recommended_action": "Rightsize to m5.large",
  "evidence": {
    "metrics": [
      { "name": "CPUUtilization", "aggregation": "avg", "value": 18.5, "unit": "%", "window": "14d" },
      { "name": "CPUUtilization", "aggregation": "max", "value": 42.1, "unit": "%", "window": "14d" },
      { "name": "MemoryUtilization", "aggregation": "avg", "value": 22.3, "unit": "%", "window": "14d" }
    ],
    "rule_expression": "avg(CPUUtilization) over 14d < 40% AND max(CPUUtilization) over 14d < 60%",
    "evaluation_window": "14 days"
  },
  "status": "active",
  "created_at": "2026-02-10T02:14:00Z",
  "last_evaluated_at": "2026-03-04T02:14:32Z",
  "resolved_at": null
}
```

### 6.4 Performance / Governance Advisory

| Field | Type | Description |
|-------|------|-------------|
| `savings_30d` | null | Not applicable |
| `recommended_action` | string | Descriptive action (e.g., "Add required tags", "Investigate anomaly") |

No `recommended_sku` or cost fields.

---

## 7. Suppression & Deduplication

### 7.1 Deduplication Rule

**Advisory identity key:** `(recommendation_id, customer_id, resource_id)`

- Same key = same advisory. It gets **updated** (evidence, savings, last_evaluated_at), never duplicated.
- This means an advisory created on Day 1 that still triggers on Day 30 has the same `advisory_id` and `created_at`, but fresh evidence.

### 7.2 Suppression Rules

| Rule | Condition | Behavior |
|------|-----------|----------|
| Non-positive savings | `savings_30d ≤ 0` (for cost_saving type) | Do not create advisory. Increment suppression counter in run results. |
| Insufficient metric history | Resource has fewer data points than the configured metric window requires | Skip resource. Log as `insufficient_history` failure. |
| Resource too new | `creation_date` is more recent than the metric window (e.g., resource created 3 days ago, window = 14 days) | Skip resource. This is a special case of insufficient history. |

### 7.3 What is NOT Suppressed (out of scope)

| Feature | Status |
|---------|--------|
| Dismissed advisories (user reject/snooze) | Not in current scope — all active advisories are shown to end users |
| Tag-based exclusion (e.g., "do not touch" tags) | Not available in current version |
| Maintenance windows | Not applicable per product decision |
| Minimum savings threshold on platform side | FinOps creates all advisories where savings > 0. End users can filter by minimum savings on their frontend. |

---

## 8. Priority & Conflict Resolution

### Rule

When a single resource qualifies for multiple recommendations simultaneously:

1. **Shutdown** has higher priority than **Rightsize** for the same resource
2. When a higher-priority advisory exists, lower-priority advisories for the same resource are **not generated**
3. If the higher-priority recommendation is turned off (disabled) or the resource no longer triggers it, the lower-priority advisory **should appear** in the next execution run

### Implementation

The execution pipeline maintains a per-resource tracking:

```
For each resource being evaluated:
  1. Check if a higher-priority advisory already exists
  2. If yes → skip this recommendation for this resource
  3. If no → evaluate normally
```

Priority order (highest first):
1. Shutdown / Idle
2. Rightsize
3. Other (performance, governance)

**Future enhancement:** Configurable priority management UI per resource type (roadmap).

---

## 9. Advisory Lifecycle & Update Semantics

### 9.1 Advisory Status Transitions

```
(rule triggers) → ACTIVE
                     │
                     │ (rule no longer triggers on next run)
                     ▼
                  RESOLVED
```

Only two states for advisories: `active` and `resolved`. End-user actions (acknowledge, etc.) are tracked separately in the Cost Advisory Portal and do not affect the advisory engine status.

### 9.2 Update-in-Place Semantics

When a recommendation config is updated while advisories are live:

| Change | Effect on existing advisories |
|--------|-------------------------------|
| Threshold changed (e.g., CPU < 40% → CPU < 30%) | On next run, advisory is re-evaluated with new threshold. If resource no longer triggers → resolved. If still triggers → updated with new evidence. |
| New metric added to recommendation | On next run, the new metric is fetched and added to evidence. Advisory keeps its `advisory_id`. |
| Metric removed from recommendation | On next run, removed metric is no longer in evidence. Advisory keeps its `advisory_id`. |
| Rule logic restructured | On next run, new rule logic is evaluated. Same update-or-resolve behavior. |

**Key principle:** The advisory itself is not versioned. It always reflects the **latest** recommendation config and the **latest** metric data. The recommendation config changes are tracked via the audit log.

### 9.3 No Separate Approval for Config Changes

Threshold or metric changes to an active recommendation **do not require re-approval**. Changes take effect on the next scheduled run. All changes are logged in the audit trail.

---

## 10. Operational Requirements

### 10.1 Scale Targets

| Dimension | Target |
|-----------|--------|
| Customers | 100s (up to ~500) |
| Resources per customer | 1,000s (up to ~5,000) |
| Total resources per run | ~500,000 |
| Active recommendations | ~50–80 |
| Advisories in database | ~500,000+ |
| Concurrent recommendation runs | Up to 10 |

### 10.2 Scheduling Defaults

| Frequency | Use Case |
|-----------|----------|
| Daily (default) | Most cost recommendations |
| Weekly | Less volatile metrics (e.g., storage tiering) |
| Biweekly | Low-priority governance checks |
| Monthly | Commitment/reservation analysis |

Platform admin selects frequency per recommendation. Default is daily.

### 10.3 SLAs

| Metric | Target |
|--------|--------|
| Advisory freshness | Updated within 24 hours of scheduled run |
| Pipeline completion | All active recommendations processed within 4-hour execution window |
| API availability (advisory reads) | 99.9% |
| Data retention (advisories) | 90 days active + 365 days archived |

### 10.4 Observability

| Signal | What to Monitor |
|--------|-----------------|
| Run duration per recommendation | Alert if > 2× historical average |
| Failure rate per run | Alert if > 10% of resources fail |
| Circuit breaker trips | Immediate alert to Platform Admin |
| CSP API latency | Track per-call latency; alert on degradation |
| Advisory volume anomaly | Alert if advisory count deviates > 2σ from baseline |
| Queue depth | If using job queue: alert if backlog exceeds 1 hour |

---

## 11. Audit Trail

### What is Logged

| Event | Fields Recorded |
|-------|-----------------|
| Recommendation created | `rec_id`, `created_by`, `created_at`, full config snapshot |
| Recommendation submitted for approval | `rec_id`, `submitted_by`, `submitted_at` |
| Recommendation approved | `rec_id`, `approved_by`, `approved_at` |
| Recommendation config changed | `rec_id`, `changed_by`, `changed_at`, `field_changed`, `old_value`, `new_value` |
| Recommendation disabled/enabled | `rec_id`, `changed_by`, `changed_at`, `new_status` |
| Execution run completed | `run_id`, `rec_id`, `started_at`, `completed_at`, summary stats |
| Execution run failed | `run_id`, `rec_id`, `failed_at`, `error_details` |
| Integration credential updated | `csp_id`, `changed_by`, `changed_at`, fields changed (not secret values) |
| Integration test connection | `csp_id`, `tested_by`, `tested_at`, `result` |

### Who can view

- Platform Admin: full audit log access
- Approvers: read-only for recommendations they've approved

### Retention

- Audit logs: retained for 2 years minimum
- Not deletable by any user role

---

## 12. Integration Point Specifications

### 12.1 CSP Native APIs

Fully documented in [csp-native-api.md](./csp-native-api.md). Summary:

| CSP | API | Auth | Key Operations |
|-----|-----|------|----------------|
| AWS | CloudWatch | IAM Role (STS AssumeRole) | `GetMetricData`, `ListMetrics`, `DescribeInstances` |
| Azure | Azure Monitor | Service Principal (OAuth 2.0) | `GET /metrics`, `GET /resources` |
| GCP | Cloud Monitoring | Service Account (JSON key / Workload Identity) | `timeSeries.list`, `instances.list` |
| OCI | OCI Monitoring | API Key (RSA) | `SummarizeMetricsData`, `ListInstances` |

**Configuration per CSP:**
- Credential fields (stored encrypted in Vault)
- Default region
- Rate limit awareness (built into fetch logic)
- Two-stage test connection: auth → sample metric pull for customer 636

### 12.2 FinOps Observability (Elasticsearch)

| Parameter | Value |
|-----------|-------|
| Protocol | HTTPS with mTLS (internal) |
| Endpoint | Configurable, e.g., `https://es.internal.finops.io:9200` |
| Index pattern | `finops-{customer_id}-{resource_type}-{year}.{month}` |
| Query type | Elasticsearch aggregation queries |
| Auth | Internal mTLS (auto-configured) |
| Validation | "Validate Pipeline" button resolves index for customer 636, runs sample query |

**Index resolution at execution time:**
```
Pattern: finops-{customer_id}-vm-metrics-{year}.{month}
Runtime: customer_id=636, year=2026, month=03
Result:  finops-636-vm-metrics-2026.03
```

### 12.3 Product Catalog (Billing / Pricing)

| Parameter | Description |
|-----------|-------------|
| Purpose | Provides list prices per SKU per CSP per region |
| Used for | Savings calculation in the execution pipeline |
| Data model | SKU → cost_per_hr, vcpu, memory, generation, family |
| Currently modeled | `SKU_CATALOG` constant (AWS, Azure, GCP, OCI families) |
| Production | Would be a database/API with regularly updated pricing from CSP price sheets |
| Update frequency | Daily (CSPs update prices periodically) |

### 12.4 Customer Registry

| Parameter | Description |
|-----------|-------------|
| Purpose | Maps customer_id → CSP accounts/subscriptions/projects |
| Used for | Scoping which customers to process per recommendation |
| Required fields | `customer_id`, `customer_name`, `csp`, `account_id`, `region_list` |
| Not yet defined | This is a prerequisite data source that needs to be specified |

### 12.5 Resource Inventory

| Parameter | Description |
|-----------|-------------|
| Purpose | Lists resources per customer per resource type |
| Used for | Resource discovery step in execution pipeline |
| Source option A | Query CSP APIs directly (ec2:DescribeInstances, etc.) |
| Source option B | Internal CMDB / asset inventory database |
| Required fields | `resource_id`, `resource_name`, `region`, `current_sku`, `creation_date`, `tags` |
| Decision needed | Which source is primary? How often is inventory refreshed? |

---

## 13. End-User Advisory Experience

The end-user Cost Advisory Portal has an existing mock at:
`web/CXP Optimization/Cost Recommendations/`

### Current Mock Structure (3-layer drill-down)

**Layer 1: Dashboard**
- KPI cards: Monthly Potential Savings, Total Recommendations, Impacted Resources
- Stacked chart by recommendation category
- Table: category → savings → impacted resources → impact level

**Layer 2: Recommendation Detail**
- Per-asset table with: CSP, subscription, asset ID, resource, advisory text, savings, status
- Templates vary by use case: rightsizing, idle, scheduler, generic

**Layer 3: Utilization / Evidence**
- Per-asset metric charts (CPU, memory, etc.) over the evaluation window
- Predicted, average, peak values
- Configurable interval (hourly / 15 min)

### Actions Available to End Users

| Action | Current State |
|--------|---------------|
| View advisory list | Mock implemented |
| Drill into evidence/utilization | Mock implemented |
| Acknowledge advisory | Mock placeholder (`alert`) |
| Filter by savings threshold | Not wired but input exists |
| Search advisories | Input exists, not wired |
| Export / download | Mock placeholder |

### Relationship to Execution Pipeline

The Cost Advisory Portal **consumes** the advisory records generated by the execution pipeline. It does not interact with recommendation configs.

```
Execution Pipeline → Advisory Database → Cost Advisory Portal (read)
```

---

## 14. Open Items & Future Roadmap

### Open Items (need decisions before dev)

| Item | Question | Impact |
|------|----------|--------|
| Customer Registry source | Where is the master customer-to-CSP-account mapping? Existing system or new table? | Scoping logic |
| Resource Inventory source | Pull from CSP APIs at runtime or from internal CMDB? | Performance, freshness |
| Advisory API | REST API design for Cost Advisory Portal to consume advisories | Frontend-backend contract |
| Multi-CSP per recommendation | Currently one CSP per rec. Should we support multi-CSP with per-CSP field mapping in v1? | Wizard UX, execution logic |
| Notification channels | Which channels for platform admin alerts? Email, Slack, Teams? | Alerting implementation |

### Future Roadmap

| Feature | Description |
|---------|-------------|
| Metric Onboarding UI | Self-service form for platform admins to register new metrics |
| Priority Management UI | Configure priority order by resource type and recommendation type |
| Multi-CSP recommendations | One recommendation targeting multiple CSPs with per-CSP metric field mapping |
| Dismissed advisory tracking | End-user reject/snooze with cooldown period |
| Savings validation | Post-implementation cost comparison (did the customer actually save?) |
| Custom aggregation functions | User-defined `f(ts) → scalar` functions for complex evaluations |
| Schedule builder | Visual cron picker for recommendation execution frequency |
| Version history | Recommendation config versioning with diff view and rollback |
| End-user minimum savings filter | Backend-enforced per-customer savings threshold |
