# FinOps Recommendation Engine — Technical Architecture

**Status:** Draft · v1.0 · 2026-04-20
**Owner:** Platform / FinOps Optimization
**Related PRDs:** `pm/features/finops-recommendation-engine/prd-basic.md`, `prd-advanced.md`
**Supersedes:** Ad-hoc architecture implicit in `web/CXP Optimization/FinOps Recommendation Engine/index.html`

---

## 1. Scope and framing

FinOps ships **one recommendation product in two tiers**:

1. **Basic** — deterministic, rule-based, operating over CSP metrics + billing + K8s + FinOps Observability. The existing `FinOps Recommendation Engine` SPA is promoted to this tier with gap-closures limited to what is achievable inside a rule-based model.
2. **Advanced** — signal-fusion engine operating over APM traces, query history, LLM usage, flow logs, commitment portfolios, product analytics, workload fingerprint classifiers. Delivered through a **separate SPA** with an internal authoring console and an end-user findings viewer.

Both tiers share a common backbone. This document specifies that backbone and each tier's differences.

### 1.1 Non-goals

- Building an autonomous AI agent that makes recommendations from raw data without engineering or PM curation. Both tiers assume human-authored hypotheses (structured rules in Basic, signal graphs in Advanced).
- Replacing CSP-native advisors (AWS Compute Optimizer, Azure Advisor, GCP Recommender). FinOps ingests them as normalized Basic Findings and can also reuse them as signals in Advanced.
- Building an IaC planner. FinOps generates Terraform / Pulumi diff proposals — it does not own state.

---

## 2. Shared backbone services

Both tiers depend on the same five services. None of them exist today; all are P0 for Basic and P0–P1 for Advanced.

| # | Service | Responsibility | Consumers |
|---|---|---|---|
| 1 | **Advisory Service** | CRUD over `Hypothesis` entities; emits `Finding`, `Action`, `Outcome` events; owns lifecycle state machine; RBAC-scoped approvals via SSO groups | Both tiers |
| 2 | **Provider Registry** | Declarative manifest per integration (auth, parameter schema, metric contract, resource-type bindings); renders onboarding forms; health and rate-limit tracking | Both tiers |
| 3 | **Signal Catalog** | Canonical metric + dimension registry; per-source schema contracts; enrichment rules (cost per sample, tag inheritance, BU / cost-centre join) | Both tiers |
| 4 | **Product Catalog** | Live CSP pricing (list + committed + spot) via SKU and region dimensions; resolves current/target rate for savings formulas; replaces in-file `SKU_CATALOG` | Both tiers |
| 5 | **Reconciler** | Joins `Action` events to billing streams (CUR / Azure Cost Export / BQ billing export) at T+30/60/90; computes realized-vs-estimated savings; feeds back into author's dashboard | Both tiers |

### 2.1 Entity model (shared)

```
Hypothesis (authored) ──emits──▶ Finding (per resource)
                                       │
                                       ├──▶ Action (typed, with rollback)
                                       │           │
                                       │           └──▶ Outcome (reconciled savings)
                                       │
                                       └──▶ Dismissal (reason code — feedback)
```

All four entities are immutable events appended to an event log. State is a projection of the event log.

**Hypothesis** (authoring artifact — both tiers):
- `id`, `name`, `version`, `tier` (basic | advanced), `owner`, `lifecycle` (draft | shadow | active | deprecated)
- `scope`: CSPs[], accounts[], environments[], BUs[], resource_types[], tag_selectors[]
- `signals[]`: source bindings (CSP metric, billing field, K8s metric, APM query, trace attribute, custom function output)
- `conditions`: boolean graph over signals with statistical operators (Basic: threshold only; Advanced: anomaly, seasonality, percentile-vs-baseline, cross-signal joins)
- `evidence_requirements`: min window, min samples, min confidence
- `action_proposals`: typed action objects (see §2.3)
- `risk_profile`: blast_radius, reversibility, SLO tier, change_window
- `savings_model`: formula ref to Product Catalog rates + confidence band method
- `metadata`: category, subcategory, severity, complexity, documentation link

