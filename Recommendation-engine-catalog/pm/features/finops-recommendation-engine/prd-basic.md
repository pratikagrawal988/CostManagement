# PRD — FinOps Recommendation Engine (Basic Tier)

## Document Control

| Field | Value |
|---|---|
| **PRD Title** | FinOps Recommendation Engine — Basic Tier |
| **Platform** | FinOps |
| **Product** | FinOps |
| **Sub-Module** | Cost Advisory |
| **Author(s)** | Pratik |
| **Reviewer(s)** | Platform Eng Lead, FinOps PM, Security Lead (TBD) |
| **Status** | Ready for Engineering Review |
| **Version** | 1.1 |
| **Created** | 2026-04-20 |
| **Last Updated** | 2026-04-29 |
| **Linked ADO Items** | Pending — to be created post review |
| **Companion docs** | `basic-requirements-critical-review.md`, `basic-recommendation-catalog.md`, `basic-recommendation-catalog-global.csv`, `basic-costvars-advisory-mapping.md`, `basic-integration-framework-guide.md`, `basic-product-catalog-coverage.md`, `basic-product-compatibility-groups.md`, `basic-ui-flow-simulation-review.md`, `basic-system-user-guide.md`, `basic-project-map-roadmap.md`, `docs/architecture/finops-recommendation-engine.md` |

---

## Table of Contents

