# FinOps Recommendation Engine — Product Design

**Version:** 3.0  
**Last updated:** 2026-03-04  
**Status:** Requirements confirmed — ready for development handoff  
**Companion doc:** [requirements-v3.md](./requirements-v3.md) — detailed execution pipeline, data models, and integration specs

---

## 1. Persona and Scope

| Attribute | Value |
|-----------|-------|
| **Primary User** | Platform Admin / FinOps Engineering team |
| **Tool Type** | Internal Configuration Console — not visible to end customers |
| **Purpose** | Configure, validate, and manage cost and performance advisories that are later surfaced to end users via a separate customer-facing portal |

End users (cloud customers) do **not** use this console. They see advisories in a future portal that reuses the same advisory engine but with a separate UI layer.

---

## 2. Navigation Structure

| Nav Item | ID | Purpose |
|----------|----|---------|
| Dashboard | `dashboard` | High-level health metrics and stats |
| Recommendations | `recommendations` | Browse, create, and manage recommendation configs |
| Production Monitor | `advisories` | Aggregated platform health — advisory volumes, hit rates, suppression |
| Connection Health | `data_sources` | Read-only status of all configured data sources |
| Aggregation Engine | `aggregations` | Test and inspect aggregation functions |
| Failure Analysis | `failures` | Review failed advisory evaluations |
| Product Catalog | `catalog` | SKU price list used for savings calculations |
| Integrations | `integrations` | **Only** place for active configuration of CSP and Observability connections |

> **Rule:** The Integrations tab is the single configuration surface. Connection Health is read-only monitoring.

---

## 3. Action Types

A **Recommendation Action Type** is the primary classification that drives:
- Which wizard steps are shown (Step 5 — SKU Mapping is conditional)
- How savings are calculated
- What the advisory tells the end user to do

| Action Type | ID | Description | Savings Formula |
|------------|-----|-------------|-----------------|
| Shutdown / Idle | `shutdown` | Resource has no meaningful activity — shut it down | `current_sku_cost_per_hr × 720 hrs` |
| Rightsize | `rightsize` | Resource is over-provisioned — move to a smaller SKU | `(current_sku_cost_per_hr − recommended_sku_cost_per_hr) × 720 hrs` |

> **Savings policy:** All costs are sourced from the **Product Catalog** at **list price**. Advisories where computed savings ≤ 0 are **automatically suppressed** and counted separately. Only positive-savings advisories are surfaced to end users.
>
> **Performance/governance recommendations** (type ≠ `cost_saving`) show "—" as savings.

---

## 4. Recommendation Lifecycle States

```
Draft → (submit for approval) → Pending Approval → (approver clicks Approve) → Approved
                                                                                    │
                                                               ┌────────────────────┤
                                                               │                    │
                                                           Run Now            Simulate Now
                                                    (live, customer 636)    (mock data, editable)
```

| Status | Label | Who sets it |
|--------|-------|-------------|
| `draft` | DRAFT | Default when created |
| `pending_approval` | PENDING APPROVAL | System on "Submit for Approval" |
| `approved` | APPROVED | Approver via Approval tab in Detail Panel |
| `active` | ACTIVE | System after first successful execution run |
| `disabled` | DISABLED | Platform admin manually |

**Approval record:** The `approvedBy` (identity/email) and `approvedAt` (timestamp) are recorded immutably when an approver clicks Approve.

**Submission record:** `submittedBy` and `submittedAt` are recorded when the wizard is submitted.

---

## 5. Create Recommendation Wizard

### Step progression (dynamic)

| Action Type | Steps shown | Total |
|-------------|-------------|-------|
| Shutdown / Idle | 1 → 2 → 3 → 4 → (skip 5) → 6 | 5 |
| Rightsize | 1 → 2 → 3 → 4 → 5 → 6 | 6 |

### Step summary

| Step | Title | Key decisions |
|------|-------|---------------|
| 1 | Basic Info + Action Type | Sets `actionType` (shutdown/rightsize), name, description, type, category |
| 2 | Cloud Provider | **Single-select** — one CSP per recommendation. Create separate recommendations for other CSPs. |
| 3 | Resource Type & Metrics | Select data source (selected CSP or FinOps Obs — one at a time), pick metrics, configure historical window only. Aggregation is NOT set here — same metric can be evaluated with different aggregations in Step 4. |
| 4 | Rule Logic & Triggers | Structured rule builder with AND/OR groups; per-condition: metric, aggregation function, operator, threshold + unit selector (default %). Warns if a Step 3 metric is not referenced in any condition. |
| 5 | SKU Mapping (rightsize only) | Platform-only; defines SKU groups with constraints for alternative suggestions |
| 6 | Savings & Benefits | Auto-calculated savings display (read-only formula, sourced from Product Catalog) + benefit description |

---