**Finding** (per-resource detection):
- `hypothesis_id`, `hypothesis_version`, `resource_id`, `detected_at`, `expires_at`, `fingerprint_hash` (dedupe key)
- `evidence`: structured references — metric series slices, billing lines, trace IDs, log IDs, pricing rows — everything needed to defend the finding to a resource owner
- `proposed_action`: concrete parameters (target SKU, schedule, commitment size, tier move) bound to the Hypothesis's action_proposal template
- `estimated_savings`: `{point, lower, upper, basis}` where basis ∈ {retail, chargeback}
- `risk_score`: 0–100 with per-dimension breakdown (blast radius, reversibility, SLO impact, data loss risk)
- `owner`: resolved via tag inheritance or hierarchy mapping, SSO group hint
- `lifecycle`: `new | snoozed | approved | applied | reconciled | dismissed | expired`

**Action** (execution artifact):
- `finding_id`, `type` (see §2.3), `parameters`, `delivery_channel` (auto_apply | itsm_ticket | iac_pr | slack_approval)
- `approver`, `approved_at`, `applied_at`, `rollback_plan`, `change_window`

**Outcome** (reconciliation):
- `action_id`, `baseline_window`, `observation_window_days` (30/60/90), `realized_savings` (reconciled against billing), `variance_pct` (vs estimate), `slo_impact` (latency p95 / error rate deltas), `status` (pending | realized | regressed | dismissed)

### 2.2 Lifecycle state machine

```
Hypothesis:    draft ──▶ shadow ──▶ active ──▶ deprecated
                │           │          │
                └─(review)──┘          └──▶ (backtest fail → back to shadow)

Finding:       new ──▶ snoozed | approved | dismissed
                      approved ──▶ applied ──▶ reconciled
                      applied  ──▶ regressed (SLO breach → auto-rollback)

Action:        proposed ──▶ approved ──▶ applied ──▶ rolled_back | realized
```

Mandatory transitions:
- `draft → shadow`: backtest must execute against ≥30 days of historical data with ≥90% coverage.
- `shadow → active`: minimum 7 days in shadow mode, owner reviews produced findings, no P0 false-positive incidents.
- `applied → reconciled`: at T+30, T+60, T+90 the Reconciler joins billing facts and writes the `Outcome`.

### 2.3 Typed action vocabulary

Replaces the current `shutdown | rightsize` binary in the SPA. Each tier supports a defined subset.

| Action type | Tier | Description | Delivery channels |
|---|---|---|---|
| `Shutdown` | Basic + Advanced | Stop / terminate / delete an idle resource | auto | itsm | iac_pr |
| `RightsizeSku` | Basic + Advanced | Move to a smaller/larger SKU with target rate from Product Catalog | auto | itsm | iac_pr |
| `SchedulePause` | Basic + Advanced | Apply a cron-style on/off schedule (non-prod workloads) | auto | itsm |
| `TierMove` | Basic + Advanced | Move object/storage to cheaper tier (S3 IA, GCS Coldline, Azure Cool) | auto | itsm |
| `DeleteOrphan` | Basic | Remove unreferenced snapshots / AMIs / EIPs / LBs | auto | itsm |
| `VolumeTypeSwap` | Basic | gp2→gp3, Premium→Balanced SSD, with IOPS retention | auto | itsm | iac_pr |
| `CommitmentReview` | Basic | Import simple CSP-native RI / SP / CUD / reservation opportunities for human review; no portfolio optimization | itsm | human_approval |
| `TagFix` | Basic | Missing / invalid tag remediation for cost allocation | itsm |
| `BudgetReview` | Basic | Forecasted budget breach review | itsm | human_approval |
| `ModelRoute` | Basic | Rule-based AI model/token-cost routing recommendation from aggregate usage metrics | itsm | human_approval |
| `SpotReview` | Basic | Obvious tag/checkpoint-based spot/preemptible candidate review | itsm | human_approval |
| `LicenseReview` | Basic | License-included / BYOL opportunity review from CSP or license SaaS data | itsm | human_approval |
| `CommitmentPurchase` | Advanced | Acquire RI / SP / CUD / reservation with ladder plan | itsm | human_approval |
| `SpotMigrate` | Advanced | Move workload to spot/preemptible with fallback pool | iac_pr | human_approval |
| `AutoscalingPolicyChange` | Advanced | Rewrite HPA / KEDA / target-tracking policy | iac_pr |
| `RegionConsolidate` | Advanced | Architecture-level data placement change | iac_pr | human_approval |
| `LicenseBYOB` | Advanced | Enable Azure Hybrid Benefit / AWS License Manager BYOL / GCP sole-tenant | itsm | iac_pr |
| `QueryOptimise` | Advanced | Materialise/partition/cluster/cache a query | itsm | slack_approval |
| `ModelRoute` | Advanced | Route LLM traffic to smaller/cached/batch API variant | iac_pr | slack_approval |
| `EndpointDeprecate` | Advanced | Surface unused APM endpoints; propose deprecation | itsm |