1. [Problem](#1-problem)
2. [Vision](#2-vision)
3. [Objectives](#3-objectives)
4. [Scope](#4-scope)
5. [User Personas & Access](#5-user-personas--access)
6. [Feature Requirements](#6-feature-requirements)
7. [Data Requirements](#7-data-requirements)
8. [UI/UX Design](#8-uiux-design)
9. [Acceptance Criteria](#10-acceptance-criteria)
10. [Non-Functional Requirements](#11-non-functional-requirements)
11. [Dependencies & Risks](#12-dependencies--risks)
12. [Rollout & Migration Plan](#13-rollout--migration-plan)
13. [Open Questions](#14-open-questions)
14. [Appendix](#15-appendix)

---

## 1. Problem

The current `FinOps Recommendation Engine` SPA (at `web/CXP Optimization/FinOps Recommendation Engine/`) is a polished authoring UI for metric-threshold rules, but the rules it authors are not actually evaluated, the savings it shows are author-typed strings, integrations beyond CSPs are display-only, the approver field is free text, and there is no reconciliation against billing to prove realized savings. Customers who shipped advisories through this UI cannot answer the CFO's first question — *"how much did we actually save?"* — because nothing closes the loop.

Concretely, today's gaps that are achievable inside a **rule-based** engine (not requiring APM, traces, ML classifiers, or product analytics — those belong to the Advanced tier):

1. **Authored rules don't execute.** `Submit` builds a `ruleGroups` object that no backend reads. `Run Now` is a UI flag toggle. `Simulate Now` uses hard-coded heuristics that ignore the authored rule.
2. **No persistence.** New advisories are not saved beyond the open browser session.
3. **No backtest.** A new rule cannot be dry-run against historical data before it ships.
4. **Savings are author-typed strings.** No live pricing lookup; no confidence band; no tracking.
5. **Approver is a free-text input.** No RBAC. No SSO group mapping.
6. **Audit log is static**. Hard-coded rows; no real event capture.
7. **Single CSP per advisory.** Multi-cloud rules (e.g., orphaned resources across AWS + Azure) cannot be authored, even though the rule logic is identical.
8. **No realized-savings reconciliation.** Once an advisory fires, there is no path to verify the saving actually landed in the bill.
9. **Rule builder cannot reference custom-function output.** The glossary lists `custom_fn` as an aggregation, but the rule builder UI cannot select it.

Each of these gaps is **rule-based-achievable** — they don't require the new Advanced engine. They are within scope of Basic.

---

## 2. Vision

FinOps Basic is the **dependable, deterministic, auditable rule-based recommender** that every FinOps customer gets on day one. It evaluates authored rules over CSP metrics, billing, K8s, and FinOps Observability; it shows you what your authored rule will hit before you publish it; it prices the savings against the live catalog with a confidence band; it routes approvals through RBAC; and it tells you 30/60/90 days later whether the saving actually landed.

It is the **floor of the product**. The Advanced tier sits on top of the same data model, the same Provider Registry, the same Reconciler — Basic and Advanced share a backbone (see `docs/architecture/finops-recommendation-engine.md` §2).

---

## 3. Objectives

- O1. **Make authored rules real.** A submitted Hypothesis is persisted, backtested, and evaluated by the Basic Evaluator end-to-end. Demonstrable as: author a rule in the UI → see N findings against your real history → publish → next evaluation cycle emits the same N findings as live findings.
- O2. **Close the trust loop on savings.** Every Action that gets approved and applied has its realized savings reconciled against billing at T+30 / T+60 / T+90 and surfaced on the Hypothesis page.
- O3. **Replace approver text input with RBAC.** All approvals routed through SSO groups; audit log becomes an immutable event log.
- O4. **Allow multi-CSP and multi-account scope.** Authors can select one or more CSPs, accounts, environments, and BU/cost-centre selectors in scope.
- O5. **Live-priced savings.** Savings on every Hypothesis are computed by the Product Catalog from live CSP pricing, not typed by the author.
- O6. **Make integrations declarative.** Onboarding is rendered from a Provider Registry manifest; FinOps team can add a new CSP-style integration by writing a manifest, not a release.
- O7. **Extend rule builder to reference custom-function outputs.** Closes the parity gap between glossary and what the builder can express.

Out of scope of Basic (deliberately — these are Advanced):
- APM / trace / log signal sources when the recommendation requires request-level attribution or multi-signal joins
- Workload fingerprint classifiers
- Cross-signal joins (billing × APM, billing × LLM usage, etc.)
- Anomaly / seasonality / peer-comparison statistical operators
- Typed action vocabulary beyond the Basic 6 (see Advanced PRD §6)

In scope for Basic as of v1.1:
- CSP-native advisor recommendations imported as normalized FinOps Findings.
- Rule-based AI cost recommendations when based on aggregate provider/SaaS usage metrics, LLM gateway metrics, billing exports, GPU/DCGM metrics, model-registry metrics, experiment-tracker metrics, or vector DB metrics.
- Third-party SaaS recommendations where the SaaS exposes deterministic metric/recommendation exports.

---

## 4. Scope

### 4.1 In Scope

**Engine and data flow**
- Persistence of `Hypothesis` entities (per architecture §2.1) backed by an Advisory API.
- Basic Evaluator service that compiles `Hypothesis.conditions` into a query plan and executes against Signal Catalog.
- Backtest-on-publish: every transition `draft → shadow` and `shadow → active` runs an evaluator replay against ≥30 days of history.
- Realized-savings Reconciler hitting CUR / Azure Cost Export / GCP BQ billing at T+30 / T+60 / T+90 and writing `Outcome` events.
- Multi-CSP, multi-account, multi-BU scope on Hypotheses.

**UI changes (existing SPA)**
- Wizard Step 1: required-field validation, owner field, business justification field.
- Wizard Step 2: multi-select CSPs (today: single).
- Wizard Step 3: source picker reads Provider Registry; CSP + Obs remain default.
- Wizard Step 4: rule builder gains custom-function-output reference, plus a live `Backtest preview` panel.
- Wizard Step 5: SKU mapping integrated with Product Catalog; target rate is fetched live.
- Wizard Step 6: savings auto-computed (point + lower + upper) from Product Catalog; confidence band shown.
- New tab on the Recommendation detail panel: `Realized savings` (T+30 / T+60 / T+90 reconciliation).
- New tab on the Recommendation detail panel: `Audit log` (event log projection).
- Approver field becomes an SSO group picker (mocked in Basic SPA; backed by Identity provider in production).
- Integrations tab: rendered generically from Provider Registry; CSP and Obs are pre-loaded entries.

**Data model and services (per architecture doc)**
- Advisory Service (CRUD over Hypothesis; event log for Finding, Action, Outcome)
- Provider Registry (manifest-rendered onboarding, health probe, catalog binding)
- Signal Catalog (canonical signals from CSP metrics, billing, K8s, Obs)
- Product Catalog (live CSP pricing)
- Reconciler

### 4.2 Out of Scope (this release)

- Anything that requires APM trace/log-level attribution, SQL/query-plan analysis, workload fingerprint classifiers, or probabilistic signal fusion → Advanced PRD.
- Aggregate AI usage and GPU telemetry are in scope when they are available as deterministic metrics from provider usage APIs, LLM gateways, GPU exporters, model registries, vector DB APIs, billing exports, or third-party SaaS providers.
- Custom Function Runtime as a sandboxed compute service → Advanced PRD (Basic only allows the wizard to *reference* custom-function outputs that already exist in the Signal Catalog; it cannot author new ones).
- Typed actions beyond the 6 in §6.4.
- Auto-apply mode. Basic delivers Actions through ITSM ticket or manual apply only; auto-apply is gated to Advanced + policy-as-code.
- IaC PR generation. Basic delivers Actions as ITSM tickets only; Advanced adds the IaC PR channel.
- Carbon-aware optimisation, query-cost optimisation, unit economics, and portfolio-level commitment orchestration → Advanced PRD. Basic may still import simple CSP-native commitment/reservation opportunities as `CommitmentReview` Findings for human approval.

---

## 5. User Personas & Access

### 5.1 Personas applicable to this feature

| Persona | Applicable | Feature-Specific Access / Actions |
|---|---|---|
| FinOps Admin | Yes | Full authoring across all tenants and scopes; approve any Hypothesis or Action; manage Provider Registry; override Product Catalog rates |
| FinOps Executive | Yes | Read-only view of Findings + Outcomes; subscribes to weekly realized-savings digest |
| FinOps CC Admin | Yes | Author Hypotheses scoped to assigned cost centres; approve Findings on owned resources |
| FinOps Owner | Yes | Approve Findings on owned projects; cannot author Hypotheses (unless granted `finops.author` add-on role) |
| FinOps User | Yes | Read-only view of Findings on accessible scopes |

### 5.2 Engineering personas (FinOps internal, not customer)

| Persona | Access |
|---|---|
| FinOps Platform Engineer | Manages Provider Registry manifests and Catalog refresh schedules |
| FinOps PM | Authors first-party Hypotheses (the "out of the box" set shipped with Basic) |
| FinOps Support | Read-only on event logs and audit; can suppress a Finding on customer request with reason code |

---

## 6. Feature Requirements

### 6.1 Hypothesis authoring (wizard upgrades)

#### 6.1.1 Step 1 — Basic info
- Required fields enforced before `Next`: `name`, `description`, `category`, `severity`, `owner`, `business_justification`.
- `owner` is an SSO group picker (resolved from Identity provider; mocked list in Basic SPA).
- `business_justification` is a free-text field with a 500-character minimum.
- Optional: `documentation_link` (URL to runbook / wiki).

#### 6.1.2 Step 2 — Scope (was "CSP & classification")
- CSP selector becomes multi-select. At least one required.
- Account selector multi-select per CSP. Defaults to all accounts in tenant.
- Environment selector: `prod | non-prod | all`.
- BU / Cost Centre selector via Tag Lens hierarchy.
- Tag selector: arbitrary `tag.key = value` pairs (AND-combined within row, OR across rows).

#### 6.1.3 Step 3 — Resource type & signals
- Source picker rendered from Provider Registry (`provider.category in {csp, billing, k8s, observability}` for Basic).
- Signal picker pulls from Signal Catalog filtered to the selected resource type's bindings.
- "Suggested signals" carries forward from current SPA's `RESOURCE_TYPES` table; now backed by catalog metadata.
- Custom-function output references appear in the dropdown when the Hypothesis is referencing a published CF (e.g., `cf://duty_cycle_v3.scalar.duty_pct`).

#### 6.1.4 Step 4 — Rule logic & triggers
- Rule builder unchanged in shape (AND / OR groups), upgraded:
  - Operator set extended: `< > <= >= == != BETWEEN IN NOT_IN EXISTS IS_NULL`.
  - Aggregation set: `avg | min | max | p50 | p90 | p95 | p99 | sum | count | stddev | rate | first | last`. (No `anomaly`, `seasonality`, `peer_compare` — those are Advanced.)
  - Window: `now-1h | now-6h | now-24h | now-7d | now-14d | now-30d | now-90d | custom`.
  - Each clause now has an explicit `evidence_required: true | false` flag — when true, a failing clause is still recorded as evidence on the Finding for the resource owner to inspect.
- `Backtest preview` panel: live counts of how many resources will hit this rule against the last 30 days of Signal Catalog data, refreshed on debounce.
- The actual `ruleGroups` object is what the Basic Evaluator runs at publish — not heuristics.

#### 6.1.5 Step 5 — SKU mapping (rightsize / tier-move actions only)
- Source SKUs and target SKUs auto-resolved from Product Catalog given selected resource_type and CSP set. Author can override.
- Constraint fields unchanged: direction, max step, headroom %, reservation respect, region constraint.
- Live target-rate display: as the author selects a target SKU, the projected rate from Product Catalog appears next to it.

#### 6.1.6 Step 6 — Savings & benefits
- Savings are no longer typed in. UI shows:
  - **Estimated savings (point)**: from Product Catalog `rate_delta(current_rate, target_rate, hours_in_window)`.
  - **Confidence band (lower / upper)**: from `confidence_band(current, target, historical_sku_usage)`.
  - **Basis**: `retail` (default) or `chargeback` (if Chargeback module is configured for tenant).
- Explanatory text auto-generated from the rule + savings model. Author can append a free-text narrative.

### 6.2 Hypothesis lifecycle

- States: `draft → shadow → active → deprecated`.
- Promotion gates:
  - `draft → shadow`: backtest must complete with ≥ 90% data coverage and produce ≥ 1 Finding (otherwise the rule is functionally dead). Author can override with justification.
  - `shadow → active`: minimum 7 days in shadow + zero P0 false-positive incidents reported on Findings.
  - `active → deprecated`: explicit author action with reason code; existing Findings transition to `expired`.
- Versioning: every save increments `version`. Findings are bound to `(hypothesis_id, version)` so an evolving rule does not retroactively rewrite history.

### 6.3 Finding lifecycle

- States: `new → snoozed | approved | dismissed`. `approved → applied → reconciled | regressed | rolled_back`.
- Snooze with reason code (`investigating`, `change_window_pending`, `dependency_blocked`) and snooze-until date.
- Dismissal requires reason code (`not_applicable`, `incorrect_finding`, `policy_exception`, `already_addressed`, `customer_decision`). Dismissals feed the author's Hypothesis quality dashboard.
- Auto-expire after 30 days if no transition; emit `expired` event.

### 6.4 Action vocabulary (Basic)

Twelve typed actions allowed in Basic:

1. `Shutdown` — terminate idle resource (delete or stop)
2. `RightsizeSku` — move to smaller / larger SKU
3. `SchedulePause` — apply on/off cron schedule for non-prod
4. `TierMove` — storage tier migration (S3 IA, GCS Coldline, Azure Cool)
5. `DeleteOrphan` — unattached snapshots / AMIs / EIPs / LBs
6. `VolumeTypeSwap` — gp2→gp3, Premium→Balanced SSD, etc.
7. `CommitmentReview` — import simple CSP-native RI / SP / CUD / reservation coverage and underutilization recommendations for human approval (Basic does not optimize the portfolio mix)
8. `TagFix` — required tag / invalid cost-centre tag remediation
9. `BudgetReview` — forecasted budget breach review
10. `ModelRoute` — rule-based AI model routing / token-cost recommendation where only aggregate LLM usage metrics are used
11. `SpotReview` — obvious tag/checkpoint-based spot/preemptible candidate review
12. `LicenseReview` — license-included / BYOL opportunity review sourced from CSP or license SaaS data

Delivery channels for Basic:
- `manual` — Action recorded as a recommendation; owner applies via CSP console; Reconciler still tracks
- `itsm_ticket` — auto-creates ServiceNow / Jira ticket assigned to owner

`auto_apply` and `iac_pr` channels are deferred to Advanced. New review-oriented Basic actions (`CommitmentReview`, `SpotReview`, `LicenseReview`, `ModelRoute`) always require human approval and are delivered as manual or ITSM actions.

### 6.5 Approval workflow

- When a Finding requires action, the system resolves the approver:
  1. If Hypothesis carries explicit `approver_group`, use that.
  2. Else, use `finops.approver` group scoped by the resource's BU / cost centre.
  3. Else, fall back to `finops.admin` global.
- Approval is delivered through Slack / MS Teams (if integrated) and via email digest.
- Approval decision is captured in the event log with `actor, decision, comment, timestamp`.
- Approver field on the Hypothesis is **always a group reference**, never free text.

### 6.6 Realized-savings reconciliation

- Reconciler runs on schedule per tenant (default: every 6 hours). For each `Action.applied` event, schedules T+30 / T+60 / T+90 jobs.
- At each window:
  - Pulls billing cost series for `[applied_at − baseline_window, applied_at + observation_window]`.
  - Normalises against usage baseline (e.g., shutdown saving = baseline_cost − current_cost; rightsize saving = baseline_rate × hours − current_rate × hours).
  - Writes `Outcome { realized_savings, variance_pct_vs_estimate, status }` to the event log.
- The Hypothesis detail page shows aggregate realized savings rolled up across all Findings the rule has generated.
- The author dashboard shows per-Hypothesis variance — when realized < 0.5 × estimated for ≥ 5 Findings, the rule is flagged for review.

### 6.7 Audit log

- Every entity transition (Hypothesis state, Finding state, Action state, Provider Registry change, Product Catalog override) writes an immutable audit event.
- Audit row fields: `actor (sso_user, sso_groups), entity_type, entity_id, before, after, ip, ua, request_id, timestamp`.
- Audit log on the SPA is a projection of the event log filtered to the current entity, sortable by timestamp, exportable as CSV.

### 6.8 Provider Registry — Basic-tier providers

The following providers are first-party in Basic and ship with Provider Registry manifests on day one:

| Provider | Category | Auth method | Onboarding parameters (minimum) |
|---|---|---|---|
| AWS | csp | IAM cross-account role | `account_id`, `role_arn`, `external_id`, `region_allowlist`, `read_only_policy_arn` |
| Azure | csp | Service Principal | `tenant_id`, `subscription_ids[]`, `client_id`, `client_secret`, `mgmt_group_scope` |
| GCP | csp | Service Account key OR Workload Identity Federation | `project_ids[]`, `sa_email`, `key_or_wif_provider`, `org_id`, `folder_ids[]` |
| OCI | csp | API signing key | `tenancy_ocid`, `user_ocid`, `region`, `compartment_ids[]`, `fingerprint`, `private_key` |
| AWS CUR | billing | IAM role + S3 bucket | `role_arn`, `external_id`, `bucket_name`, `report_prefix`, `report_format`, `crawler_schedule` |
| Azure Cost Export | billing | SPN + Storage access | `tenant_id`, `client_id`, `client_secret`, `billing_account_id`, `export_storage_account`, `export_container`, `export_scope` |
| GCP Billing BQ Export | billing | Service Account / WIF | `project_id`, `dataset_id`, `table_suffix`, `sa_email`, `key_or_wif_provider`, `dataset_location` |
| OCI Usage Report | billing | API key + Object Storage | `tenancy_ocid`, `bucket_namespace`, `bucket_name`, `prefix`, `usage_type` |
| Kubernetes (in-cluster) | k8s | SA token + kubeconfig | `cluster_api_server`, `ca_bundle`, `sa_token`, `metric_window` |
| Kubecost | k8s | API key | `kubecost_base_url`, `api_key`, `allocation_window`, `cluster_id_map` |
| Prometheus / Thanos / Mimir | k8s | Bearer / mTLS | `query_endpoint`, `auth_method`, `bearer_token` *or* `client_cert`, `client_key`, `external_labels` |
| FinOps Observability | observability | Internal SA | `index_pattern`, `tenant_id` (default tenant context) |

### 6.9 Custom-function output reference (rule builder)

- The wizard Step 4 dropdown exposes outputs from the Signal Catalog, including:
  - Native signals (e.g., `compute.vm.cpu_utilisation_pct`)
  - Outputs of FinOps-published custom functions registered in the catalog (e.g., `cf://linear_forecast_v2.scalar.predicted_value`)
- Author cannot **define** new custom functions in Basic — that is Advanced. Author can only reference outputs of CFs that are already published and active in the catalog.

### 6.10 Multi-CSP rule semantics

When a Hypothesis selects multiple CSPs in scope:
- The evaluator runs the same rule per-CSP, per-account, per-region partition.
- Findings carry the partition keys so the end-user UI can group correctly.
- SKU mapping must declare per-CSP target SKUs (or a regex pattern that matches across CSPs, e.g., `*.large` for VM rightsize).

### 6.11 Recommendation library and prioritization

Basic ships with a global recommendation library defined in `basic-recommendation-catalog-global.csv`. The original `basic-recommendation-catalog-500.csv` remains as the stable seed baseline.

- The catalog is the implementation contract for 1,030 Basic recommendation definitions.
- Each row defines category, sub-category, provider scope, source provider, action type, priority, end-user value, implementation complexity, primary metrics, baseline thresholds, lookback window, data source/API, SaaS options, Product Catalog dependency, compatibility group, definition, expected benefits, configurator guidance, advisory ID/source, onboarding path, and guardrails.
- CostVars advisories from `FinOps_CostVars_Tooling_v2.docx` are configured as `CVAR-001` through `CVAR-043`; see `basic-costvars-advisory-mapping.md`.
- Engineering must not ship a first-party Basic recommendation unless it maps to a row in this catalog or an approved extension row.
- P0 selection order is: high end-user value, low/medium complexity, strong native metric coverage, Product Catalog availability, and clear realized-savings model.
- Tenant admins can override baseline thresholds, but overrides must be versioned and visible in audit logs.

### 6.12 CSP-native recommendation imports

AWS Compute Optimizer / Cost Optimization Hub / Trusted Advisor, Azure Advisor, and Google Cloud Recommender recommendations are first-class Provider Registry integrations.

- Native recommendations import as FinOps `Finding` records, not as a separate UI surface.
- Imported Findings must normalize to FinOps action types (`Shutdown`, `RightsizeSku`, `DeleteOrphan`, `TierMove`, `CommitmentReview`, etc.).
- Imported Findings preserve source provider, source recommendation ID, source impact estimate, source lookback, and source confidence when available.
- FinOps still recomputes savings using Product Catalog and/or customer billing basis before showing final savings.
- Dismissal, snooze, approval, action, and outcome workflows are identical to FinOps-authored Basic Findings.

### 6.13 Third-party SaaS and AI aggregate metric integrations

Basic supports third-party integrations where the external system exposes deterministic metrics, recommendations, or usage exports. Details are in `basic-integration-framework-guide.md`.

Supported Basic sources include:
- FinOps SaaS: CloudHealth, Cloudability / Apptio, Densify, Datadog Cloud Cost, Kubecost / OpenCost, Spot.io / CAST AI, Flexera / Snow.
- AI usage / LLM gateway: OpenAI usage/cost APIs, Azure OpenAI through Azure Monitor and Cost Management, Bedrock through CUR/CloudWatch, Vertex/Gemini through billing export, LiteLLM, Portkey, Helicone, LangSmith, Langfuse.
- AI compute / experiments: NVIDIA DCGM, GPU Operator, Prometheus, run:ai, W&B, MLflow, DVC, vector DB APIs.

Privacy rule: raw prompts, completions, traces, and full log payloads are not required for Basic. Basic ingests counts, costs, hashed identifiers, model names, token totals, cache hit ratios, and aggregate telemetry.

### 6.14 Product Catalog review view

Basic requires a dedicated Product Catalog view defined in `basic-product-catalog-coverage.md`.

The view must support:
- Provider, category, sub-category, region, SKU/meter search, pricing model, OS/license, technical specs, recommendation eligibility, and freshness filters.
- Source-to-target SKU comparison for authoring Step 5 and Step 6.
- Immutable pricing snapshot IDs on every savings estimate.
- Stale-rate warnings for catalog rates older than 7 days.
- Coverage reporting showing which recommendation definitions are blocked by missing pricing data.

---

## 7. Data Requirements

### 7.1 Data Sources

| Source | Provider | Data Type | Refresh Frequency |
|---|---|---|---|
| AWS CloudWatch | AWS | Resource metrics | 1–5 min lag |
| Azure Monitor | Azure | Resource metrics | 1–5 min lag |
| GCP Cloud Monitoring | GCP | Resource metrics | 1–5 min lag |
| OCI Monitoring | OCI | Resource metrics | 1–5 min lag |
| AWS CUR | AWS | Billing lines | 24 h |
| Azure Cost Export | Azure | Billing lines | 24 h |
| GCP BQ Billing Export | GCP | Billing lines | 24 h |
| OCI Usage Report | OCI | Usage / cost lines | 24 h |
| Kubernetes API + kube-state-metrics | Customer K8s | Pod / node state | 30 s |
| FinOps Observability | FinOps internal | Resource metrics fallback | 1 min |
| AWS Pricing API | AWS | List + commitment rates | Daily |
| Azure Retail Prices API | Azure | List + commitment rates | Daily |
| GCP Cloud Billing Catalog API | GCP | List + commitment rates | Daily |
| OCI Pricing List | OCI | List rates | Weekly |
| AWS Compute Optimizer / Cost Optimization Hub / Trusted Advisor | AWS | Native recommendations | 6-24 h |
| Azure Advisor | Azure | Native recommendations | 6-24 h |
| Google Cloud Recommender | GCP | Native recommendations | 6-24 h |
| CloudHealth / Cloudability / Densify / Datadog / Kubecost / Spot.io / Flexera | Third-party SaaS | Recommendation exports, utilization, allocation, license / seat data | 1-24 h |
| LiteLLM / Portkey / Helicone / LangSmith / Langfuse | AI SaaS / gateway | Token usage, retries, models, cache hits, per-project cost | 5 min-24 h |
| NVIDIA DCGM / GPU Operator / run:ai / W&B / MLflow | AI compute / experiment tools | GPU utilization, GPU memory, checkpoint, sweep, model artifact metrics | 30 s-24 h |

### 7.2 Data Quality & Validation

- Per resource, ≥ 14 days of metric history before a Hypothesis evaluates against it (configurable per Hypothesis).
- Per Hypothesis backtest, ≥ 90% sample density in the backtest window.
- Per Action reconciliation, ≥ 30 days post-action billing data before T+30 outcome is finalised.
- Billing line dedupe: CUR/Cost Export idempotency on `(line_item_id, billing_period)`.
- Pricing freshness: Catalog rejects rates older than 7 days for use in `target_rate()`.
- Provider-native import freshness: imported native recommendations older than 7 days are marked stale and excluded from new Finding creation unless explicitly configured.
- AI aggregate metrics: raw prompts and completions are not required for Basic; token counts, model names, project/user keys, hashed prompt IDs, retry counts, and costs are sufficient.

### 7.3 Data Transformations

| Raw | Canonical | Logic |
|---|---|---|
| `AWS/EC2 CPUUtilization` | `compute.vm.cpu_utilisation_pct` | unit `%`, identity |
| `AWS/EC2 NetworkOut` | `compute.vm.network_egress_bytes` | unit `bytes`, identity |
| `Microsoft.Compute/virtualMachines Percentage CPU` | `compute.vm.cpu_utilisation_pct` | unit `%`, identity |
| `compute.googleapis.com/instance/cpu/utilization` | `compute.vm.cpu_utilisation_pct` | unit `%`, multiply by 100 |
| `kube-state pod.cpu_request_utilization` | `k8s.pod.cpu_request_utilisation_pct` | identity |
| `CUR.lineItem/UnblendedCost` | `billing.resource.cost` | sum by resource_id, day |
| `AzureCostExport CostInBillingCurrency` | `billing.resource.cost` | sum by resource_id, day |

Each canonical signal is enriched at ingest with `tag_*`, `bu`, `cost_centre`, `application`, `domain`, `environment` from Tag Lens hierarchy.

---

## 8. UI/UX Design

The Basic SPA at `web/CXP Optimization/FinOps Recommendation Engine/index.html` is upgraded in place. Visual style stays the same (purple/indigo accent on dark background); layout grammar (top tabs + side rail + main pane) is preserved.

### 8.1 Surface inventory (changed surfaces)

| Surface | Change |
|---|---|
| Wizard Step 1 | Required-field validation; new `owner` (SSO group picker) and `business_justification` fields |
| Wizard Step 2 | CSP selector → multi-select; new account / environment / BU / tag scope rows |
| Wizard Step 3 | Source picker rendered from Provider Registry; CSP + Obs default |
| Wizard Step 4 | Rule builder gains custom-function-output reference + Backtest preview panel |
| Wizard Step 5 | Live target-rate display from Product Catalog |
| Wizard Step 6 | Savings auto-computed; confidence band shown |
| Recommendation detail | New `Realized savings` tab + `Audit log` tab; approver chip becomes group, not text |
| Integrations tab | Generic renderer reading Provider Registry manifests |
| Product Catalog tab | Dedicated browse/review view with provider, category, sub-category, region, SKU, pricing model, OS/license, specs, eligibility, and freshness filters |
| Recommendations list | New `Realized savings (T+30)` column |

### 8.2 Key UI states

| Component | Loading | Success | Empty | Error |
|---|---|---|---|---|
| Backtest preview | Spinner with "Running 30-day backtest…" | "12 hits over 30 days · 4 distinct resources · est. $4,820 / month" | "No hits — rule never matched in window" with "Loosen rule" CTA | Red banner "Backtest failed: ${reason}" with retry button |
| Realized savings | Skeleton rows for T+30 / T+60 / T+90 | Each window shows realized + variance vs estimate | "T+30 reconciliation in 14 days" countdown until window opens | "Reconciliation skipped: billing export not configured" with link to Integrations |
| Savings (Step 6) | Pricing-API call spinner | Estimated point + lower/upper band displayed | "Cannot price: target SKU not in catalog" | "Pricing API error — last successful update {ago}" |
| Approver picker | SSO group fetch spinner | Group picker with search | "No SSO groups available — configure Identity in Integrations" | "Identity provider unreachable" |

### 8.3 Disclaimers & messages

- **Backtest with no data**: *"This rule did not match any resource in the last 30 days. Either loosen the rule, broaden the scope, or extend the backtest window."*
- **Approver picker empty**: *"No SSO groups found. Connect an Identity provider in Integrations to enable RBAC-scoped approvals."*
- **Savings out of band**: *"Estimated savings band is wider than 50 %. Consider tightening the rule's evidence requirements before promoting to active."*
- **Reconciliation regressed**: *"This Action was reconciled but realized savings are < 50 % of estimate. Click to investigate."*

---

## 9. (skipped — covered by ACs in §10)

---

## 10. Acceptance Criteria

### 10.1 Hypothesis authoring & persistence

- **AC-1.1: A submitted Hypothesis is persisted and visible to other users in the same tenant.**
  ```
  Given user U1 has finops.author role in tenant T1
  When U1 completes the wizard and clicks "Submit"
  Then the Hypothesis is persisted via Advisory API with status=draft
  And U2 (also in T1, finops.viewer role) sees the new Hypothesis in the recommendations list within 30 seconds.
  ```

- **AC-1.2: Required fields block submission.**
  ```
  Given U1 is on Step 1 of the wizard
  When U1 clicks "Next" without filling owner or business_justification
  Then the wizard does not advance
  And inline error markers appear next to the missing fields.
  ```

- **AC-1.3: Multi-CSP scope is honoured.**
  ```
  Given U1 selects CSPs = [aws, azure] in Step 2
  When the rule is evaluated
  Then findings are emitted for matching resources in both AWS and Azure
  And each finding carries its csp dimension correctly.
  ```

### 10.2 Backtest

- **AC-2.1: Backtest runs on demand.**
  ```
  Given U1 has authored a rule in Step 4
  When U1 clicks "Run backtest preview"
  Then within 60 seconds the panel displays hit count, distinct-resource count, and estimated aggregate savings.
  ```

- **AC-2.2: Backtest required for promotion.**
  ```
  Given U1 attempts to transition a Hypothesis from draft → shadow
  When the most recent backtest has coverage < 90% OR was run > 7 days ago
  Then the transition is rejected with a clear error citing the failing condition
  And U1 is offered a "Rerun backtest" CTA.
  ```

### 10.3 Live-priced savings

- **AC-3.1: Savings come from the Product Catalog.**
  ```
  Given U1 selects a target SKU in Step 5
  When the wizard moves to Step 6
  Then the savings panel displays a point estimate + lower + upper band
  And the values match Product Catalog.rate_delta() for that source-target pair.
  ```

- **AC-3.2: Stale catalog rates are flagged.**
  ```
  Given Product Catalog last refreshed > 7 days ago for the selected SKU
  When U1 reaches Step 6
  Then the savings panel shows a stale-rate warning with the last refresh date.
  ```

### 10.4 RBAC approvals

- **AC-4.1: Approver is an SSO group, not free text.**
  ```
  Given the wizard renders Step 1
  When U1 sets the "Owner" field
  Then the field is a searchable picker over SSO groups returned from the Identity provider
  And free-text entry is not permitted.
  ```

- **AC-4.2: Action approval requires correct group membership.**
  ```
  Given a Finding requires approval and is routed to group G1
  When user U2 (NOT a member of G1) attempts to approve via the SPA
  Then the Approve button is disabled and a tooltip explains the missing membership.
  ```

### 10.5 Realized-savings reconciliation

- **AC-5.1: T+30 outcome lands.**
  ```
  Given an Action was applied on 2026-04-20
  When the Reconciler runs on 2026-05-21
  Then an Outcome event is emitted with realized_savings, variance_pct_vs_estimate, and status
  And the Hypothesis detail page displays the T+30 row within 1 hour of the event.
  ```

- **AC-5.2: SLO regression triggers regressed state.**
  ```
  Given an Action was applied AND SLO signals exist for the affected resource
  When the Reconciler observes p95 latency increased by ≥ 25% post-action
  Then the Finding transitions to status=regressed
  And an alert is sent to the owner SSO group.
  ```

### 10.6 Provider Registry

- **AC-6.1: New CSP-class provider can be added by manifest.**
  ```
  Given a new YAML manifest is deployed to providers/digitalocean.yaml with category=csp
  When the SPA Integrations tab is reloaded
  Then DigitalOcean appears as an addable integration
  And clicking "Add" renders an onboarding form derived from manifest.auth.parameters.
  ```

- **AC-6.2: Health probe surfaces failure.**
  ```
  Given an integration's health_probe endpoint returns non-200 three times consecutively
  When the Integrations tab refreshes
  Then the integration card shows status=unhealthy with the last error and last_success timestamp.
  ```

### 10.7 Custom-function output reference

- **AC-7.1: Published CF outputs appear in the dropdown.**
  ```
  Given the Signal Catalog has a custom function cf://duty_cycle_v3 registered as active
  And duty_cycle_v3 declares output scalar field "duty_pct"
  When U1 opens the rule builder dropdown in Step 4
  Then "cf://duty_cycle_v3.scalar.duty_pct" appears as a selectable signal.
  ```

### 10.8 Recommendation catalog

- **AC-8.1: Seed recommendation library is loaded.**
  ```
  Given the Basic service starts for a new tenant
  When the seed library is loaded
  Then all active rows from basic-recommendation-catalog-global.csv are available as disabled recommendation definitions
  And admins can enable definitions by provider, category, priority, value, and complexity.
  ```

- **AC-8.2: Every active recommendation has a metric contract.**
  ```
  Given a recommendation definition is enabled
  When the evaluator validates it
  Then every primary metric maps to a Signal Catalog canonical signal
  And missing signal mappings block activation with a clear error.
  ```

### 10.9 Native CSP recommendation imports

- **AC-9.1: Native recommendations import as FinOps Findings.**
  ```
  Given AWS Compute Optimizer, Azure Advisor, or GCP Recommender is connected
  When FinOps syncs native recommendations
  Then each native recommendation becomes a FinOps Finding with source_provider, source_recommendation_id, normalized action type, evidence, and estimated savings.
  ```

- **AC-9.2: Native imported Findings follow the same lifecycle.**
  ```
  Given a native recommendation was imported
  When a user snoozes, dismisses, approves, or applies it
  Then the same Finding/Action/Outcome lifecycle and audit log apply as for FinOps-authored rules.
  ```

### 10.10 Integration setup and customer cost visibility

- **AC-10.1: Integration setup displays customer-side cost estimate.**
  ```
  Given a user configures AWS, Azure, GCP, Kubernetes, SaaS, or AI usage integration
  When the setup wizard reaches review
  Then FinOps shows expected API calls, telemetry ingestion/storage/query costs, required SaaS license dependency, and rate-limit risk before enablement.
  ```

- **AC-10.2: Signal coverage gates recommendation activation.**
  ```
  Given an integration is connected
  When FinOps computes signal coverage
  Then recommendation definitions with missing required metrics are disabled
  And the UI explains which metric/source blocks activation.
  ```

### 10.11 Product Catalog review view

- **AC-11.1: Catalog can be browsed and filtered.**
  ```
  Given Product Catalog data is available
  When a user opens the Product Catalog tab
  Then they can filter by provider, category, sub-category, region, SKU/meter, pricing model, OS/license, technical specs, eligibility, and freshness.
  ```

- **AC-11.2: Savings estimates cite immutable pricing snapshots.**
  ```
  Given a Finding shows estimated savings
  When the user opens pricing basis
  Then FinOps displays source SKU rate, target SKU rate, region, currency, effective date, pricing model, and pricing_snapshot_id.
  ```

### 10.12 AI aggregate metric recommendations

- **AC-12.1: AI cost rules run without raw prompt ingestion.**
  ```
  Given an LLM gateway integration exposes prompt_tokens, completion_tokens, model, request_count, retry_count, cache_hit_pct, and cost
  When a token-cost recommendation runs
  Then FinOps evaluates the rule without storing raw prompts or completions.
  ```

- **AC-12.2: GPU cost rules run from aggregate GPU telemetry.**
  ```
  Given DCGM or equivalent GPU metrics are connected
  When GPU idle/rightsize recommendations run
  Then FinOps evaluates gpu_util_pct, gpu_mem_used_pct, job_queue_depth, and SKU rate without requiring trace data.
  ```

### 10.E Failure scenarios (required)

- **AC-E1: Persistence failure.**
  ```
  Given the Advisory API is unavailable
  When U1 clicks Submit
  Then the wizard does not lose state
  And a toast appears: "Save failed — your work is preserved locally. Retry?"
  And U1 can retry without re-entering data.
  ```

- **AC-E2: Idempotent submit.**
  ```
  Given U1 clicks Submit and the network connection drops mid-call
  When U1 retries Submit
  Then the same Idempotency-Key is used
  And no duplicate Hypothesis is created.
  ```

- **AC-E3: Reconciler skip.**
  ```
  Given billing export is not configured for the tenant
  When the Reconciler attempts to run
  Then it logs a skip with reason=no_billing_export
  And the Hypothesis detail page shows a banner with a link to configure billing export.
  ```

---

## 11. Non-Functional Requirements

| Category | Baseline | This Feature's Requirement |
|---|---|---|
| **Performance** — wizard step transitions | < 3 s | < 1 s for Steps 1–5; Step 4 backtest preview ≤ 60 s |
| **Performance** — evaluator | — | p95 ≤ 5 s per Hypothesis × 10 k resources |
| **Performance** — backtest | — | 90-day, 10 k-resource backtest ≤ 5 minutes |
| **Scalability** | 10 k resources / customer | Support up to 200 active Hypotheses per tenant |
| **Security / RBAC** | persona-scoped | All mutating endpoints enforce scope; Approver field cannot be free text |
| **Availability** | 99.9 % | 99.9 % for Advisory API; 99.5 % for Reconciler (longer windows acceptable) |
| **Data Retention** | 13 months | Hypothesis + Finding + Action + Outcome events retained 24 months |
| **Audit / Logging** | actor + before/after | Immutable hash-chained audit trail; 24-month retention |
| **Idempotency** | — | All mutating endpoints accept Idempotency-Key (24 h dedupe window) |
| **Multi-tenant safety** | — | Every query carries tenant_id; cross-tenant access is logged and alerted |
| **Cost-type consistency** | follows admin selection | Realized savings respect tenant's `default_cost_type` (List / Chargeback / Amortised) |

---

## 12. Dependencies & Risks

### 12.1 Dependencies

| Dependency | Owner | Impact if Delayed |
|---|---|---|
| Advisory API (new service) | Platform Eng | Blocks O1, O2, O3 — entire PRD |
| Provider Registry (new service) | Platform Eng | Blocks O6 — Integrations tab cannot ship |
| Signal Catalog (new service) | Platform Eng | Blocks rule evaluator and backtest |
| Product Catalog (new service) | Data Eng | Blocks O5 — savings priced from catalog |
| Reconciler (new service) | Data Eng | Blocks O2 — realized savings loop |
| Identity provider integration (Okta/AAD/Ping/Google) | Customer onboarding | Blocks O3 — SSO group picker; mocked in SPA until live |
| Tag Lens enrichment | FinOps Platform | Blocks BU / cost-centre attribution at ingest |

### 12.2 Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Customers expect the SPA to behave the same on day one of upgrade | High | Med | Migration script imports current SAMPLE_RECOMMENDATIONS as `active` Hypotheses; all wizard steps remain functionally identical to today |
| Backtest performance pegs ES at scale | Med | High | Hot/warm tier separation in Signal Catalog; backtest runs against warm Parquet, not hot ES |
| Pricing-API rate limits | Med | Med | Catalog batched refresh + per-tenant cache; never on-demand from wizard |
| Reconciler latency vs CFO reporting cadence | High | High | Communicate explicit T+30 SLA; show countdown until first outcome on Hypothesis detail |
| Identity provider scope mismatch with tenant scope | Med | Med | Group resolution always intersects with tenant scope before write; conflicts logged |

---

## 13. Rollout & Migration Plan

| Phase | Scope | Timeline | Notes |
|---|---|---|---|
| **Phase 0** — Backbone services up | Internal alpha, FinOps-only tenant | Weeks 1–6 | Advisory + Provider Registry + Signal Catalog + Product Catalog + Reconciler all in dev |
| **Phase 1** — SPA upgrades wired to backbone | Design partners (3 tenants) | Weeks 5–10 | Migration script imports existing SAMPLE_RECOMMENDATIONS as `active` Hypotheses; UX flag enables new wizard steps |
| **Phase 2** — GA | All tenants | Weeks 10–14 | Old SPA flow disabled behind feature flag; rollback path retained for 30 days |
| **Phase 3** — Provider Registry self-service | Add 4 new providers via manifest only | Weeks 12–16 | Validates that provider onboarding is genuinely manifest-driven |

Migration script:
- Reads existing `SAMPLE_RECOMMENDATIONS` from the SPA bundle.
- For each, creates a Hypothesis at version 1 with status=`active`.
- Runs a backtest against last 30 days; if hit rate ≠ 0, ratifies.
- If hit rate = 0, marks as `shadow` and notifies FinOps PM.

---

## 14. Open Questions

| # | Question | Blocking? | Owner | Target | Status |
|---|---|---|---|---|---|
| 1 | Approver group resolution: do we use Identity-provider-native groups, or FinOps-internal scope groups, or both? | Yes | Security Lead | 2026-05-03 | Open |
| 2 | Reconciler — should we attempt reconciliation for Findings the user dismissed but the underlying resource changed anyway (e.g., they applied via console)? | No, but UX | Product | 2026-05-10 | Open |
| 3 | What's the tenant-level default for backtest window — 30, 60, or 90 days? | No (configurable) | FinOps PM | 2026-05-03 | Open |
| 4 | How do we surface CSP-native advisor recommendations (AWS Compute Optimizer, Azure Advisor, GCP Recommender) in Basic — first-class as Findings, or as a distinct surface? | No | FinOps PM | 2026-04-29 | Resolved — first-class FinOps Findings with source metadata |
| 5 | Custom function reference: do we restrict references to CFs in the customer's tenant only, or allow FinOps-published global CFs? | Yes | Security Lead | 2026-05-10 | Open |

---

## 15. Appendix

### 15.1 Glossary

| Term | Definition |
|---|---|
| Hypothesis | The authored rule artifact; carries scope, signals, conditions, action proposals, savings model |
| Finding | Per-resource detection emitted by the evaluator from a Hypothesis |
| Action | Typed proposal to remediate a Finding (Shutdown, RightsizeSku, etc.) |
| Outcome | Reconciled realized savings event emitted by the Reconciler at T+30/60/90 |
| Provider Registry | Manifest-driven integration catalogue |
| Signal Catalog | Canonical metric registry across all sources |
| Product Catalog | Live CSP pricing across SKUs, regions, commitment states |
| Reconciler | Service that joins Actions to billing to compute realized savings |
| SSO group | Identity-provider group used for RBAC scoping |
| Backtest | Replay of an evaluator against historical Signal Catalog data |
| Shadow mode | Hypothesis state where Findings are emitted but hidden from end users |

### 15.2 Reference documents

- `docs/architecture/finops-recommendation-engine.md` — technical design (both tiers)
- `pm/features/finops-recommendation-engine/basic-requirements-critical-review.md` — Basic-only gap review and revamped requirements
- `pm/features/finops-recommendation-engine/basic-recommendation-catalog.md` — usage guide for the global recommendation catalog
- `pm/features/finops-recommendation-engine/basic-recommendation-catalog-500.csv` — stable seed recommendation library retained for comparison
- `pm/features/finops-recommendation-engine/basic-recommendation-catalog-global.csv` — global recommendation library with metrics, thresholds, benefits, advisory IDs, priority, complexity, data sources, onboarding path
- `pm/features/finops-recommendation-engine/basic-costvars-advisory-mapping.md` — CostVars advisory ID to recommendation row mapping
- `pm/features/finops-recommendation-engine/basic-integration-framework-guide.md` — integration setup guide for CSPs, SaaS, K8s, AI usage, GPU telemetry
- `pm/features/finops-recommendation-engine/basic-product-catalog-coverage.md` — extracted Product Catalog coverage and browse view requirements
- `pm/features/finops-recommendation-engine/basic-system-user-guide.md` — end-to-end Basic system usage and operating guide
- `docs/finops_finops_capability_inventory.md` — ADV-* capability rows superseded by this feature
- `web/CXP Optimization/FinOps Recommendation Engine/index.html` — current SPA (upgraded in place)

### 15.3 API Contract (high level)

```
POST   /api/v1/hypotheses                         — create draft (Idempotency-Key required)
PUT    /api/v1/hypotheses/{id}                    — update (creates new version)
POST   /api/v1/hypotheses/{id}/transitions        — { from, to, justification } — drives lifecycle
POST   /api/v1/hypotheses/{id}/backtest           — { window_days } → backtest_id
GET    /api/v1/backtests/{id}                     — { status, results }
GET    /api/v1/findings?hypothesis_id=…           — paged
POST   /api/v1/findings/{id}/transitions          — { to, reason_code, comment }
POST   /api/v1/actions                            — { finding_id, type, parameters, delivery_channel }
POST   /api/v1/actions/{id}/approve               — RBAC-checked
GET    /api/v1/outcomes?action_id=…               — list reconciled outcomes
GET    /api/v1/audit?entity_type=…&entity_id=…    — audit projection
GET    /api/v1/providers                          — Provider Registry list
POST   /api/v1/providers/{id}/instances           — onboard an integration instance
GET    /api/v1/providers/{id}/instances/{iid}/health — probe state
GET    /api/v1/recommendation-definitions          — seed library and tenant-enabled definitions
POST   /api/v1/recommendation-definitions/{id}/enable — enable seeded definition for tenant scope
POST   /api/v1/providers/{id}/sync-native-recommendations — import CSP/SaaS native recommendations as Findings
GET    /api/v1/product-catalog/coverage            — pricing coverage by provider/resource/region
GET    /api/v1/product-catalog/skus                — browse/filter SKU catalog
POST   /api/v1/product-catalog/rate-delta          — compare source and target SKU/rate snapshot
```

### 15.4 State Machine (Hypothesis)

```
                ┌──────────┐
                │  draft   │
                └────┬─────┘
                     │ promote (backtest passes)
                     ▼
                ┌──────────┐  reject (review)
                │  shadow  │ ◀─────────────────┐
                └────┬─────┘                   │
                     │ activate (≥ 7 d shadow) │
                     ▼                         │
                ┌──────────┐                   │
                │  active  │ ──── backtest fail ┘
                └────┬─────┘
                     │ deprecate
                     ▼
                ┌──────────────┐
                │  deprecated  │
                └──────────────┘
```

---

*PRD version: 1.1 · Tier: Basic · Companion: basic-requirements-critical-review.md, basic-recommendation-catalog-global.csv, basic-costvars-advisory-mapping.md, basic-integration-framework-guide.md, basic-product-catalog-coverage.md, basic-system-user-guide.md, docs/architecture/finops-recommendation-engine.md*