## 6. CSP & Metric Architecture

### Current: Single-CSP per recommendation

Each recommendation targets **one CSP**. To cover the same logic across AWS, Azure, GCP, and OCI, the platform team creates separate recommendations per CSP. Each recommendation configures:
- The specific CSP's metric field names
- Rules using those field names
- SKU groups from that CSP's catalog

### Metric Field Name Mapping

The same metric concept (e.g. "CPU Utilization") has different field names per CSP:

| CSP | Field Name |
|-----|-----------|
| AWS (CloudWatch) | `CPUUtilization` |
| Azure (Monitor) | `Percentage CPU` |
| GCP (Cloud Monitoring) | `cpu/utilization` |
| OCI (Monitoring) | `CpuUtilization` |

In the wizard (Step 3), each selected metric has an expandable **field mapping** section. Field names are **auto-suggested from the catalog** and are **user-editable**. The rule builder (Step 4) uses the selected metric name — the engine uses the configured field name at runtime.

### Future Enhancement: Multi-CSP per recommendation

Multi-CSP support (one recommendation targeting multiple CSPs with per-CSP field mapping) is a future enhancement. If rule logic changes, it would need to be applied across all CSPs within the same recommendation.

---

## 7. Savings Model

### Source of Truth
All savings calculations use the **Product Catalog** (list prices). No customer-specific pricing or committed-rate discounts are applied. This is by design — the goal is to show consistent, comparable savings across all customers.

### Formula by Action Type

**Shutdown:**
```
savings_30d = current_sku_cost_per_hr × 720
```

**Rightsize:**
```
savings_30d = (current_sku_cost_per_hr − recommended_sku_cost_per_hr) × 720
```

**Performance / Governance:**
```
savings_30d = N/A  (shown as "—")
```

### Suppression rule
If `savings_30d ≤ 0` for a resource evaluation, the advisory is **suppressed** (not created). The suppression count is tracked separately and visible in the Production Monitor.

### Projection period
All savings are projected over **30 days (720 hours)**. This is fixed and not user-configurable.

---

## 8. Simulate Now and Run Now

Both actions are available on **approved** recommendations from the Approval tab.

### Run Now
- Executes the recommendation rule against **demo customer 636** using real integration data.
- Shows a summary: resources checked, advisories generated, savings estimates.
- Results are transient (not persisted to the recommendation store).

### Simulate Now
- Opens `SimulateModal` with an **editable mock dataset** pre-populated from `MOCK_DATA_TEMPLATES`.
- Mock data structure: `{ resourceId, currentSku, metrics: { fieldName: value } }`.
- Users can **export JSON**, edit externally, and **import JSON** back to the modal.
- Clicking **Run Simulation** applies the rule logic against the mock data, computes savings from the Product Catalog, and shows which resources would receive an advisory.
- Mock cost resolution: `cost_per_hr` is looked up from `SKU_CATALOG` by `currentSku`.

### Mock Data Template Schema
```json
{
  "resourceId": "string",
  "region": "string",
  "currentSku": "string (must exist in SKU_CATALOG for savings calculation)",
  "metrics": {
    "<fieldName>": "<numeric value>"
  }
}
```

---

## 9. Production Monitor

The **Production Monitor** view is an internal health dashboard for the platform team. It replaces the old "Customer Advisories" view which showed per-customer details (those belong in the future end-user portal).

### Summary Cards
- Total Advisories (MTD)
- Advisories Today (estimated)
- Suppressed (savings ≤ 0)
- Execution Failures (MTD)
- Last successful run timestamp

### Advisory Breakdown Table
Per recommendation row: ID, name, type, CSPs, resources checked, advisories generated, suppressed, failures, hit rate %, last run date, 7-day sparkline trend.

### Suppression policy note
Prominently displayed: suppressed advisories are counted separately and never appear in customer-facing advisory lists.

---

## 10. Integration Testing Flow

### CSP Native APIs — Two-Stage Test Connection
See [csp-native-api.md](./csp-native-api.md) for full details.

1. **Stage 1 — Auth:** Validates credentials against the CSP auth endpoint.
2. **Stage 2 — Data pull:** Pulls a sample metric for demo customer 636 to confirm end-to-end pipeline.

### FinOps Observability — Validate Pipeline
1. Resolves the configured index pattern template with `customer_id = 636`.
2. Issues a sample Elasticsearch query.
3. Returns: resolved index name, document count, sample field/value, query latency.

---

## 11. SKU Mapping (Step 5 — Rightsize Only)

SKU groups define which alternative SKUs can be suggested for a resource. Platform configuration only — end users see only the final recommendation.