---

## 3. Basic engine architecture

The Basic engine is a rule-based evaluator over a bounded signal set. Its architectural promise is **deterministic, auditable, and fast**.

### 3.1 Data sources (bounded list)

| Source | Type | Used for |
|---|---|---|
| CSP Metrics APIs | CloudWatch, Azure Monitor, GCP Cloud Monitoring, OCI Monitoring | Resource utilisation series |
| CSP Resource APIs | EC2/EBS DescribeInstances, Azure Resource Graph, GCP Asset Inventory, OCI compute API | State, attributes, tags |
| CSP Billing exports | AWS CUR, Azure Cost Export, GCP BQ billing, OCI usage report | Cost lines, commitment drawdown, anomaly baselines |
| FinOps Observability | Internal Elasticsearch indices per resource type | Fallback when CSP agent is absent |
| Kubernetes metrics | kube-state-metrics, metrics-server, cAdvisor | Pod/node utilisation |
| CSP-native advisors | AWS Compute Optimizer / Cost Optimization Hub / Trusted Advisor, Azure Advisor, Google Cloud Recommender | Native recommendation import as normalized FinOps Findings |
| Third-party FinOps SaaS | CloudHealth, Cloudability, Densify, Datadog Cloud Cost, Kubecost/OpenCost, Spot.io, Flexera | Deterministic recommendation exports, utilization, allocation, license / seat data |
| AI aggregate telemetry | LLM usage APIs, LiteLLM, Portkey, Helicone, LangSmith/Langfuse, DCGM, run:ai, W&B, MLflow, vector DB APIs | Token, retry, model, GPU, checkpoint, sweep, vector-index metrics for rule-based AI recommendations |

No APM trace-level attribution, raw prompt/completion storage, SQL/query-plan analysis, product analytics joins, or probabilistic signal fusion. Those remain Advanced.

### 3.2 Evaluator

A deterministic boolean evaluator that compiles `Hypothesis.conditions` into a query plan:

1. Fetch required signal windows from Signal Catalog-backed query layer.
2. Apply aggregations (`avg | min | max | p50/90/95/99 | sum | count | stddev | rate`).
3. Evaluate operator chain (`< > <= >= == != BETWEEN IN EXISTS IS_NULL`).
4. Combine via AND/OR at inner-group and outer-group levels.
5. If all clauses pass → emit `Finding` with bound evidence slices.

Supported operators, functions, and windows are explicitly whitelisted. No custom code executes inside the Basic evaluator.

### 3.3 Backtest

Every `Hypothesis` is backtested before transitioning to `shadow` or `active`:

- Replay the evaluator against 30–90 days of historical Signal Catalog data.
- Produce: hit count, per-resource-type breakdown, estimated aggregate savings, false-positive rate (overlap with prior dismissals), coverage gaps.
- Reject the promotion transition if coverage < 90% or FP rate > configured tenant threshold.

### 3.4 Limitations Basic accepts by design

- Cannot reason about workload behaviour beyond statistical summaries of a fixed metric list.
- Cannot attribute cost to business dimensions beyond CSP tags and pre-configured hierarchy.
- Cannot propose architecture, commitment, or scheduling actions that require multi-signal fusion.
- Rule authors specify thresholds; the engine does not learn them.

All of these are Advanced's job.

---

## 4. Advanced engine architecture

The Advanced engine is a signal-fusion system. Its architectural promise is **evidence-rich findings grounded in workload, portfolio, and business context**, with actions that cite their evidence.

### 4.1 Signal graph

A `Hypothesis` in Advanced references a **Signal Graph** — a DAG of signal nodes, transform nodes, and condition nodes.

```
 [CSP metric]    [APM trace]     [Billing]     [Workload fingerprint]
      │              │               │                 │
      └──────┬───────┴──────┬────────┴─────────┬──────┘
             ▼              ▼                  ▼
        [Join on pod]  [Join on service]  [Join on resource]
             │              │                  │
             └──────┬───────┴──────────┬──────┘
                    ▼                  ▼
              [Transform: cost-    [Transform: fingerprint
               per-endpoint]        classifier]
                    │                  │
                    └───┬──────────────┘
                        ▼
                [Condition: P95 cost/call
                 > 3σ of peers for 14 days]
                        │
                        ▼
                   [Emit Finding]
```

Nodes are defined in a manifest (YAML or JSON). The wizard UI for Advanced authoring is a graph editor over this structure.

### 4.2 Transform nodes (vs Basic aggregations)

In addition to Basic's aggregation whitelist, Advanced supports:
- **Statistical transforms**: `fft`, `duty_cycle`, `seasonal_decompose`, `anomaly_2sigma`, `percentile_vs_baseline`, `trend_slope`, `step_change_point`.
- **Classifier transforms**: `workload_fingerprint` (steady / bursty / batch / diurnal / seasonal), `spot_readiness_score`, `slo_budget_headroom`.
- **Attribution transforms**: `cost_per_label` (joins billing with tags or APM service attribute), `cost_per_customer`, `cost_per_feature`, `token_cost_per_prompt`.
- **Architectural transforms**: `egress_graph` (per-region byte flow), `commitment_burn_rate`, `license_utilisation_map`.
- **Custom functions**: signed, sandboxed transforms executed by the Custom Function Runtime (see §4.5).

### 4.3 Evidence binding

Every emitted `Finding` is accompanied by a structured `evidence` object whose contents are **enforced at emit time** by the Hypothesis's `evidence_requirements`. The rendering layer in the end-user UI reads this object directly — authors cannot ship a finding without evidence bound.

Evidence fields can reference:
- Metric series slice URL (time range + dimensions)
- Trace IDs (APM vendor link)
- Log record IDs (log vendor link)
- Billing line IDs (CUR row)
- SKU pricing row (Product Catalog snapshot)
- Workload fingerprint classification (with confidence score)
- Peer comparison set (other similar resources for context)

### 4.4 Anti-noise controls

Because Advanced surfaces harder-to-explain findings, it adds controls Basic does not need:
- **Peer comparison**: finding suppressed if it is not statistically different from peers in same scope.
- **Confidence band requirement**: `savings_model.confidence_lower > 0` to emit (no negative-savings findings).
- **Dedupe fingerprint**: `(hypothesis_id, resource_id, coarse_window)` — one active finding per window.
- **Owner resolution gate**: finding parked in `awaiting_owner` until tag / hierarchy lookup resolves.

### 4.5 Custom Function Runtime

Transforms beyond the whitelist are user-authored JavaScript or Python functions running in a sandbox:
- Sandboxed in `isolate-vm` (Node) or `firejail+seccomp` (Python).
- CPU limit 30 s, memory limit 512 MB, no network, no filesystem except stdin/stdout.
- Inputs: `metric series[], dimensions{}, window`.
- Outputs: `transformed series[], scalar fields{}, metadata{}`.
- Versioned, signed with platform key, reviewed before being promotable to `active`.
- Failure isolation: transform errors do not kill the Hypothesis evaluation — they emit a `finding_error` with a reason code.

### 4.6 Shadow mode (required for Advanced)

Every Advanced Hypothesis spends ≥ 7 days in `shadow` — findings are produced but hidden from end users; PM/ops reviews them for precision before promoting to `active`. Basic allows skipping shadow; Advanced does not.

---

## 5. Provider Registry

Replaces the hard-coded CSP onboarding UI in today's SPA. The Provider Registry is the canonical integration mechanism for both tiers.

### 5.1 Manifest schema