### Constraints per SKU group
- **Direction:** Only downsizing allowed (enforces savings > 0) / bidirectional
- **Max size delta:** Maximum allowed CPU/memory ratio change
- **Buffer %:** Headroom above projected utilization the recommended SKU must accommodate
- **Max cost increase:** Hard cap on recommended SKU cost (typically 0 — no cost increase allowed)
- **Stay in family:** Constraint to stay within the same instance series/family (e.g. AWS `m6i` series only)

### CSP-specific notes
- **AWS:** Stay within the same instance family series by default (e.g. `m6i` → `m6i.large`). Cross-family moves require architectural justification.
- **Azure:** Stay within the same VM series (e.g. `Standard_D` series) unless explicitly overridden.
- **GCP:** Prefer same machine family (e.g. `n2-standard` → `n2-standard-2`). Cross-family to E2 or T2A allowed for ARM workloads.
- **OCI:** Stay within same shape category (e.g. `VM.Standard.E4.Flex`). OCI Flex shapes allow vCPU/RAM adjustment within the same shape.

---

## 12. Recommendation Priority Management

A single resource may qualify for both "Idle Compute" (shutdown) and "Rightsizing" recommendations simultaneously. The priority model:

- **Shutdown** has higher priority than **Rightsize** for the same resource.
- When both apply, only the higher-priority advisory is surfaced (no duplicate advisories for the same resource).
- If the higher-priority recommendation is **disabled or the resource no longer triggers it**, the lower-priority advisory **should appear** on the next execution run.
- A future **Priority Management UI** will allow platform teams to configure priority order by resource type and advisory type per environment.

---

## 13. Data Sources

### Metric Sources

| Source | Type | How Connected |
|--------|------|---------------|
| CSP Native APIs (AWS CloudWatch, Azure Monitor, GCP Cloud Monitoring, OCI Monitoring) | Pull-based REST | Credentials configured in Integrations tab |
| FinOps Observability (Elasticsearch) | Internal pull | Internal mTLS — auto-configured; endpoint editable in Integrations tab |
| Billing API | Internal | Provides product catalog list prices; separate from metric data |

### Index Naming Convention (FinOps Observability)
```
finops-{customer_id}-{resource_type}-{year}.{month}
```
Example: `finops-636-vm-metrics-2026.03`

Runtime variables (`{customer_id}`, `{year}`, `{month}`) are substituted at execution time.

---

## 14. Advisory Deduplication & Update Semantics

### Identity key

`(recommendation_id, customer_id, resource_id)` — this tuple uniquely identifies an advisory.

### Behavior

- **Same advisory, new data:** Advisory created on Day 1 that still triggers on Day 30 keeps the same `advisory_id`. Only evidence, savings, and `last_evaluated_at` are refreshed.
- **Config changes (new metrics, new thresholds):** Next run evaluates with the updated config. Advisory is enriched with updated evidence — not replaced.
- **Rule no longer triggers:** Advisory status changes to `resolved` with a `resolved_at` timestamp.
- **No versioning on advisories:** The advisory always reflects the latest recommendation config and latest metric data.

### Suppression rules

| Rule | Behavior |
|------|----------|
| Savings ≤ 0 | Suppressed — not created. Counted separately in Production Monitor. |
| Insufficient metric history | Resource skipped — logged as failure reason. |
| Resource too new | Treated as insufficient history (creation date < metric window). |
| End-user dismissal | Not in current scope. All active advisories are shown to end users. |
| Tag-based exclusion | Not available in current version. |
| Minimum savings threshold | Created on platform side for all savings > 0. End users filter on their frontend. |

---

## 15. Recommendation Config Change Management

| Change Type | Re-approval needed? | Effect |
|-------------|---------------------|--------|
| Threshold adjustment | No | Applied on next scheduled run |
| New metric added | No | Fetched on next run; evidence enriched |
| Metric removed | No | Removed from evidence on next run |
| Rule logic restructured | No | New logic evaluated on next run |
| Action type changed | Yes (create new recommendation) | Fundamental change — should be a new recommendation |

All changes are logged in the **audit trail** with: who changed, when, what field, old value, new value.

---

## 16. Execution Schedule

| Default | Daily |
|---------|-------|
| Configurable per recommendation | daily, weekly, biweekly, monthly |
| Decision pending | Some advisories may need less-frequent evaluation |

---

## 17. Error Handling (Execution Pipeline)

| Scenario | Behavior |
|----------|----------|
| Metric fetch fails for 1 resource | Skip resource, try next |
| Same failure across a resource type for a customer | Skip remaining resources of that type, try next customer |
| Same failure across multiple customers | **Circuit breaker:** stop run, alert Platform Admin |
| CSP API rate limit | Exponential backoff, retry 3x |
| Run exceeds timeout | Terminate, save partial results, alert |

---

## 18. Audit Trail

Logged events: recommendation create/edit/approve/disable, execution runs (success/failure), integration credential changes, test connections. Each event records: user identity, timestamp, details. Retained for 2 years minimum. Not deletable.