```yaml
# providers/datadog.yaml
provider:
  id: datadog
  name: Datadog
  category: apm_metrics_logs     # csp | billing | apm_metrics_logs | k8s | data_platform | llm | itsm | iac | identity | notification | secret | product_analytics | crm
  tier_support: [advanced]        # basic | advanced
  version: 1.0.0

auth:
  type: api_key_pair              # iam_role | service_principal | service_account | api_key | api_key_pair | oauth | pat
  parameters:
    - key: site
      label: Datadog site
      type: enum
      values: [us1, us3, us5, eu1, ap1]
      required: true
    - key: api_key
      label: API key
      type: secret
      required: true
    - key: app_key
      label: Application key
      type: secret
      required: true

rate_limits:
  budget_per_minute: 600
  backoff_strategy: exponential

health_probe:
  endpoint: /api/v1/validate
  expected_status: 200
  check_interval_seconds: 300

metric_contract:
  # Canonical metric names this integration can provide.
  # Catalog Service registers these as 'signals' available to Hypothesis authors.
  signals:
    - canonical_name: apm.service.request.latency_p95
      source_metric: trace.servlet.request.duration_p95
      unit: ms
      dimensions: [service.name, env, version, customer_id, feature_id]
    - canonical_name: apm.service.request.rate
      source_metric: trace.servlet.request.hits
      unit: rps
      dimensions: [service.name, env, version]
    - canonical_name: apm.endpoint.cost_per_call
      derived_from: [apm.service.request.rate, billing.service.cost]
      unit: usd_per_call

resource_type_bindings:
  # Which FinOps resource types can this integration enrich with signals?
  - resource_type: vm
    match_on: [service.name, host.name, cloud.instance_id]
  - resource_type: container
    match_on: [service.name, k8s.pod.name, k8s.namespace]
  - resource_type: serverless
    match_on: [service.name, faas.name]

documentation:
  onboarding_steps_url: https://docs.finops.io/integrations/datadog/onboarding
  permissions_url: https://docs.finops.io/integrations/datadog/permissions
  rate_limit_guidance_url: https://docs.finops.io/integrations/datadog/rate-limits
```

### 5.2 Runtime behaviour

- **Onboarding UI**: rendered generically from `auth.parameters`. Secret fields flagged `type: secret` are written directly to Vault; the UI never echoes them.
- **Health probe**: runs on schedule from `health_probe.check_interval_seconds`; feeds the Integrations tab health state.
- **Catalog registration**: on activation, `metric_contract.signals` are registered into the Signal Catalog and become selectable in Hypothesis authoring.
- **Resource binding**: when a finding is emitted, the binding rules are used to enrich evidence with external links (e.g., Datadog trace URL for the same `service.name`).

### 5.3 Supported provider categories (v1)

Each category has a schema sub-template so adding a new provider in that category is a manifest-only change:

- `csp` — AWS, Azure, GCP, OCI metrics + resource APIs
- `billing` — AWS CUR, Azure Cost Export, GCP BQ billing, OCI usage report
- `apm_metrics_logs` — Datadog, New Relic, Dynatrace, Splunk, ElasticCloud, OTel
- `k8s` — native K8s API, Kubecost, Prometheus/Thanos/Mimir, Grafana Cloud
- `data_platform` — Snowflake, Databricks, BigQuery, Redshift
- `llm` — OpenAI, Anthropic, Bedrock, Vertex AI
- `itsm` — ServiceNow, Jira
- `iac` — GitHub App, GitLab, Bitbucket, Terraform Cloud / HCP
- `identity` — Okta, Azure AD, Ping (OIDC + SCIM)
- `notification` — Slack, MS Teams, PagerDuty
- `secret` — HashiCorp Vault, AWS Secrets Manager, GCP Secret Manager, Azure Key Vault
- `product_analytics` — Amplitude, Segment, LaunchDarkly, Heap
- `crm` — Salesforce, HubSpot, Stripe

---

## 6. Signal Catalog and data contracts

### 6.1 Canonical signal namespace

Every signal has a canonical name in the form `<domain>.<subject>.<attribute>` with a declared unit and dimension set. Sources register source-specific mappings. The evaluator only operates on canonical names.

Examples:
- `compute.vm.cpu_utilisation_pct` — unit `%`, dims `[resource_id, region, instance_family]`
- `compute.vm.memory_utilisation_pct` — unit `%`
- `compute.vm.network_egress_bytes_per_sec` — unit `bytes_per_second`
- `k8s.pod.cpu_request_utilisation_pct` — unit `%`
- `k8s.pod.memory_usage_bytes` — unit `bytes`
- `billing.resource.cost` — unit `usd`
- `billing.service.spend` — unit `usd`, dims `[service, account, day]`
- `apm.service.request.latency_p95` — unit `ms`, dims `[service, env, customer_id]`
- `apm.endpoint.cost_per_call` — unit `usd_per_call`, dims `[service, endpoint, method]`
- `database.query.execution_time_ms` — unit `ms`, dims `[warehouse, query_fingerprint]`
- `database.query.bytes_scanned` — unit `bytes`, dims `[warehouse, query_fingerprint]`
- `llm.prompt.input_tokens` — unit `tokens`, dims `[model, prompt_template_id, customer_id]`
- `llm.prompt.cost_usd` — unit `usd`, dims `[model, prompt_template_id, customer_id]`
- `network.flow.egress_bytes` — unit `bytes`, dims `[src_region, dst_region, src_account, dst_account]`
- `commitment.coverage_pct` — unit `%`, dims `[csp, instance_family, region]`

### 6.2 Enrichment at ingest

Every raw sample is enriched with:
- `resource_id` normalisation (cross-CSP canonical form)
- Tag inheritance from FinOps Tag Lens
- Hierarchy attribution (BU / Domain / Application)
- Cost-per-sample (joins billing stream at best available grain)
- Cost-centre mapping via Chargeback rules

This happens once at ingest, not at query time. Downstream evaluator queries get enriched samples for free.

### 6.3 Storage tiers

- **Hot** (7 days at 1-minute grain): Elasticsearch or similar TSDB — used by shadow-mode evaluation.
- **Warm** (90 days at 5-minute grain): columnar (Parquet on S3/GCS) — used by backtest and reconciler.
- **Cold** (2 years at hourly grain): object storage — compliance / trend analysis only.

---

## 7. Product Catalog

Replaces the in-file `SKU_CATALOG` in the current SPA.

### 7.1 Data sources

- AWS Pricing API (`pricing.api.aws`)
- Azure Retail Prices API
- GCP Cloud Billing Catalog API
- OCI Pricing List API
- Customer-specific negotiated rates from EA / MCA / Enterprise Agreement exports
- Commitment rates (RI / SP / CUD) from billing exports

### 7.2 Resolved objects

- `current_rate(resource_id, effective_date)` — returns the priced rate the resource currently pays (list, chargeback, or committed)
- `target_rate(target_sku, region, commitment_state)` — returns the priced rate for a proposed target
- `rate_delta(current_rate, target_rate, hours)` — returns savings point estimate + basis
- `confidence_band(current, target, historical_sku_usage)` — returns lower/upper band for savings

### 7.3 Refresh cadence

- CSP list prices: daily
- Commitment rates: on billing export refresh (typically daily with 24–48h lag)
- EA/MCA rates: when customer uploads a new rate card

---

## 8. Reconciler

### 8.1 Trigger

On every `Action.applied` event, schedule three reconciliation windows:
- T+30: first reliable billing snapshot
- T+60: validation
- T+90: final outcome + feed model recalibration

### 8.2 Method

1. Resolve resource_id from Action.
2. Pull billing cost series for `[applied_at − baseline_window, applied_at + observation_window]`.
3. Normalise against usage baseline (hours running, storage retained, etc.) — otherwise a shutdown inflates savings.
4. Compute delta against baseline window of equal length prior to Action.
5. Write `Outcome` with realized_savings, variance_pct vs estimate, SLO impact (if SLO signals exist for the resource).
6. If SLO regressed → trigger `regressed` transition on Finding; notify owner.

### 8.3 Aggregation

Per-tenant dashboard shows:
- Realized savings total
- Realized-vs-estimated variance by Hypothesis (feeds author feedback)
- Top 10 applied Findings by realized value
- Regressed Findings requiring attention

---

## 9. RBAC and approval flow

### 9.1 Identity sources

Federated identity via OIDC (Okta, Azure AD, Ping, Google Workspace). Groups via SCIM or SAML attribute mapping.

### 9.2 Roles

| Role | Capabilities |
|---|---|
| `finops.admin` | Author Hypotheses in any tier; configure Provider Registry; manage Product Catalog rate overrides; approve any Action |
| `finops.author` | Author Hypotheses in scopes they own; require approval for promotion from `draft → shadow` or `shadow → active` |
| `finops.approver` | Approve Actions in assigned scopes; cannot author Hypotheses |
| `resource_owner` | Approve Actions on their resources; subscribe to Finding digests |
| `viewer` | Read-only access to Findings and Outcomes in scopes they are mapped to |

Scope is resolved via Tag Lens → BU / Project / Cost Centre.

### 9.3 Approval delivery

- `finops.admin` / `finops.author` publishes a Hypothesis → routed to `finops.approver` group for sign-off.
- Finding → Action transition requires `resource_owner` approval unless the Hypothesis is flagged `auto_apply` AND policy-as-code allows.
- Slack / MS Teams integration delivers approval requests in-line; decisions recorded in the event log.

### 9.4 Audit

Every state transition on any entity writes an immutable audit event with `actor, resource, before, after, ip, ua, request_id`. Retention 2 years.

---

## 10. Tier boundary — what Basic allows, what Advanced requires

| Dimension | Basic | Advanced |
|---|---|---|
| Authoring UI | Wizard (current SPA, upgraded) | Graph editor (new SPA) |
| Signal sources | CSP metrics + billing + K8s + Obs | Everything Basic has + APM + traces + logs + LLM + query history + flow logs + product analytics + CRM + CSP-native advisor streams |
| Aggregations | Whitelisted statistical | Basic + transforms + custom functions |
| Conditions | Threshold / boolean | Threshold + anomaly + seasonality + cross-signal joins + peer comparison |
| Evidence | Metric series + billing row | Metric + billing + trace + log + SKU + workload fingerprint + peer set |
| Savings | Catalog-priced point + simple band | Catalog-priced + realized drift + confidence band + per-BU attribution |
| Actions | 6 types (see §2.3) | Full 14-type vocabulary |
| Shadow mode | Optional (recommended) | Mandatory (≥ 7 days) |
| Backtest | ≥ 30 days, coverage ≥ 90% | ≥ 60 days, coverage ≥ 95%, peer comparison run |
| Owner resolution | Tag / hierarchy / default | Tag / hierarchy / SSO group / CRM account join |
| Runtime | Sync evaluator, per-resource | Async DAG scheduler (signal fetch → transform → join → evaluate) |

---

## 11. Deployment topology

```
                    ┌──────────────────────────────────┐
                    │       Web Clients                │
                    │  ┌──────────┐   ┌────────────┐   │
                    │  │ Basic SPA│   │Advanced SPA│   │
                    │  └────┬─────┘   └──────┬─────┘   │
                    └───────┼────────────────┼─────────┘
                            │                │
                            ▼                ▼
                    ┌──────────────────────────────────┐
                    │      Advisory API (REST + WS)    │
                    └────┬─────────────────────────┬───┘
                         │                         │
         ┌───────────────┴────┐       ┌────────────┴─────────────┐
         ▼                    ▼       ▼                          ▼
  ┌──────────────┐   ┌──────────────┐    ┌──────────────┐   ┌──────────────┐
  │ Basic        │   │ Advanced     │    │ Provider     │   │ Reconciler   │
  │ Evaluator    │   │ Evaluator    │    │ Registry     │   │              │
  │ (sync)       │   │ (DAG sched.) │    │              │   │              │
  └──────┬───────┘   └──────┬───────┘    └──────┬───────┘   └──────┬───────┘
         │                  │                   │                  │
         └──────┬───────────┴───────────┬───────┴─────────┬───────┘
                ▼                       ▼                 ▼
         ┌──────────────┐       ┌──────────────┐   ┌──────────────┐
         │ Signal       │       │ Product      │   │ Billing      │
         │ Catalog      │       │ Catalog      │   │ Streams      │
         │ (ES + warm)  │       │              │   │ (CUR/Exp/BQ) │
         └──────────────┘       └──────────────┘   └──────────────┘
```

---

## 12. Migration plan

### 12.1 From today's SPA to Basic

The existing SPA becomes Basic. Migration is in-place:

1. **Persistence layer**: wizard submits now POST to `Advisory API` → Hypothesis CRUD.
2. **Evaluator**: `Simulate Now` and `Run Now` paths replaced with calls to the Basic Evaluator that reads the actual `ruleGroups` from the Hypothesis.
3. **Integrations tab**: rendered generically from Provider Registry manifests; existing CSP + Obs panels remain the first two entries.
4. **Approval tab**: `approverName` text field replaced by SSO group picker; audit log becomes projection of event log.
5. **Savings**: `savingsPct` field is now computed from Product Catalog at Hypothesis save time; author sees a live estimate instead of typing a string.
6. **Detail panel**: new `Realized Savings` and `Evidence` tabs reading from Outcome and Finding events.

Breaking changes are absorbed by the migration; existing `SAMPLE_RECOMMENDATIONS` are imported as `active` Hypotheses in a one-time script.

### 12.2 Advanced launch

Advanced ships as a separate SPA at `/CXP Optimization/FinOps Advanced Recommendations/` with two top-level surfaces: **Internal Console** (authoring + integrations + backtest) and **Findings Viewer** (end-user list + detail). RBAC enforces which users see which surface.

### 12.3 Sequencing

Phases map to the 24-week roadmap in the Advanced PRD:
- Phase 0 (wks 1–6): shared backbone + Basic upgrades
- Phase 1 (wks 5–12): Provider Registry + Signal Catalog + P0 integrations
- Phase 2 (wks 10–18): Advanced Bands A–B (observability, workload shape)
- Phase 3 (wks 16–24): Advanced Bands C–D (portfolio, business context)

---

## 13. NFRs

| Category | Target |
|---|---|
| **Evaluator latency (Basic)** | p95 ≤ 5 s per Hypothesis × 10k resources |
| **Evaluator latency (Advanced)** | p95 ≤ 60 s per Hypothesis × 10k resources (DAG scheduler parallelism = 8) |
| **Backtest** | 90-day, 10k-resource backtest completes in ≤ 5 minutes |
| **Ingest lag (CSP metrics)** | ≤ 5 minutes from source to Signal Catalog |
| **Ingest lag (billing)** | ≤ 24 hours from CSP export |
| **Product Catalog refresh** | ≤ 24 hours after CSP price change |
| **Reconciler SLA** | Outcome written within 48 h of T+30 window close |
| **Integration health probe** | Fresh within 5 minutes; alerts on 3 consecutive failures |
| **Audit retention** | 2 years immutable; signed hash chain |
| **Multi-tenant isolation** | All queries and actions scoped by tenant_id; zero cross-tenant leakage |
| **API idempotency** | All mutating endpoints accept `Idempotency-Key`; duplicate retries within 24 h are no-op |

---

## 14. Open questions

| # | Question | Blocking? | Owner | Target |
|---|---|---|---|---|
| 1 | Do we standardise on OTel as the preferred APM ingest path, or support vendor-native APIs first? | Yes for Advanced Band A | Platform Eng | 2026-05-10 |
| 2 | Which IaC platform do we generate PRs for first — Terraform, Pulumi, CloudFormation, or Terragrunt-aware? | Yes for Advanced action runtime | Platform Eng | 2026-05-10 |
| 3 | Does FinOps host the Custom Function Runtime, or delegate to a customer-provided webhook? | Yes for Advanced custom transforms | Security + Platform Eng | 2026-05-17 |
| 4 | Reconciler scope — are we comfortable claiming realized savings for actions we didn't apply (e.g., user applied via CSP console)? | No, but affects UX | Product | 2026-05-03 |
| 5 | Commitment orchestrator (C1) — do we operate it autonomously or human-in-the-loop only for v1? | Yes for Band C scope | Product + Platform Eng | 2026-05-24 |

---

*Document version: 1.0 · Platform: FinOps · Product: FinOps · Last updated: 2026-04-20*
