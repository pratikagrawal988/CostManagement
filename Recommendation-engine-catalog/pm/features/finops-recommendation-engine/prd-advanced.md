# PRD — FinOps Advanced Recommendations (Advanced Tier)

## Document Control

| Field | Value |
|---|---|
| **PRD Title** | FinOps Advanced Recommendations — Signal-Fusion Tier |
| **Platform** | FinOps |
| **Product** | FinOps |
| **Sub-Module** | Cost Advisory (Advanced) |
| **Author(s)** | Pratik |
| **Reviewer(s)** | Platform Eng Lead, FinOps PM, Security Lead, Data Eng Lead (TBD) |
| **Status** | Draft |
| **Version** | 1.0 |
| **Created** | 2026-04-20 |
| **Last Updated** | 2026-04-20 |
| **Linked ADO Items** | Pending — to be created post review |
| **Companion docs** | `prd-basic.md`, `docs/architecture/finops-recommendation-engine.md` |

---

## Table of Contents

1. [Problem](#1-problem)
2. [Vision](#2-vision)
3. [Objectives](#3-objectives)
4. [Scope](#4-scope)
5. [User Personas & Access](#5-user-personas--access)
6. [Feature Requirements — the 12 recommendation classes](#6-feature-requirements)
   - 6.A Band A — Observability-driven (A1, A2, A3)
   - 6.B Band B — Workload shape & scheduling (B1, B2, B3)
   - 6.C Band C — Portfolio & commitment orchestration (C1, C2, C3)
   - 6.D Band D — Business-context & unit economics (D1, D2, D3)
7. [Data Requirements & Integration Mapping](#7-data-requirements--integration-mapping)
8. [UI/UX Design — Internal Console + End-User Findings Viewer](#8-uiux-design)
9. [User Journeys](#9-user-journeys)
10. [Acceptance Criteria](#10-acceptance-criteria)
11. [Non-Functional Requirements](#11-non-functional-requirements)
12. [Dependencies & Risks](#12-dependencies--risks)
13. [Rollout & Migration Plan](#13-rollout--migration-plan)
14. [Open Questions](#14-open-questions)
15. [Appendix](#15-appendix)

---

## 1. Problem

The FinOps optimisation market has converged on metric-threshold rules over CSP utilisation data. CSP-native tools (AWS Compute Optimizer, Azure Advisor, GCP Recommender) and SaaS incumbents (Cloudability, Harness CCM, Zesty, Cast.ai, Kubecost) all play in the same shape:
- They sample CSP metrics
- They apply heuristics or ML models
- They emit *"this resource looks under-utilised — shrink it."*

This catches the easy money. Every customer has bought the easy money already. The next dollar of saving is hidden in:
- **Endpoint and trace cost** (which API calls cost what?)
- **Query and warehouse cost** (which Snowflake / BQ queries cost what?)
- **LLM and AI token cost** (which prompt template costs what per customer?)
- **Workload behaviour** (is this steady, bursty, batch, diurnal, seasonal?)
- **Commitment portfolio fit** (do my SPs / RIs / CUDs match my actual burn?)
- **Architecture** (egress, region placement, data transfer)
- **Business unit economics** (cost per customer / feature / transaction)
- **SLO budget** (can I shrink this without breaking the user?)
- **License posture** (am I paying for licenses I already own?)
- **Carbon-aware placement** (can I move workloads to lower-emission regions / hours?)

FinOps today cannot reason about any of these because the existing engine is built on a single-source signal model with whitelisted aggregations. Authors cannot join APM with billing, cannot reference workload classifiers, cannot emit findings that cite trace evidence, cannot propose architecture-level actions.

**This PRD specifies the Advanced tier that closes that gap.** It is a separate engine — separate data fabric, separate authoring surface, separate end-user surface — that *augments* Basic and that prices into the differentiated SKU.

---

## 2. Vision

FinOps Advanced ships **twelve recommendation classes the rest of the market does not have**, organised in four bands. Each class produces findings that cite trace, query-history, billing-line, or workload-fingerprint evidence; that propose typed actions including IaC PRs, commitment purchases, schedule changes, and tier moves; and that close the loop with realized-savings reconciliation against billing.

The product is delivered through a **separate SPA with two surfaces**:
- **Internal Console** — for FinOps's product / ops team (and customer power users) to author Hypotheses, configure Provider Registry integrations, run backtests and shadow-mode reviews, and ship new recommendation classes without code changes.
- **End-User Findings Viewer** — for customer FinOps owners and resource owners to see what was recommended, why (with evidence), what action is proposed, and what realized savings landed.

The internal team gets a graph editor, a backtest workbench, and a confusion matrix. The end user gets a clean, evidence-rich card with an Approve / Snooze / Dismiss decision.

---

## 3. Objectives

- **O1.** Ship 12 recommendation classes (Bands A–D) that no single CSP-native or SaaS competitor ships in one product.
- **O2.** Every Advanced finding carries structured evidence: trace IDs, query fingerprints, billing line refs, SKU snapshots, workload fingerprint classification, peer-comparison set.
- **O3.** Every Advanced finding's action is deliverable through ITSM ticket, IaC PR (Terraform / Pulumi), or human-approved auto-apply with rollback plan.
- **O4.** Every applied action is reconciled against billing at T+30 / T+60 / T+90; SLO regression triggers automatic rollback on auto-apply actions.
- **O5.** A new recommendation class can be authored end-to-end in the Internal Console (signal graph, conditions, action template, savings model, backtest, shadow, activate) **without an engineering release**.
- **O6.** Custom Function Runtime allows customer / FinOps-PM-authored signed transforms (FFT, classifier, custom anomaly) to be referenced in Hypothesis signal graphs.
- **O7.** Internal Console exposes precision / recall / dismissal-reason analytics per Hypothesis, so PMs can prove and improve their recommendations.

---

## 4. Scope

### 4.1 In Scope

**Engine**
- Signal-graph DAG evaluator (per architecture §4.1) supporting:
  - 13 signal categories (CSP metrics, billing, K8s, observability, APM, traces, logs, query history, LLM usage, flow logs, product analytics, CRM, CSP-native advisors)
  - Statistical transforms (FFT, duty-cycle, seasonal-decompose, anomaly-2σ, percentile-vs-baseline, trend-slope, step-change-point)
  - Classifier transforms (workload fingerprint, spot readiness, SLO budget headroom)
  - Attribution transforms (cost-per-label, cost-per-customer, cost-per-feature, token-cost-per-prompt)
  - Architectural transforms (egress graph, commitment burn rate, license utilisation map)
  - Custom Function Runtime (sandboxed JS / Python, signed, versioned)
- Cross-signal joins on canonical keys (`resource_id`, `service.name`, `k8s.pod.name`, `customer_id`, `feature_id`, `query_fingerprint`, `model.name`, `trace.id`)
- Peer comparison and dedupe fingerprinting (anti-noise controls)
- Mandatory shadow mode (≥ 7 days before activation)

**Twelve recommendation classes** (specified in §6 with 5 worked examples each)
- Band A: A1 Cost-per-endpoint, A2 Query-cost, A3 LLM-token-economics
- Band B: B1 Workload-fingerprint, B2 Spot-readiness, B3 Autoscaling-policy
- Band C: C1 Multi-cloud commitment orchestrator, C2 License-BYOB, C3 Egress-architecture
- Band D: D1 Unit economics, D2 SLO-aware rightsizing, D3 Carbon-aware

**Action vocabulary (Advanced-only adds)**
- `CommitmentPurchase`, `SpotMigrate`, `AutoscalingPolicyChange`, `RegionConsolidate`, `LicenseBYOB`, `QueryOptimise`, `ModelRoute`, `EndpointDeprecate`

**Provider Registry — Advanced-tier providers (P1)**
- Datadog, New Relic, Dynatrace, Splunk, OTel collector
- Snowflake, Databricks, BigQuery, Redshift query history
- OpenAI, Anthropic, Bedrock, Vertex AI usage exports
- VPC / NSG / GCP VPC flow logs
- ServiceNow, Jira (ITSM)
- GitHub App, GitLab, Bitbucket (IaC)
- Slack, MS Teams (notification + approval)
- Okta, Azure AD, Ping (identity / SSO)
- Amplitude, Segment, LaunchDarkly, Heap (product analytics)
- Salesforce, HubSpot, Stripe (CRM)
- HashiCorp Vault, AWS Secrets Manager, GCP Secret Manager, Azure Key Vault (secret store)
- AWS Compute Optimizer, Azure Advisor, GCP Recommender, OCI Optimizer (CSP-native streams)

**UI**
- New SPA at `web/CXP Optimization/FinOps Advanced Recommendations/index.html`
- Two top-level surfaces with RBAC-gated visibility:
  - **Internal Console** (signal graph editor, integrations, backtest, shadow, analytics)
  - **End-User Findings Viewer** (findings list, detail, evidence, action approval, outcome)

### 4.2 Out of Scope (this release)

- Fully autonomous AI agent that authors Hypotheses without human curation. Human-in-the-loop authoring is the contract.
- Real-time enforcement (sub-minute reaction). Advanced ships near-real-time evaluation (≤ 5 min) only.
- FinOps-managed IaC apply (we generate PRs; we don't apply them).
- Cross-tenant Hypothesis sharing as a marketplace. Internal Console can publish a Hypothesis to all FinOps tenants only via FinOps-PM-curated catalog.
- Sub-classes of a recommendation type that require dedicated infrastructure (e.g., live database query rewriting through a proxy). v1 ships static recommendations only.

---

## 5. User Personas & Access

### 5.1 Personas applicable to this feature

| Persona | Surface | Capabilities |
|---|---|---|
| **FinOps PM** | Internal Console | Author Hypotheses, configure Provider Registry, manage Custom Functions, view precision/recall analytics, publish to global catalog |
| **FinOps Platform Engineer** | Internal Console | Manage Provider Registry manifests, deploy Custom Functions, set rate-limit budgets, manage Reconciler schedules |
| **FinOps Support** | Internal Console (read-only) | Read all Findings, suppress on customer request with reason code |
| **FinOps Admin (customer)** | Internal Console (limited) + End-User Viewer | Author tenant-scoped Hypotheses; approve any Action; view all Findings |
| **FinOps Author (customer add-on role)** | Internal Console (limited) | Author Hypotheses in scopes they own; cannot publish to global catalog |
| **FinOps Owner (customer)** | End-User Viewer | Approve / snooze / dismiss Findings on owned resources; view Outcomes |
| **Resource Owner (customer eng team)** | End-User Viewer | Approve actions on owned resources; subscribe to Slack/Teams digest |
| **Executive / Viewer (customer)** | End-User Viewer (read-only) | Roll-up dashboards: realized savings, top Findings, regressions |

### 5.2 Persona ↔ Surface matrix

| | Hypothesis authoring | Provider config | Backtest | Shadow review | Findings list | Finding approval | Outcome dashboard |
|---|---|---|---|---|---|---|---|
| FinOps PM | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ |
| FinOps Platform Eng | ✓ | ✓ | ✓ | ✓ | ✓ | — | ✓ |
| FinOps Support | read-only | read-only | read-only | read-only | ✓ + suppress | — | read-only |
| FinOps Admin | tenant-scoped | tenant-scoped | ✓ | ✓ | ✓ | ✓ | ✓ |
| FinOps Author | scope-limited | — | ✓ | scope-limited | scope-limited | — | scope-limited |
| FinOps Owner | — | — | — | — | scope-limited | scope-limited | scope-limited |
| Resource Owner | — | — | — | — | scope-limited | scope-limited | — |
| Executive / Viewer | — | — | — | — | read-only | — | read-only |

---

## 6. Feature Requirements — The 12 Recommendation Classes

Each class is specified in the same six-field structure for consistency:

1. **What it detects** (problem hypothesis in business terms)
2. **Required data points** (canonical signals from the Signal Catalog)
3. **Integrations used** (Provider Registry entries)
4. **What data is extracted** (concrete fields lifted from each integration)
5. **Technical rules** (the signal-graph conditions; reference functions only)
6. **Business rules** (eligibility, owner resolution, SLO/policy gates, suppression)

Followed by **5 different worked examples** showing how the class fires across distinct scenarios.

---

### 6.A Band A — Observability-driven

#### Class A1 — Cost per endpoint / service

**1. What it detects**
APIs whose marginal cost-per-request (compute + DB + egress) is materially out-of-line with peers, growing fast, or cheap-but-extreme-volume. Lets product owners see *which API calls are bleeding money*.

**2. Required data points**
- `apm.service.request.rate` (rps per service / endpoint)
- `apm.service.request.latency_p95` (ms)
- `apm.service.request.error_rate` (%)
- `apm.endpoint.request.count` (per endpoint)
- `apm.span.cpu_time_ms` (per service)
- `billing.resource.cost` (compute, DB, egress per resource_id)
- `k8s.pod.cpu_usage_millicores`, `k8s.pod.memory_usage_bytes` (when service runs on K8s)
- `network.flow.egress_bytes` (per src service)
- Join key: `service.name`, `k8s.pod.name`, `cloud.instance_id`

**3. Integrations used**
- Datadog, New Relic, Dynatrace, OTel collector — APM metrics + spans
- AWS CUR / Azure Cost Export / GCP BQ billing — billing lines
- Kubernetes (in-cluster) + Kubecost — pod-to-resource attribution
- VPC / NSG flow logs — egress attribution

**4. What data is extracted**
- Per service: trace count, P50/P95/P99 latency, error rate, CPU time, span count
- Per service: billing aggregates (compute $, DB $, egress $) joined via `service.name → resource_id` map maintained from K8s + tag annotations
- Trace IDs for the slowest 1% of requests (for evidence binding)
- Peer set: services in same `bu`, same `environment`, similar `request.rate` band

**5. Technical rules** (signal graph)
```
let endpoint_cost_per_call =
  cost_per_label(billing.resource.cost, label=service.name) /
  apm.service.request.rate

let peer_p50 = percentile(endpoint_cost_per_call, 50, peer_set)
let peer_p95 = percentile(endpoint_cost_per_call, 95, peer_set)

emit when:
  (endpoint_cost_per_call > peer_p95 * 3) OR
  (trend_slope(endpoint_cost_per_call, window=90d) > 0.30 / quarter) OR
  (apm.endpoint.request.count > peer_p99 * 5 AND
    endpoint_cost_per_call < peer_p50)   // cheap-but-extreme-volume
```

**6. Business rules**
- Eligibility: service must have ≥ 100 RPS sustained over 14 days (else statistical signal is too noisy).
- Owner resolution: service-name → SSO-group via service catalog (e.g., from Backstage), else fall back to repo `CODEOWNERS`, else `finops.admin`.
- SLO gate: do not propose endpoint deprecation if endpoint is on critical path of an SLO with budget < 50%.
- Suppression: if a deprecation finding was dismissed with reason `business_critical` in last 90 days, suppress unless cost grew further by 50%.

**Worked examples (5)**

| # | Scenario | Trigger | Evidence | Proposed Action | Est. monthly | Realized variance pattern |
|---|---|---|---|---|---|---|
| A1-E1 | E-commerce checkout endpoint cost-per-call is 4× peer average due to N+1 query | `endpoint_cost_per_call > peer_p95 * 3` (4.2× peer P95) | 5 trace IDs showing 47 DB calls per request; CUR rows showing $2,140/d in RDS spend; Datadog APM dashboard link | `QueryOptimise` — propose batching DB calls (Slack approval to backend lead) | $48,200 saved | Realized 88% of estimate within 30 days after fix lands |
| A1-E2 | Search service cost grew 80% QoQ tied to wider result-set in API V2 | `trend_slope > 0.80 / quarter` AND ramp aligns with v2 release tag | 90-day cost vs RPS chart; deploy timestamps; trace samples showing payload size 4× larger | `EndpointDeprecate` — sunset v1 → all callers must migrate to a paged v3 (ITSM ticket to product owner) | $19,800 saved | Realized 60% (v1 retained for legacy enterprise tier) |
| A1-E3 | Payment webhook cost spiked 3σ above baseline tied to retry storm | `anomaly_2sigma(endpoint_cost_per_call, window=24h)` fires; correlates with retry-rate signal | Trace samples showing 12 retries per webhook; CUR cost spike; PagerDuty incident link | `QueryOptimise` — exponential backoff config + idempotency token (auto IaC PR to retry config repo) | $8,600 saved (one-time spike avoided) | Realized 110% — also avoided next month's spike |
| A1-E4 | Reporting export endpoint cost grew 200% QoQ tied to expanded payload | `trend_slope` + `endpoint_cost_per_call > peer_p95 * 3` | Payload size growth chart; 3 trace IDs; CUR egress + compute cost lines | `RightsizeSku` — switch to async export with S3 pre-signed URL pattern (IaC PR to API gateway) | $14,400 saved | Realized 75% — async pattern reduced compute, egress unchanged for first 60 days |
| A1-E5 | Health-check endpoint called 100× peer P99 — propose cache | `apm.endpoint.request.count > peer_p99 * 5 AND endpoint_cost_per_call < peer_p50` | Volume chart; cost-per-call chart; trace sample showing trivial response | `EndpointDeprecate` — add 30s edge cache via CloudFront / Cloudflare (IaC PR) | $2,200 saved (small but high-confidence) | Realized 95% — cache hit-rate 99.6% |

---

#### Class A2 — Query / SQL-level cost

**1. What it detects**
Specific data-warehouse queries (Snowflake / BigQuery / Redshift / Databricks) whose warehouse-time, slot-consumption, or bytes-scanned cost is disproportionate to their value, and that have remediation patterns: materialise, partition, cluster, cache, or warehouse-rightsize.

**2. Required data points**
- `database.query.execution_time_ms`
- `database.query.bytes_scanned`
- `database.query.slot_ms` (BQ) or `warehouse.compute_seconds` (Snowflake / Redshift)
- `database.query.cache_hit` (boolean)
- `database.query.fingerprint` (normalised SQL hash)
- `database.query.user`, `database.query.role`, `database.query.dashboard_id` (when annotated)
- `billing.warehouse.cost` (per warehouse, per day)

**3. Integrations used**
- Snowflake QUERY_HISTORY (via service principal)
- BigQuery INFORMATION_SCHEMA.JOBS
- Redshift STL_QUERY + SVL_QLOG
- Databricks query history API
- BI tools (Looker / Tableau / Power BI / Metabase) via tag annotations on dashboard_id (P2)

**4. What data is extracted**
- Per `query_fingerprint`: count, total cost, avg execution time, cache hit rate, bytes scanned trend
- Per warehouse / project / cluster: cost time-series and utilisation
- Query SQL text (redacted of literal values) for evidence binding
- Schema context: tables and partitions touched

**5. Technical rules**
```
let query_cost = warehouse.cost_per_query_fingerprint(fingerprint, window=30d)
let bytes_per_call = bytes_scanned / call_count
let cache_eligible = cache_hit_rate < 0.10 AND call_count > 50

emit when:
  (query_cost > $5,000 / month) AND
  (bytes_per_call > 1 GB OR cache_eligible OR
   trend_slope(query_cost, 30d) > 0.20 / month)

derive proposed_action ∈ {
  partition_pruning if bytes_scanned_unpruned_pct > 0.50,
  materialise        if call_count > 100 AND result_size < 10 MB,
  cluster_by_key     if range_scan_pct > 0.40,
  cache_reuse        if cache_eligible,
  warehouse_resize   if warehouse.utilisation < 0.40 AND warehouse.bill > $10k/mo,
  auto_suspend       if warehouse.idle_pct > 0.30
}
```

**6. Business rules**
- Eligibility: query must run ≥ 50× over the 30-day window.
- Owner resolution: warehouse owner from Snowflake / BQ permissions; else SQL author from query log; else `finops.admin`.
- Compliance gate: do not surface SQL containing PII tags (data-classification mapping) in evidence; show fingerprint only.
- Suppression: dismissed `compliance_query` reason → suppress for 365 days.

**Worked examples (5)**

| # | Scenario | Trigger | Evidence | Proposed Action | Est. monthly | Realized variance pattern |
|---|---|---|---|---|---|---|
| A2-E1 | Snowflake nightly aggregation scans 4 TB; partition pruning drops to 200 GB | `bytes_per_call > 1 GB AND bytes_scanned_unpruned_pct > 0.50` | Query SQL fingerprint; 30-day cost chart; partition usage breakdown | `QueryOptimise` — add `WHERE event_date >= …` partition predicate (Slack to data-eng) | $7,400 saved | Realized 92% within T+30 |
| A2-E2 | BigQuery marketing dashboard query rerun 200×/day, 0% cache reuse | `cache_hit_rate < 0.10 AND call_count > 50 AND query_cost > $5,000/mo` | Query fingerprint; cache-miss pattern from JOBS; dashboard refresh schedule | `QueryOptimise` — schedule materialised view + 1h refresh (ITSM ticket to BI lead) | $5,800 saved | Realized 70% — Looker still issued ad-hoc variants of the query |
| A2-E3 | Redshift BI tool issues `SELECT *` across all months — should be materialised | `bytes_per_call > 1 GB` + `range_scan_pct > 0.60` | Query fingerprint; 90-day cost; bytes scanned vs returned ratio | `QueryOptimise` — convert to a roll-up table refreshed nightly (Slack approval) | $11,200 saved | Realized 105% — also reduced concurrency contention |
| A2-E4 | Databricks ETL job uses runtime DBR 10 (legacy); upgrade saves slots | Custom `runtime.is_outdated` signal + `cost > $5k/mo` | Cluster runtime config; benchmark of DBR 14 LTS at 22% cheaper for same workload | `RightsizeSku` — bump cluster runtime + re-tune (IaC PR to job config) | $4,400 saved | Realized 80% — DBR 14 ran 18% cheaper, slightly less than benchmark |
| A2-E5 | Snowflake warehouse running 24/7 but only used 8 h — auto-suspend cuts 66% | `warehouse.idle_pct > 0.30 AND warehouse.bill > $10k/mo` | Activity heatmap; idle hours per week; bill | `AutoscalingPolicyChange` — set `AUTO_SUSPEND = 60s, AUTO_RESUME = TRUE` (IaC PR to Terraform) | $9,800 saved | Realized 96% — auto-suspend exactly as predicted |

---

#### Class A3 — LLM / AI token economics

**1. What it detects**
LLM workloads where prompt design, model choice, caching, or batch API would materially reduce token cost without quality regression. Per-customer / per-feature attribution included.

**2. Required data points**
- `llm.prompt.input_tokens`, `llm.prompt.output_tokens`
- `llm.prompt.cost_usd`
- `llm.prompt.latency_ms`
- `llm.prompt.cache_hit` (true / false)
- `llm.prompt.model_name`, `llm.prompt.template_id`
- `llm.prompt.customer_id`, `llm.prompt.feature_id` (from tracing context)
- `llm.eval.quality_score` (when downstream eval pipeline tags responses)

**3. Integrations used**
- OpenAI usage export / API
- Anthropic usage API
- AWS Bedrock CloudWatch metrics + S3 invocation logs
- GCP Vertex AI usage logs + Vertex Pricing
- LangSmith / Helicone / Langfuse (if customer uses an LLM observability tool) — P2

**4. What data is extracted**
- Per `template_id` × `model`: input / output token distributions, cost, latency, cache rate
- Per `customer_id` × `feature_id`: rollups for unit-economic attribution
- Sample prompt fingerprints (hashed) — never raw prompt content
- Quality eval scores for proposed swaps (when available)

**5. Technical rules**
```
let cost_per_call = llm.prompt.cost_usd
let input_size   = llm.prompt.input_tokens

emit when:
  // Oversized prompts
  (input_size > 4000 AND
   trend_slope(input_size, 30d) > 0)  → suggest context_compression

  // Wrong model tier
  (model_name in [opus, gpt-4-turbo] AND
   eval.quality_score(this_template, smaller_model) ≥ 0.95 * eval.quality_score(this_template, current_model))
   → suggest model_route(target=smaller)

  // Batch eligibility
  (latency_p95 > 2 hours allowed_for_template AND
   not_using_batch_api)
   → suggest batch_api_route

  // Cache eligible
  (cache_hit < 0.10 AND
   prompt_prefix_stability > 0.80 over window)
   → suggest prefix_cache

  // Model deprecation
  (model_name in [legacy_model_list])
   → suggest model_route(target=replacement)
```

**6. Business rules**
- Eligibility: template must have ≥ 1,000 calls / week.
- Quality gate: never propose a smaller model unless `eval.quality_score` shadow benchmark is available and ≥ 0.95 of current.
- Owner resolution: feature_id → product owner via product-analytics tagging; else feature-flag owner; else `finops.admin`.
- Compliance gate: prompt content is never extracted to evidence — only fingerprints, sizes, and metadata.

**Worked examples (5)**

| # | Scenario | Trigger | Evidence | Proposed Action | Est. monthly | Realized variance |
|---|---|---|---|---|---|---|
| A3-E1 | OpenAI GPT-4 customer support prompt 8k tokens — context compression to 2k | `input_size > 4000 AND trend > 0` | Token-size histogram; cost chart; sample prompt fingerprint | `ModelRoute` (effectively prompt redesign with context compression) — propose new template (Slack to AI eng) | $11,200 | Realized 82% — compressed prompt was 2.4k, not 2k as planned |
| A3-E2 | Anthropic classifier task using Claude Opus — Haiku ($30→$1) at equal accuracy | `model in [opus]` AND `eval.quality_score(template, haiku) ≥ 0.97 * opus` | Eval benchmark numbers (97% match); cost differential | `ModelRoute(target=haiku)` — IaC PR to model-router config | $9,800 | Realized 99% — exact prediction |
| A3-E3 | Bedrock Llama 3 70B batch prompts not using batch API | `latency_p95 < allowed AND not_using_batch_api` | Latency tolerance profile; current request mode | `ModelRoute(use_batch=true)` — switch SDK call to batch API (Slack approval) | $4,400 | Realized 75% — batch API has different rate limits, throughput slightly lower |
| A3-E4 | Vertex Gemini 1.5 Pro 0% cache hit on stable preamble — enable prefix caching | `prompt_prefix_stability > 0.80 AND cache_hit < 0.10` | Prefix-stability score; cache miss chart | `ModelRoute(use_prefix_cache=true)` — flip API parameter (auto IaC PR) | $6,500 | Realized 100%+ — prefix cache hit 95% |
| A3-E5 | OpenAI Embeddings text-embedding-3-large used; -small is 5× cheaper for same workload | `model in [embedding-3-large]` AND `eval(small) ≥ 0.95 * eval(large)` | Eval benchmark; cost differential | `ModelRoute(target=embedding-3-small)` (with vector-store reindex plan) — ITSM ticket | $13,400 | Realized 60% in T+30, 90% by T+60 (reindex took 5 weeks) |

---

### 6.B Band B — Workload shape & scheduling

#### Class B1 — Workload fingerprint classifier

**1. What it detects**
Classifies every workload as `steady | bursty | batch | diurnal | seasonal` via FFT + duty-cycle analysis. Each class unlocks a different **action catalog** keyed to behaviour. Replaces blunt threshold heuristics like "avg CPU < 40%."

**2. Required data points**
- 30+ days of `compute.vm.cpu_utilisation_pct` at 1-min grain
- `compute.vm.network_egress_bytes_per_sec`
- `compute.vm.disk_io_ops_per_sec`
- `apm.service.request.rate` (when available — improves classifier accuracy)
- `k8s.pod.cpu_usage_millicores` for K8s-hosted workloads
- Calendar context: weekday/weekend, business-hours per timezone

**3. Integrations used**
- All CSP metric APIs (Basic providers)
- Kubernetes (Basic providers)
- APM (Datadog / NR / Dynatrace — Advanced) for traffic-rate signal
- Custom Function Runtime — runs `cf://workload_fingerprint_v2`

**4. What data is extracted**
- Per resource: 30-day FFT spectrum, dominant period, duty-cycle, peak-trough ratio, weekend-vs-weekday delta, business-hours-vs-off-hours delta
- Classification: one of `steady | bursty | batch | diurnal | seasonal | mixed`, with confidence score
- Recommended action template per class

**5. Technical rules**
```
let fingerprint = cf://workload_fingerprint_v2(
  cpu_series = compute.vm.cpu_utilisation_pct(window=30d, granularity=1m),
  rps_series = apm.service.request.rate(window=30d),    // optional
  calendar   = customer_business_calendar
)

// classifier returns: { class, confidence, period_seconds?, duty_cycle?, peak_trough_ratio? }

action_catalog by class:
  steady       → CommitmentPurchase (1y or 3y, full coverage)
  diurnal      → SchedulePause (off-hours), AutoscalingPolicyChange (target tracking)
  bursty       → AutoscalingPolicyChange (target=RPS not CPU), keep on-demand
  batch        → SpotMigrate, SchedulePause
  seasonal     → CommitmentPurchase(baseline) + SpotMigrate(peak)
  mixed        → human review

emit when:
  fingerprint.confidence > 0.70 AND
  current_action_pattern != recommended_action_pattern_for_class
```

**6. Business rules**
- Eligibility: ≥ 30 days of data; gaps < 5%.
- Owner resolution: resource owner via tag inheritance.
- SLO gate: SchedulePause never recommended on workloads tagged `prod`.
- Suppression: classifier confidence < 0.70 → `mixed`; suggest investigation, not action.

**Worked examples (5)**

| # | Scenario | Classification | Trigger | Evidence | Proposed Action | Est. monthly | Realized variance |
|---|---|---|---|---|---|---|---|
| B1-E1 | Stable web tier, 30 days CPU 38–48%, no peaks | `steady`, conf 0.94 | confidence > 0.70 AND no commitment coverage | FFT spectrum (no dominant period); duty-cycle 92% | `CommitmentPurchase` — 1-yr SP for 80% of baseline | $42,300 | Realized 94% — closely matched commitment plan |
| B1-E2 | Report engine, hourly bursts to 80%, baseline 5% | `bursty`, conf 0.88 | confidence > 0.70 AND target-tracking on CPU misconfigured | Burst pattern; current HPA on CPU 70% target | `AutoscalingPolicyChange` — target-tracking on RPS instead of CPU | $8,200 | Realized 85% — RPS metric needed extra config |
| B1-E3 | Nightly ETL, runs 02:00–05:00 UTC daily | `batch`, conf 0.96 | confidence > 0.70 AND on-demand instances | Activity heatmap; duty cycle 12.5% | `SpotMigrate` (workload is fault-tolerant via checkpoint) | $14,800 | Realized 91% — 2 spot interruptions, all recovered |
| B1-E4 | Dev environment, weekday 09:00–18:00 EST | `diurnal`, conf 0.93 | confidence > 0.70 AND no schedule | Heatmap; weekend usage near-zero | `SchedulePause` — stop 18:00–09:00 weekdays + weekends | $19,400 | Realized 88% — some devs worked late, kept some hours |
| B1-E5 | Black Friday infra, baseline + 5×-10× peak Q4 | `seasonal`, conf 0.85 | confidence > 0.70 AND on-demand entire year | 12-month FFT showing yearly period; baseline 200 vCPU, peak 1,800 vCPU | `CommitmentPurchase`(baseline) + `SpotMigrate`(burst) | $312,000 | Realized 78% — actual peak smaller than forecast, savings still large |

---

#### Class B2 — Spot / preemptible readiness score

**1. What it detects**
Workloads ready to move to spot / preemptible instances based on a composite readiness score (interruption tolerance, statelessness, idempotency, queue-backed-ness, fault-tolerance instrumentation). Emits a 0–100 score and a concrete migration plan.

**2. Required data points**
- All `compute.vm.*` and `k8s.pod.*` from B1
- `k8s.workload.has_pdb` (boolean — Pod Disruption Budget present)
- `k8s.workload.has_checkpoint_lib` (signature scan: `torch.distributed.checkpoint`, `keras.callbacks.ModelCheckpoint`, custom)
- `k8s.workload.is_stateless` (no PVC mounts; runs behind LB)
- `apm.service.request.idempotent_pct` (HEAD/GET share + tagged idempotent endpoints)
- `queue.depth` for SQS/PubSub/Service Bus subscribers
- `cloud.spot_market.interruption_rate` (CSP spot pool history)

**3. Integrations used**
- All CSP metric APIs + spot price/interruption history (CSP-native streams)
- Kubernetes (workload manifest scan)
- APM (idempotency tag)
- Cloud queue services (CSP)

**4. What data is extracted**
- Per workload: composite score 0–100 with per-dimension breakdown (interruption, stateless, idempotent, queue-backed, instrumented)
- Spot pool diversification recommendations (instance families × AZ)
- Estimated savings at current spot pricing

**5. Technical rules**
```
let readiness = (
  20 * indicator(has_pdb) +
  15 * indicator(has_checkpoint_lib) +
  20 * indicator(is_stateless) +
  20 * indicator(idempotent_pct > 0.90 OR queue_backed) +
  15 * indicator(workload_class in [batch, bursty]) +
  10 * (1 - normalised(cloud.spot_market.interruption_rate))
)

emit when:
  readiness >= 70 AND
  current_purchase_mode == on_demand AND
  estimated_savings >= $500/month
```

**6. Business rules**
- Eligibility: workload must have ≥ 14 days of stable behaviour.
- SLO gate: never propose spot for workloads tagged `tier-0` or with SLO budget < 30%.
- Diversification rule: action proposal always specifies ≥ 3 instance families across ≥ 2 AZs to reduce concentration risk.
- Owner resolution: Kubernetes namespace owner; else service owner.

**Worked examples (5)**

| # | Scenario | Score | Trigger | Evidence | Proposed Action | Est. monthly | Realized variance |
|---|---|---|---|---|---|---|---|
| B2-E1 | K8s deployment with PDB, checkpoint lib, idempotent HTTP, behind LB | 92 | readiness ≥ 70 AND on-demand AND savings ≥ $500 | PDB present; codebase scan match for `torch.distributed.checkpoint`; APM idempotent_pct 0.96; LB target group | `SpotMigrate` — shift to mixed-pool node group across `m6i.large + m6a.large + m5n.large` × 3 AZs | $6,400 | Realized 90% — 4 interruptions over 30 d, no incident |
| B2-E2 | Stateful PostgreSQL primary | 12 | readiness < 70 — do not emit | n/a | none (suppressed) | n/a | n/a |
| B2-E3 | Async worker reading from SQS with idempotent processor | 88 | readiness ≥ 70 AND queue_backed AND savings ≥ $500 | SQS subscription metrics; idempotency tags from APM | `SpotMigrate` — diversified spot fleet for the worker pool | $3,800 | Realized 96% — queue depth absorbed interruptions cleanly |
| B2-E4 | CI/CD runner pool — bursty, stateless, ephemeral | 95 | readiness ≥ 70 | Workload class = bursty; stateless; checkpointed; idempotent (re-run safe) | `SpotMigrate` — spot fleet with on-demand fallback at 30% capacity | $11,200 | Realized 97% — fallback kicked in twice, total cost still 70% lower |
| B2-E5 | ML training fault-tolerant via Hugging Face checkpoint | 90 | readiness ≥ 70 | Codebase scan; PVC-backed checkpoint dir; trainer config | `SpotMigrate` — A10G spot fleet across regions | $24,000 | Realized 80% — 2 long interruptions added 6 hours to total job time but cost still 4× cheaper |

---

#### Class B3 — Autoscaling-policy optimisation

**1. What it detects**
Misconfigured HPA / KEDA / target-tracking / step-scaling policies that prevent scale-down, cause flapping, or use the wrong metric. Rather than shrink an instance, **rewrite the policy**.

**2. Required data points**
- `k8s.workload.hpa.config` (min, max, target metric, target value, cooldown)
- `k8s.workload.hpa.actual_replicas` time-series
- `k8s.pod.cpu_request_utilisation_pct`, `memory_request_utilisation_pct`
- `apm.service.request.rate`, `queue.depth` (for proposed metric switches)
- `csp.asg.config` and `csp.asg.actual_capacity`

**3. Integrations used**
- Kubernetes (workload manifest scan + replica history)
- KEDA / metrics-adapter for custom metrics
- APM (RPS, latency, queue depth)
- CSP ASG API (DescribeAutoScalingGroups)

**4. What data is extracted**
- Current HPA / ASG config
- Actual replica history vs config bounds
- RPS / queue-depth correlation with scale events
- Suggested new policy as JSON patch

**5. Technical rules**
```
emit when:
  // Pinned-min misconfiguration
  (hpa.min_replicas > p99(actual_replicas, window=14d) * 1.2)
    → propose new min = p99 * 1.1

  // Flapping cooldown
  (count(scale_events, window=1h) > 6 over multiple hours)
    → propose cooldown += 5min

  // Wrong metric for traffic-spike workload
  (workload.class == bursty AND hpa.target_metric == cpu)
    → propose target = rps

  // Missing custom metric on queue-backed worker
  (workload.is_queue_backed AND hpa.target_metric != queue.depth)
    → propose target = queue.depth

  // Step-scaling vs target-tracking choice
  (workload.class == bursty AND policy == target_tracking)
    → propose step-scaling with explicit step thresholds
```

**6. Business rules**
- Eligibility: ≥ 14 days of replica history.
- SLO gate: any policy change must be backtested for SLO impact in shadow before activation.
- Reversibility: every B3 action carries the previous policy as `rollback_plan`.

**Worked examples (5)**

| # | Scenario | Trigger | Evidence | Proposed Action | Est. monthly | Realized variance |
|---|---|---|---|---|---|---|---|
| B3-E1 | HPA pinned at min=10, actual replicas never below 7 | `hpa.min > p99(actual) * 1.2` | Replica time-series; HPA YAML | `AutoscalingPolicyChange` — set min=2 (IaC PR to manifest) | $4,800 | Realized 88% — actual min dropped to 3 over time |
| B3-E2 | KEDA scaler with no cooldown causing flapping | `count(scale_events, 1h) > 6` over 5 hours/day | Scale event log; CPU oscillation | `AutoscalingPolicyChange` — add 5 min cooldown (IaC PR) | $1,400 | Realized 102% — also reduced LB churn cost |
| B3-E3 | ASG using avg CPU 70% target on bursty workload | workload.class == bursty AND policy_target == cpu | RPS leads CPU by 40 s; ASG history | `AutoscalingPolicyChange` — switch to RPS target via custom CW metric | $3,600 | Realized 78% — better throughput, slightly less savings than estimate |
| B3-E4 | K8s HPA on SQS-backed worker without queue-depth metric | workload.is_queue_backed AND hpa.target_metric != queue.depth | SQS depth time-series; current HPA YAML | `AutoscalingPolicyChange` — add KEDA SQS scaler (IaC PR) | $2,200 | Realized 92% |
| B3-E5 | ECS service with target-tracking CPU 50% on bursty pattern | workload.class == bursty AND policy == target_tracking | Replica/CPU oscillation; cold-start latency | `AutoscalingPolicyChange` — switch to step-scaling with explicit upper thresholds | $5,800 | Realized 90% — cold-start incidents reduced as side benefit |

---

### 6.C Band C — Portfolio & commitment orchestration

#### Class C1 — Multi-cloud commitment orchestrator

**1. What it detects**
Whole-portfolio optimisation of RI / SP / CUD / reservation coverage across CSPs. Detects expiring commitments, mismatched mix (Compute SPs vs EC2 SPs), under-coverage on stable spend, over-coverage on shrinking spend, convertible RI mis-allocation, and suggests laddered purchase plans.

**2. Required data points**
- `billing.commitment.coverage_pct` per CSP × instance-family × region × OS
- `billing.commitment.expiration_date` (per active commitment)
- `billing.commitment.upfront_paid` and `effective_rate`
- `billing.on_demand.spend` (uncovered spend)
- `commitment.burn_rate.monthly`
- `compute.usage.steady_baseline` (from B1 fingerprints aggregated across resources)
- CSP commitment marketplace prices (current SP/RI/CUD rates)

**3. Integrations used**
- AWS CUR (commitments + usage)
- Azure Cost Export (RIs + SPs)
- GCP BQ billing (CUDs)
- OCI usage report (Universal Credits)
- CSP-native: AWS Cost Explorer SP recommender, Azure RI recommender, GCP CUD analyzer

**4. What data is extracted**
- 12-month historical commitment ledger
- 12-month projected on-demand burn (per family/region)
- Optimal-coverage curve from a linear-program solver run by `cf://commitment_optimiser_v3`
- Expiring commitments list with rebuy plan

**5. Technical rules**
```
let coverage = billing.commitment.coverage_pct
let baseline = compute.usage.steady_baseline(window=90d)

emit when:
  // Under-coverage on stable spend
  (coverage < 0.50 AND baseline > $X / month) → propose CommitmentPurchase(plan = ladder)

  // Expiring within 60 d unrebuyable today
  (commitment.days_to_expiry < 60 AND auto_rebuy_disabled) → propose CommitmentPurchase(plan = rebuy)

  // Convertible RI on superseded family
  (RI.type == convertible AND family.is_superseded) → propose Convert(target = current_family)

  // SP mix wrong
  (compute_SP.coverage_pct < EC2_SP.opportunity) → propose ReallocateSP

  // Overcoverage on shrinking spend
  (coverage > 1.05 AND trend_slope(usage) < -0.20 / quarter) → propose Modify(reduce)
```

**6. Business rules**
- Eligibility: tenant must have ≥ 6 months of billing history.
- Approval: `CommitmentPurchase` is **never** auto-applied. Always routed to `finops.admin` or named approver group.
- Risk: max single-purchase commit cannot exceed 30% of tenant's monthly cloud spend without dual approval.
- Owner resolution: tenant FinOps Admin always approves; resource-owner not required.

**Worked examples (5)**

| # | Scenario | Trigger | Evidence | Proposed Action | Est. annual | Realized variance |
|---|---|---|---|---|---|---|
| C1-E1 | Customer holds AWS SPs + Azure RIs separately; combined portfolio ladder saves 12% | LP solver shows 12% improvement vs current allocation | LP output; current portfolio; recommended schedule | `CommitmentPurchase` × 4 staged purchases over 60 days (ITSM ticket per purchase) | $1.2M / yr | Realized 88% — one tranche delayed past optimal window |
| C1-E2 | Expiring 1-yr CUD on GCP unnoticed | `days_to_expiry < 60 AND auto_rebuy_disabled` | Expiration alert; usage continues at same rate | `CommitmentPurchase` — auto-rebuy 1-yr CUD (ITSM ticket) | $84k / yr | Realized 96% — rebuy executed in time |
| C1-E3 | Convertible RIs on EC2 family `c4` (superseded by `c6i`) | `RI.type == convertible AND family.is_superseded` | RI inventory; current usage on c6i (uncovered) | `CommitmentPurchase` — Convert c4→c6i convertible (no incremental spend) | $216k / yr | Realized 100% — paper transaction, exact savings |
| C1-E4 | SP coverage 60% but on-demand spend on uncovered family is 3× covered | uncovered spend on family X / covered ≥ 3 | Per-family coverage; on-demand burn | `CommitmentPurchase` — Compute SP shift to cover family X | $145k / yr | Realized 91% — usage shifted slightly mid-month |
| C1-E5 | Spot pool concentrated in single AZ — diversification reduces interruption | spot_pool.azs ≤ 1 AND interruption_rate > tolerance | Pool composition; interruption history | `SpotMigrate` (re-allocation) — diversify across 3 AZs and 4 instance families | $24k / yr (savings retained while interruption falls) | Realized 110% — fewer interruptions translated to less retry overhead |

---

#### Class C2 — License BYOB / Hybrid Benefit

**1. What it detects**
Resources running OS / database licenses that the customer already owns (on-prem or unused cloud) but is paying CSP for. Plus drift in software-asset-management (SAM) compliance.

**2. Required data points**
- CSP: instance OS, database engine, license_model field per resource
- `billing.line_item.usage_type` (e.g., `BoxUsage:m5.xlarge` vs `BoxUsage:m5.xlarge:SQL`)
- Customer SAM inventory: on-prem license entitlements (CSV upload or SAM tool integration)
- `azure.hybrid_benefit_eligible` per VM
- `aws.license_manager` license-utilisation snapshots

**3. Integrations used**
- All CSPs (Basic providers for resource attributes)
- AWS License Manager (P1)
- Azure Cost Management (Hybrid Benefit eligibility flag)
- Customer SAM tool (Flexera / ServiceNow SAM / Snow) — P2; CSV upload as fallback

**4. What data is extracted**
- Inventory of OS / DB / app licenses per resource
- SAM entitlement vs cloud usage
- Per-resource Hybrid Benefit / BYOL eligibility

**5. Technical rules**
```
emit when:
  (resource.license_model == license_included AND
   sam.entitlement[product, edition].available > 0)
   → propose LicenseBYOB(target_program)

  (azure.vm.hybrid_benefit_enabled == false AND
   sam.entitlement[windows_server, datacenter].available > 0)
   → propose LicenseBYOB(azure_hybrid_benefit)

  (aws.rds.engine == oracle AND
   sam.entitlement[oracle_db_ee].ula_active)
   → propose LicenseBYOB(byol)
```

**6. Business rules**
- Eligibility: SAM inventory must be loaded and dated within last 90 days; otherwise emit a `data_freshness_required` finding instead.
- Compliance gate: Oracle BYOL requires legal attestation; finding routed to `legal.approver` group.
- Reversibility: every BYOB action records the original license-model in case of rollback.

**Worked examples (5)**

| # | Scenario | Trigger | Evidence | Proposed Action | Est. annual | Realized variance |
|---|---|---|---|---|---|---|
| C2-E1 | SQL Server VMs on Azure not enabled for AHB | `hybrid_benefit_enabled == false AND sam.windows_dc.available > 0` | VM inventory; SAM entitlement; eligibility check | `LicenseBYOB(azure_hybrid_benefit)` — toggle on 42 VMs (IaC PR) | $186k / yr | Realized 99% — direct API toggle |
| C2-E2 | RHEL on AWS, customer has unused on-prem subs | `aws.usage_type contains RHEL AND sam.rhel_subscriptions.available > 0` | Subscription matrix; AWS BYOL marketplace AMI | `LicenseBYOB(byol)` — switch to BYOL AMI for 18 VMs (ITSM) | $34k / yr | Realized 80% — some VMs needed full reprovision, retained subscription cost briefly |
| C2-E3 | Windows Server on GCP sole-tenant eligible for BYOL | `gcp.os == windows_server AND gcp.sole_tenant == true AND sam.windows_dc.available > 0` | Sole-tenant config; SAM entitlement | `LicenseBYOB` — enable BYOL on sole-tenant node group (IaC PR) | $42k / yr | Realized 95% |
| C2-E4 | Oracle DB on AWS RDS-Oracle: switch to BYOL with on-prem ULA | `aws.rds.engine == oracle AND license_model == license_included AND ula_active` | ULA terms; RDS resources | `LicenseBYOB(byol)` — convert RDS to BYOL (legal approval required) | $312k / yr | Realized 70% — ULA terms restricted some workloads |
| C2-E5 | Customer has unused 200 SQL Server cores in SAM — apply to dev fleet | `sam.entitlement[sql_server].available - in_use > 200` | Available pool; uncovered dev fleet license_model | `LicenseBYOB(azure_hybrid_benefit)` on 200 cores in dev | $94k / yr | Realized 100% |

---

#### Class C3 — Egress & data-transfer architecture

**1. What it detects**
Cross-AZ, cross-region, and cross-cloud data transfer that drives outsized egress charges. Recommends PrivateLink / VPC peering / CDN offload / region consolidation / batch compaction / topology-aware routing.

**2. Required data points**
- `network.flow.egress_bytes` from VPC / NSG / GCP VPC flow logs (per `(src_account, dst_account, src_region, dst_region, src_az, dst_az)`)
- `billing.line_item.usage_type` for `*-DataTransfer-*` / `Bandwidth-*`
- Resource topology (which workload owns the source IP / NIC)
- DNS query patterns (where is data going)
- CDN hit/miss metrics (Cloudfront, Cloudflare, Akamai) when present

**3. Integrations used**
- AWS VPC Flow Logs (S3 export)
- Azure NSG Flow Logs (Storage Account export)
- GCP VPC Flow Logs (BigQuery export)
- CSP billing for transfer line items
- CDN providers (P2)

**4. What data is extracted**
- Top-N byte flows by `(src_service, dst_service, region_pair)`
- Per-flow cost attribution (joining flow log bytes to billing rates)
- Architecture pattern detection (cross-AZ replication, cross-region replication, public-IP-when-private-link-eligible, NAT GW abuse, cold-data CDN miss)

**5. Technical rules**
```
let flow_cost = network.flow.egress_bytes × csp_egress_rate(src_region, dst_region)

emit when:
  // Cross-AZ when Private Link eligible
  (flow.src_az != flow.dst_az AND service.privatelink_eligible AND flow_cost > $500/mo)
    → propose RegionConsolidate(use_privatelink)

  // Cross-region replication unnecessary
  (flow.src_region != flow.dst_region AND replication_can_use_async_or_be_consolidated)
    → propose RegionConsolidate

  // CDN miss on static assets
  (cdn_miss_rate > 0.40 AND egress_bytes_origin > $1000/mo)
    → propose RegionConsolidate(add_cdn_cache_headers)

  // K8s pod-to-pod cross-AZ at high volume
  (k8s_pod.cross_az_traffic_mbps > 50 AND topology_aware_routing == off)
    → propose AutoscalingPolicyChange(enable_topology_aware_routing)

  // Cross-cloud egress for shared service
  (src_csp != dst_csp AND service.is_internal)
    → propose RegionConsolidate(co-locate)
```

**6. Business rules**
- Eligibility: ≥ 14 days of flow log data.
- Owner resolution: source workload owner (resource → tag → SSO group).
- Action proposals carry detailed migration runbook references; nothing in C3 is auto-applied.

**Worked examples (5)**

| # | Scenario | Trigger | Evidence | Proposed Action | Est. monthly | Realized variance |
|---|---|---|---|---|---|---|---|
| C3-E1 | Stateful service replica cross-AZ traffic 4 TB/mo via NAT GW | cross-AZ + service.privatelink_eligible + cost > $500 | Flow log top flow; NAT GW bill line | `RegionConsolidate(use_privatelink)` — provision PrivateLink endpoint (IaC PR) | $4,800 | Realized 92% |
| C3-E2 | CloudWatch logs to cross-region S3 bucket | flow.src_region != flow.dst_region + service is logging | Flow log volume; CW destination config | `RegionConsolidate` — VPC interface endpoint + same-region S3 bucket (IaC PR) | $2,100 | Realized 100% |
| C3-E3 | CDN miss rate 60% on static assets | cdn_miss_rate > 0.40 AND origin egress > $1000/mo | CDN dashboard; cache-control headers (missing) | `RegionConsolidate(add_cdn_cache_headers)` — Cache-Control + ETag (IaC PR to web app) | $5,400 | Realized 75% — some asset versions still busted cache |
| C3-E4 | K8s pod-to-pod cross-AZ at 5 GB/min | k8s_pod.cross_az_mbps > 50 AND topology_aware == off | Flow log; K8s topology config | `AutoscalingPolicyChange(enable_topology_aware_routing)` — service annotation (IaC PR) | $3,200 | Realized 88% — some traffic still cross-AZ for HA |
| C3-E5 | Cross-cloud egress AWS→Azure for internal shared service | src_csp != dst_csp AND service.is_internal | Flow log; transfer cost line items | `RegionConsolidate(co-locate)` — move shared service to Azure side (architecture review + IaC PR) | $14,800 | Realized 65% — co-location took 2 quarters; T+90 only captured partial benefit |

---

### 6.D Band D — Business-context & unit economics

#### Class D1 — Cost per customer / feature / transaction

**1. What it detects**
Workloads where unit cost (per customer, per feature, per transaction) is out of line with revenue, growing untracked, or signalling a margin inversion. The CFO's question.

**2. Required data points**
- `billing.resource.cost` (with full tag enrichment)
- `product_analytics.event` (tenant_id, user_id, feature_id, event_type)
- `crm.account.arr` (annual recurring revenue per tenant)
- `crm.account.product_tier`
- `apm.service.request.customer_id` (extracted from headers / span attributes)
- `feature_flag.evaluation` (LaunchDarkly / Optimizely)

**3. Integrations used**
- Amplitude / Segment / Heap / Mixpanel — product events
- LaunchDarkly / Statsig — feature evaluations
- Salesforce / HubSpot / Stripe — ARR + tier
- Datadog / NR / Dynatrace — span attributes for customer_id
- All CSP billing (Basic providers)

**4. What data is extracted**
- Per `(tenant_id, feature_id)`: cost rollup using `cost_per_label` on cost-attribution tags
- Per tenant: cost-per-MAU, cost-as-percent-of-ARR, margin
- Per feature: incremental cost since flag turned on, cost-per-feature-user
- Per transaction (if customer instruments transaction count): cost-per-transaction by type

**5. Technical rules**
```
let cost_per_active_user = sum(billing.resource.cost, by=tenant_id) /
                           count_distinct(product_analytics.event.user_id, by=tenant_id)

let margin = (crm.account.arr / 12 - cost_per_tenant) / (crm.account.arr / 12)

emit when:
  // Margin inversion
  (margin < 0)
    → propose finding(severity=critical, alert=cfo_dashboard, action=human_review)

  // Cost-per-user 3σ above peer cohort
  (cost_per_active_user > peer_cohort.p95 * 3 within product_tier)
    → propose finding(action=feature_team_review)

  // Feature post-launch cost spike
  (feature_flag.cost_attributable_to_flag > 0.30 * total_cost AND
   feature.user_pct < 0.10)
    → propose finding(action=feature_team_review)

  // Per-transaction cost out of band
  (cost_per_transaction[type] > peer.p95 * 2)
    → propose finding(action=architecture_review)
```

**6. Business rules**
- Eligibility: cost-attribution tag coverage ≥ 75%; otherwise emit `tag_coverage_required`.
- Owner resolution: feature owner from product analytics; tenant owner from CRM.
- D1 findings rarely propose typed actions — they are evidence packages routed to product / engineering for human review. The action vocabulary is `human_review` with structured payload.
- Compliance gate: redact tenant names in cross-FinOps-team views unless viewer is `finops.admin`.

**Worked examples (5)**

| # | Scenario | Trigger | Evidence | Proposed Action | Business outcome | Realized variance |
|---|---|---|---|---|---|---|
| D1-E1 | SaaS tenant T-1234 cost-per-MAU $0.42 vs $0.08 peer | `cost_per_active_user > peer_cohort.p95 * 3` | Tenant tier (Pro); MAU; cost rollup; peer histogram | `human_review` — surface to tenant CSM for plan upgrade conversation OR architectural fix | $240k ARR re-tier | Realized as commercial outcome — not in billing reconciler |
| D1-E2 | New "AI assistant" feature added 30% to compute spend, used by 4% of users | `feature_flag.cost_attributable > 0.30 AND feature.user_pct < 0.10` | LaunchDarkly evaluation count; deploy timestamp; cost spike | `human_review` — flag to product manager: monetise, restrict, or kill | $182k / yr saved (feature gated to Enterprise) | Realized 100% (gated post launch) |
| D1-E3 | Free-tier customers cost 80% of compute spend | by-tier rollup shows free_tier.cost / total > 0.80 | Tier breakdown; compute usage by tier | `human_review` — tighten free quotas (rate limits, retention) | $96k / yr | Realized 60% (some quotas softened after user backlash) |
| D1-E4 | Per-transaction cost for international wire 4× domestic | `cost_per_transaction[wire_intl] > peer.p95 * 2` | Transaction-type cost rollup; provider mix | `human_review` — propose secondary acquirer for international traffic | $48k / yr | Realized as commercial restructuring |
| D1-E5 | Self-serve cost-per-MAU steady; enterprise cost-per-MAU growing 8% MoM | `trend_slope(cost_per_user, by=tier) > 0` over 3 months for enterprise | Tier-segmented cost-per-MAU chart | `human_review` — investigate which Enterprise feature drives growth | n/a (investigation) | Action class — directs RCA, not direct savings |

---

#### Class D2 — SLO-aware rightsizing

**1. What it detects**
Rightsizing opportunities filtered by SLO budget — refuses to propose downsizing if the workload is inside its error budget or near its latency SLO. Cites the SLI directly in evidence.

**2. Required data points**
- All `compute.vm.*` and `k8s.pod.*` from B1
- `apm.service.request.latency_p95`, `latency_p99`, `error_rate`
- `slo.budget.remaining` (from SLO definitions)
- `slo.target.latency_p95_ms`, `slo.target.error_rate_pct`

**3. Integrations used**
- All CSP metric APIs + Kubernetes (Basic)
- APM (Datadog / NR / Dynatrace) — latency, error rate
- SLO platforms (Nobl9, Datadog SLO, Grafana SLO) — P2; otherwise tag-defined SLOs in the customer's catalog

**4. What data is extracted**
- Per resource: utilisation distribution + SLO budget snapshot
- Recommended target SKU bounded by a "would still meet SLO" simulation
- SLI evidence directly attached to the finding

**5. Technical rules**
```
let target_sku = catalog.smallest_sku_meeting(
  cpu_p95 * 1.2,
  memory_p95 * 1.2
)

let slo_headroom = (
  slo.target.latency_p95_ms / apm.latency_p95 - 1,
  slo.target.error_rate_pct / apm.error_rate - 1,
  slo.budget.remaining
)

emit when:
  (cpu_utilisation_p95 < 0.40 AND memory_p95 < 0.40 AND
   slo_headroom.latency > 0.30 AND
   slo_headroom.error_budget > 0.50 AND
   target_sku is not null)
    → propose RightsizeSku(target_sku)

suppress when:
  (slo.budget.remaining < 0.30) OR
  (latency_p95 > slo.target.latency_p95_ms * 0.85)
```

**6. Business rules**
- Eligibility: SLO must be defined for the service (tag or platform).
- SLO gate (mandatory): suppress if budget < 30% or if P95 already > 85% of target.
- Owner resolution: SRE / service owner.

**Worked examples (5)**

| # | Scenario | Trigger / Suppression | Evidence | Proposed Action | Est. monthly | Realized variance |
|---|---|---|---|---|---|---|
| D2-E1 | RDS CPU 22% but P99 query latency 950 ms vs SLO 1000 ms | suppressed: latency > 0.85 × SLO target | latency chart; SLO config | none — emit `slo_constrained` notice | n/a | Correct refusal: avoided breach |
| D2-E2 | EC2 fleet CPU 35% AND P95 latency 250 ms vs SLO 800 ms | trigger fires | utilisation; SLI; slo_headroom 220% | `RightsizeSku` — m6i.xlarge → m6i.large | $4,200 | Realized 91% |
| D2-E3 | DB at memory 60% but cache hit rate 99.4% (SLO N/A) | trigger fires (no SLO constraint) | utilisation; cache stats | `RightsizeSku` — db.r5.large → db.r5.medium | $2,600 | Realized 95% |
| D2-E4 | K8s pod under-utilised, error rate within budget | trigger fires | request util; error budget remaining 78% | `RightsizeSku` — pod request reduction | $1,800 | Realized 88% |
| D2-E5 | Lambda P99 cold-start 2.1s vs SLO 3s | trigger fires | utilisation; cold-start histogram | `RightsizeSku` — memory cut + provisioned concurrency 5 | $1,200 (memory) − $420 (PC) = $780 net | Realized 85% — provisioned concurrency cost slightly higher than estimated |

---

#### Class D3 — Carbon & regional sustainability

**1. What it detects**
Workloads where region or schedule changes reduce gCO₂e per workload-hour without breaking data residency. Emerging procurement requirement for enterprise FinOps.

**2. Required data points**
- `billing.resource.cost` per region
- `compute.vm.utilisation` per region
- CSP carbon APIs: `aws.carbon.gco2e_per_kwh`, `azure.emissions`, `gcp.carbon_footprint`
- Regional electricity-mix data (e.g., Electricity Maps API)
- Workload data residency / latency requirements (tag-defined)
- Workload class (from B1) — batch / steady / diurnal

**3. Integrations used**
- AWS Customer Carbon Footprint Tool (CCFT)
- Azure Emissions Impact Dashboard
- GCP Carbon Footprint
- Electricity Maps (optional, P2)
- All CSP billing + metric APIs

**4. What data is extracted**
- Per region: gCO₂e/kWh, embodied carbon
- Per resource: emissions snapshot, alternative-region emissions, data-residency tag
- Per batch workload: optimal-renewable-hour schedule

**5. Technical rules**
```
emit when:
  // Region move feasible
  (resource.data_residency in [null, "any", explicit_set_including_target]) AND
  (alt_region.gco2e < current_region.gco2e * 0.60) AND
  (latency_to_users[alt_region] - latency_to_users[current] < 50 ms)
    → propose RegionConsolidate(target = alt_region)

  // Schedule shift for batch
  (workload.class == batch AND
   target_renewable_hours.gco2e < current_run_window.gco2e * 0.50)
    → propose SchedulePause(shift_to = target_renewable_hours)

  // Storage tier embodied-carbon
  (storage.last_access_days > 90 AND tier > coldest_acceptable)
    → propose TierMove(target = colder_tier)
```

**6. Business rules**
- Eligibility: data residency tag must be present (or explicit `any`); else suppress with `data_residency_unknown`.
- Owner resolution: workload owner; some D3 actions also require legal/compliance approval (`compliance.approver` group).
- Co-benefit: most D3 actions also reduce cost — savings reported in $ AND gCO₂e.

**Worked examples (5)**

| # | Scenario | Trigger | Evidence | Proposed Action | Est. impact | Realized variance |
|---|---|---|---|---|---|---|
| D3-E1 | Workload in us-east-1 (455 g/kWh), data residency US-only — move to us-west-2 (255) | alt_region.gco2e < current * 0.60 AND residency permits | Carbon API readings; latency Δ < 20 ms | `RegionConsolidate` — move 12 VMs (IaC PR) | -44% emissions, $0 cost change | Realized 95% emissions; $1,200 NET savings (network rebate) |
| D3-E2 | Batch job runs 24/7 — schedule for renewable peak hours | workload.class == batch AND alt_window.gco2e < 0.50 | Daily carbon-intensity curve; job duration 4h | `SchedulePause` — schedule daily 02:00–06:00 (Cleanest 4h window) | -38% emissions | Realized 90% — small drift due to timezone DST |
| D3-E3 | Multi-region active-active where data residency permits single region | data_residency permits AND alt is single region | Topology; residency tags; load balancing setup | `RegionConsolidate` — collapse to single region (architecture review + IaC PR) | -52% emissions, $86k / yr saved | Realized 70% — kept active-active for some tier-0 services |
| D3-E4 | ML training in eu-west-1 (Ireland 290 g/kWh); propose Stockholm (40 g/kWh) | alt_region < 60% AND residency = EU | Carbon readings; latency to data tier | `RegionConsolidate` — migrate training cluster (IaC PR) | -86% emissions | Realized 100% emissions; cost +5% (Stockholm slightly pricier) |
| D3-E5 | Storage tier in Standard with 6-month-old data — Glacier cuts cost AND embodied carbon | last_access_days > 90 AND tier == standard | Access pattern; tier policy | `TierMove` — lifecycle to Glacier IR (auto IaC PR) | -22% storage cost; -35% embodied carbon estimate | Realized 100% on cost; emissions modelled (no direct realized signal) |

---

## 7. Data Requirements & Integration Mapping

### 7.1 Per-band integration matrix

| Band | Class | Required integrations (P0 must-have) | Optional (improves accuracy) |
|---|---|---|---|
| A | A1 Cost-per-endpoint | APM (Datadog **OR** NR **OR** Dynatrace **OR** OTel) + CSP billing + K8s | Service catalog (Backstage) for owner mapping |
| A | A2 Query cost | Snowflake / BigQuery / Redshift / Databricks query history | BI tool annotations (Looker / Tableau) |
| A | A3 LLM tokens | OpenAI / Anthropic / Bedrock / Vertex usage exports | LangSmith / Helicone / Langfuse (eval scores) |
| B | B1 Workload fingerprint | CSP metric APIs + 30 d history | APM (improves traffic-rate signal); Custom Function Runtime |
| B | B2 Spot readiness | CSP metric APIs + K8s manifests + spot pool history | Codebase scanner (signature for checkpoint libs) |
| B | B3 Autoscaling policy | K8s API + KEDA + APM | CSP ASG API |
| C | C1 Commitment orchestrator | All CSP billing + commitment ledger | Custom Function Runtime (LP solver) |
| C | C2 License BYOB | All CSPs + customer SAM upload | AWS License Manager / Flexera / Snow |
| C | C3 Egress architecture | VPC / NSG / GCP flow logs + CSP billing | CDN provider (Cloudflare / Cloudfront) |
| D | D1 Unit economics | Billing + Tag Lens + Product analytics + CRM | LaunchDarkly + APM with customer_id |
| D | D2 SLO-aware | APM + SLO platform OR tag-defined SLO | Nobl9 / Datadog SLO |
| D | D3 Carbon | CSP carbon APIs + billing + metric APIs | Electricity Maps |

### 7.2 Per-integration onboarding parameters (Provider Registry manifests)

| Integration | Auth | Required parameters |
|---|---|---|
| Datadog | api_key_pair | `site` (us1/us3/us5/eu1/ap1), `api_key` (secret), `app_key` (secret), `service_filter`, `metric_scope`, `rate_limit_budget_per_min` |
| New Relic | user_api_key | `account_id`, `region` (US/EU), `user_api_key` (secret), `ingest_key` (secret), `entity_guid_filter` |
| Dynatrace | oauth OR api_token | `environment_url` (mycluster.live.dynatrace.com), `api_token` (secret, scopes: metrics.read, entities.read), `management_zone` |
| OpenTelemetry collector | otlp + bearer / mTLS | `otlp_endpoint`, `auth_method`, `bearer_token` *or* `client_cert` + `client_key`, `resource_attributes_allowlist`, `sampling_policy` |
| Splunk Observability | api_token | `realm` (us0/us1/eu0/jp0), `api_token` (secret), `service_filter` |
| Snowflake | service_account + key_pair | `account_url`, `warehouse`, `role`, `service_principal`, `private_key` (secret), `query_history_retention_days` |
| BigQuery | service_account / WIF | `project_id`, `dataset_id`, `sa_email`, `key_or_wif_provider`, `dataset_location` |
| Redshift | iam role / db_user | `cluster_id`, `db_user`, `db_name`, `secret_arn`, `region` |
| Databricks | pat / spn | `workspace_url`, `pat_token` (secret) *or* `spn_client_id`+`secret`, `cluster_filter` |
| OpenAI | api_key | `api_key` (secret), `org_id`, `usage_export_s3` *or* `usage_api_endpoint`, `model_allowlist`, `tokenizer_version` |
| Anthropic | api_key | `api_key` (secret), `org_id`, `usage_endpoint` |
| Bedrock | iam_role | `role_arn`, `external_id`, `regions[]`, `cw_log_group`, `s3_invocation_log_bucket` |
| Vertex AI | service_account / WIF | `project_id`, `sa_email`, `key_or_wif_provider`, `location_filter` |
| AWS VPC Flow Logs | iam_role + s3 | `role_arn`, `external_id`, `flow_log_bucket`, `log_format_version`, `parser_config`, `retention_days`, `aggregation_window` |
| Azure NSG Flow Logs | spn + storage | `tenant_id`, `client_id`, `client_secret` (secret), `storage_account`, `container`, `version` |
| GCP VPC Flow Logs | sa + bigquery | `project_id`, `dataset_id`, `table_id`, `sa_email`, `key_or_wif_provider` |
| ServiceNow | oauth | `instance_url`, `oauth_client_id`+`secret` (secret), `default_assignment_group`, `template_sys_id`, `field_map` |
| Jira | pat / oauth | `site_url`, `pat` (secret), `default_project`, `default_assignee`, `field_map` |
| GitHub | github_app | `org_or_user`, `repo_allowlist`, `installation_id`, `private_key` (secret), `path_map`, `pr_assignees`, `review_policy` |
| GitLab | oauth | `instance_url`, `oauth_app_id`+`secret`, `group_allowlist`, `path_map`, `mr_assignees` |
| Bitbucket | app_password | `workspace`, `username`, `app_password` (secret), `repo_allowlist` |
| Slack | bot_token | `workspace_id`, `bot_token` (secret), `default_channel`, `approver_group_mapping`, `digest_schedule` |
| MS Teams | webhook + bot | `tenant_id`, `app_id`, `app_secret` (secret), `default_team_id`, `approver_group_mapping` |
| Okta | oidc + scim | `issuer_url`, `client_id`+`secret`, `scim_endpoint`+`token` (secret), `group_claim`, `mfa_enforcement` |
| Azure AD | oidc + msgraph | `tenant_id`, `client_id`+`secret`, `graph_scope`, `group_filter` |
| Ping | oidc + scim | `issuer_url`, `client_id`+`secret`, `scim_endpoint`+`token` (secret) |
| Amplitude | api_key | `api_key`+`secret_key` (secret), `event_schema_map` (`{user_id, tenant_id, feature_id} → tag.*`), `export_frequency` |
| Segment | api_token | `workspace_slug`, `personal_access_token` (secret), `source_filter`, `event_filter` |
| LaunchDarkly | api_key | `api_key` (secret), `environment_keys[]`, `flag_filter` |
| Heap | api_key | `app_id`, `api_key` (secret) |
| Salesforce | oauth | `instance_url`, `oauth_client_id`+`secret`, `account_match_key` (`domain`/`external_id`), `refresh_cadence` |
| HubSpot | oauth | `portal_id`, `oauth_client_id`+`secret`, `pipeline_filter` |
| Stripe | api_key | `api_key` (secret), `webhook_secret` (secret), `account_id` |
| Vault | approle | `vault_addr`, `auth_mount`, `role_id`, `secret_id` (secret), `secret_path_pattern`, `rotation_schedule` |
| AWS Compute Optimizer | iam_role | `role_arn`, `external_id`, `regions[]`, `org_account_filter` |
| Azure Advisor | spn | `tenant_id`, `client_id`+`secret` (secret), `subscription_filter` |
| GCP Recommender | sa / WIF | `project_id`, `sa_email`, `key_or_wif_provider`, `recommender_filter` |

---

## 8. UI/UX Design — Internal Console + End-User Findings Viewer

The Advanced SPA is a **separate** React-in-Babel SPA at `web/CXP Optimization/FinOps Advanced Recommendations/index.html`. RBAC determines which surface a user lands on by default.

### 8.1 Surface 1 — Internal Console (FinOps PM / Platform Eng / FinOps Admin)

A power-user authoring + ops surface. Five top-level sections, navigated via left rail.

#### 8.1.1 Hypothesis Studio (signal-graph editor)

**Layout**: full-bleed canvas. Left palette = signal categories (CSP / billing / K8s / APM / traces / billing / LLM / flow logs / product analytics / CSP-native / custom functions). Right inspector panel for selected node.

**Node types**:
- Signal nodes (typed by category, draggable from palette)
- Transform nodes (aggregations, statistical, classifier, attribution, architectural, custom-function references)
- Join nodes (specify join keys; warn on cardinality blow-up)
- Condition nodes (boolean, threshold, anomaly, peer-compare)
- Action proposal nodes (typed action with parameter template)
- Emit node (terminal — produces Finding)

**Inspector panels**:
- Node config form (parameters specific to type)
- Live signal preview (sample data from last 24 h shown as a sparkline)
- Schema warnings (unit mismatch, missing dimension)

**Top toolbar**:
- Save (creates new version)
- Validate (DAG cycle check, schema check, evidence-requirement check)
- Backtest (Run against 30/60/90 d of history → opens Backtest workbench)
- Promote (Draft → Shadow → Active) — gated by validation + backtest

#### 8.1.2 Backtest Workbench

**Inputs**: window (30/60/90 d), scope (override or inherit), peer comparison toggle.

**Outputs**:
- Findings list (each row: resource_id, evidence summary, estimated savings, would-fire-on-which-day)
- Confusion matrix (when historical dismissals exist for the same resource fingerprint, label TP/FP/FN/TN)
- Coverage map (percentage of expected resources where signals were available)
- Estimated aggregate savings (point + band)
- Per-resource-type breakdown (which resource types contributed most)

**Actions on the workbench**: tighten / loosen condition, edit signal graph, save snapshot, push to Shadow.

#### 8.1.3 Shadow Review

A dashboard for the period a Hypothesis spends in `shadow`. Surfaces:
- Findings emitted (hidden from end users)
- Per-Finding: classification (looks_correct | looks_false_positive | unclear | needs_more_evidence)
- Reviewer notes
- Per-day emission rate trend
- Coverage gap notifications (e.g., "no findings for resource type X in 7 days — is the signal available?")

**Promotion gate**: ≥ 7 days in shadow + reviewer accepts ≥ 80 % of sampled findings as `looks_correct` + zero P0 false-positive incidents.

#### 8.1.4 Provider Registry

Manifest editor. Tabs for active providers, draft manifests, health.

- Click "Add provider" → choose category template → fill manifest fields → validate → publish.
- Per-provider detail: manifest YAML (left), live test ping (right), connected tenants (bottom).
- Health probe results: green / yellow / red per tenant × provider, with last error message.

#### 8.1.5 Hypothesis Analytics (precision / recall / dismissal-reason)

For every active Hypothesis:
- Findings emitted per day
- Approval rate (Findings approved / total)
- Dismissal breakdown by reason code
- Realized-vs-estimated variance distribution
- Time-to-decision distribution
- Top 10 dismissals with reason and customer tenant (for review)

This is what lets PMs prove and improve. Without it, Advanced is shipping in the dark.

### 8.2 Surface 2 — End-User Findings Viewer

A clean, opinionated, evidence-first surface. Left rail navigates between Findings, Outcomes, and Subscriptions.

#### 8.2.1 Findings List

- Default scope: resources the user owns (RBAC-resolved).
- Filters: severity, category, recommendation class (A1, A2, …), proposed action type, resource type, CSP, BU.
- Each row: severity dot · class label · short headline · estimated savings · age · status pill.
- Sort: estimated savings desc, age desc, severity desc.

#### 8.2.2 Finding Detail

A two-column layout with a top-strip status bar.

**Top strip**:
- Recommendation class + Hypothesis name + version
- Severity + estimated savings (point + band) + confidence
- Status (`new | snoozed | approved | applied | reconciled | regressed | dismissed`)
- Owner (SSO group)

**Left column — Why (evidence)**:
- Headline: "We detected … because …" (one-sentence summary auto-generated from evidence)
- Evidence cards (one per evidence type carried by the Hypothesis):
  - Metric series sparkline + click-through to APM / Cloud Monitoring
  - Trace IDs (linked to APM vendor)
  - Billing rows (linked to CUR/Cost Export)
  - Workload fingerprint classification (with confidence)
  - SKU snapshot (Product Catalog rate at time of finding)
  - Peer comparison panel (where this resource sits in the peer distribution)

**Right column — What (action)**:
- Proposed Action card (typed action, parameters, delivery channel)
- Risk score breakdown (blast radius, reversibility, SLO impact, data loss risk)
- Rollback plan
- Change window
- Decision controls: Approve / Snooze (with reason) / Dismiss (with reason) / Request Owner Review

#### 8.2.3 Outcomes Dashboard

For each Finding the user approved:
- T+30 / T+60 / T+90 reconciled savings (vs estimate)
- SLO impact post-action (latency / error rate deltas)
- Total realized YTD across owned resources
- Variance flag if realized < 50 % of estimate

#### 8.2.4 Subscriptions

- Slack / Teams channel for digest delivery
- Email cadence (off | daily | weekly | monthly)
- Severity threshold for inline notification

### 8.3 Visual style

Same dark-purple/indigo palette as the Basic SPA. Same component grammar (cards, status pills, severity dots). Distinct enough that Advanced reads as "the bigger surface" — accent on signal-graph diagrams, evidence cards, and outcome charts.

### 8.4 Empty / Loading / Error states

| Component | Loading | Success | Empty | Error |
|---|---|---|---|---|
| Signal graph editor | Skeleton nodes | Live-rendered DAG | "Drag a signal from the left to start" | "Validation failed: ${reason}" with click-through to offending node |
| Backtest workbench | "Replaying 90 days against signal catalog…" with progress | Findings list + confusion matrix + coverage | "Backtest produced no findings — try loosening or extending window" | "Backtest aborted: ${cause}" with retry |
| Findings list | Skeleton rows | Paged list | "No findings on owned resources right now — nice work" | "Some integrations are unhealthy; coverage may be incomplete" with link |
| Finding detail | Skeleton evidence cards | Full evidence + action panel | n/a | "Evidence binding lost — Hypothesis was changed since this finding emitted" |
| Outcomes dashboard | Skeleton bars | Realized vs estimated bars + SLO impact | "First reconciled outcome lands T+30" with countdown | "Reconciler skipped — billing export missing" with link |

---

## 9. User Journeys

### 9.1 Internal — FinOps PM ships a new recommendation class

1. Open Internal Console → Hypothesis Studio → New Hypothesis (template: "Cost per endpoint").
2. Drag signals: APM → service request rate, latency_p95; Billing → resource cost; K8s → pod-to-resource map.
3. Drag join: on `service.name`.
4. Drag transforms: `cost_per_label` → `peer_compare`.
5. Drag conditions: `endpoint_cost > peer_p95 × 3 OR trend_slope > 0.30/q OR cheap_extreme_volume`.
6. Drag action: `EndpointDeprecate` template; configure delivery `slack_approval`; rollback via `noop`.
7. Drag emit node; bind evidence requirements (5 trace IDs, billing rows, peer panel).
8. Save (v1 draft) → Validate → Backtest 90 days → review confusion matrix → tighten condition → Push to Shadow.
9. After 7 days in shadow, review samples in Shadow Review → 87 % accepted → Activate.
10. Findings begin reaching customer end users.

### 9.2 Customer — Resource owner approves a B1 finding

1. Slack notification: "*New optimisation finding on workload `payments-api` — est. $4,200/mo savings*"
2. Click → opens End-User Findings Viewer at the finding detail.
3. Review evidence: workload fingerprint = `diurnal`, confidence 0.93; weekday-business-hours pattern chart; peer comparison.
4. Review proposed action: `SchedulePause` 18:00–09:00 EST weekdays + weekends; rollback = re-enable schedule.
5. Click Approve → adds Slack thread comment; finding transitions to `approved`.
6. ITSM ticket auto-created in Jira; assigned to ops on-call.
7. Ops applies via runbook; ticket closes; Action transitions to `applied`.
8. T+30: Outcome reconciled — realized $3,710 (88 % of estimate). Owner sees variance on Outcomes Dashboard.

### 9.3 Internal — Provider Registry lifecycle

1. FinOps Platform Eng publishes `providers/dynatrace.yaml` to the manifest repo.
2. Provider Registry CI validates schema, deploys to staging, runs synthetic onboarding.
3. PR review approves; manifest deployed to prod.
4. End-user Internal Console shows Dynatrace as a new available integration.
5. Customer FinOps Admin onboards via the generated form; secret fields go to Vault; health probe succeeds.
6. Dynatrace `metric_contract.signals` automatically appear in the Hypothesis Studio palette.

---

## 10. Acceptance Criteria

### 10.1 Authoring (Internal Console)

- **AC-1.1: Hypothesis with cross-source signal join can be authored.**
  ```
  Given a FinOps PM has Datadog and AWS CUR providers active
  When the PM drags an APM signal node and a billing signal node onto the canvas
   And drags a join node specifying join_key=service.name
  Then the join node validates green
   And a live preview shows joined sample data within 5 seconds.
  ```

- **AC-1.2: Promotion to active requires shadow + accept-rate threshold.**
  ```
  Given a Hypothesis has been in shadow for 5 days with 70% reviewer-accept rate
  When the PM clicks Promote to Active
  Then the transition is rejected
   And a clear message cites the unmet criteria (≥7d shadow, ≥80% accept).
  ```

### 10.2 Findings (End-User Viewer)

- **AC-2.1: Evidence binding renders correctly.**
  ```
  Given a Class A1 finding has 5 trace_ids and 3 CUR row references in evidence
  When the resource owner opens the finding detail
  Then trace_ids render as clickable Datadog links
   And CUR rows render as a billing card with correct amounts
   And the workload fingerprint card displays classification + confidence.
  ```

- **AC-2.2: Approve transitions finding correctly.**
  ```
  Given a finding is in status=new and the user is in the resource owner SSO group
  When the user clicks Approve
  Then the finding transitions to status=approved within 5 seconds
   And an Action of the proposed type is created in status=proposed
   And the configured delivery channel (ITSM/IaC PR/Slack) is invoked.
  ```

### 10.3 Reconciler

- **AC-3.1: Realized savings land at T+30.**
  ```
  Given an Action was applied on day D
  When day D+30 has elapsed and Reconciler runs
  Then an Outcome event is emitted within 24 hours
   And the End-User Outcomes Dashboard shows the T+30 row.
  ```

- **AC-3.2: SLO regression triggers regressed state.**
  ```
  Given an Action was applied AND the affected resource has SLO signals
  When latency_p95 increased by ≥ 25% over a 7-day window post-action
  Then the originating Finding transitions to status=regressed
   And the owner SSO group is alerted
   And on auto_apply Hypotheses, automatic rollback is invoked using the action's rollback_plan.
  ```

### 10.4 Provider Registry

- **AC-4.1: New provider added by manifest only.**
  ```
  Given a new manifest providers/dynatrace.yaml passes CI validation
  When the manifest deploys to prod
  Then Dynatrace appears in the Internal Console Provider Registry list
   And its metric_contract.signals appear in the Hypothesis Studio palette
   And no other code change was required.
  ```

### 10.5 Custom Function Runtime

- **AC-5.1: CF executes within sandbox limits.**
  ```
  Given a custom function cf://workload_fingerprint_v2 declares CPU≤30s, RAM≤512MB
  When the evaluator invokes the CF on a 30-day series
  Then the CF returns within 30 seconds
   And memory does not exceed 512 MB
   And the function has no network access (verified by attempted HTTP throwing).
  ```

### 10.E Failure scenarios (required)

- **AC-E1: Integration unhealthy degrades gracefully.**
  ```
  Given the Datadog provider's health probe has failed three consecutive times
  When the evaluator runs Class A1
  Then findings that depend on Datadog signals are emitted with reduced confidence and an evidence flag "datadog_signals_stale"
   And the Internal Console marks the provider as unhealthy
   And a digest notification is sent to the FinOps Admin.
  ```

- **AC-E2: Reconciler partial-data handling.**
  ```
  Given billing export has a 24-hour gap on a key day
  When the Reconciler attempts T+30 reconciliation across that gap
  Then the Outcome is written with status=partial and reason=billing_gap
   And the realized_savings field shows a wider confidence band annotation.
  ```

---

## 11. Non-Functional Requirements

| Category | Baseline | This Feature's Requirement |
|---|---|---|
| **Performance — evaluator** | — | p95 ≤ 60 s per Hypothesis × 10 k resources (DAG parallelism = 8) |
| **Performance — backtest** | — | 90-day, 10 k-resource backtest ≤ 10 min for Advanced |
| **Performance — signal-graph editor** | — | Node drag-drop responsive ≤ 100 ms; live preview ≤ 5 s |
| **Scalability** | 10 k resources | Up to 50 active Advanced Hypotheses per tenant; up to 200 if customer pays for compute add-on |
| **Security / RBAC** | persona-scoped | All Internal Console surfaces are RBAC-gated; CFs run sandboxed; secrets stored in Vault |
| **Availability** | 99.9 % | 99.9 % Advisory API; 99.5 % evaluator (longer windows acceptable) |
| **Data Retention** | 13 months | Hypothesis + Finding + Action + Outcome events retained 24 months |
| **Audit / Logging** | actor + before/after | Immutable hash-chained audit trail; CF executions logged with CPU, memory, exit code |
| **Idempotency** | — | All mutating endpoints accept Idempotency-Key (24 h dedupe); CF execution idempotent on `(version, input_hash)` |
| **Multi-tenant safety** | — | Strict scope on every query; CFs cannot access cross-tenant data even within FinOps |
| **CF sandbox** | — | CPU 30 s, RAM 512 MB, no network, no fs except stdin/stdout, signed binary verification |
| **Rate-limit safety** | — | Provider-side rate budgets respected; never breach tenant rate limit |

---

## 12. Dependencies & Risks

### 12.1 Dependencies

| Dependency | Owner | Impact if Delayed |
|---|---|---|
| Basic engine (Advisory + Provider Registry + Signal Catalog + Product Catalog + Reconciler) | Platform Eng | Blocks entire PRD — Advanced builds on Basic backbone |
| DAG scheduler / async evaluator | Platform Eng | Blocks all Advanced Hypotheses |
| Custom Function Runtime | Security + Platform Eng | Blocks B1, C1 (FFT, LP solver) |
| Identity provider integration (OIDC + SCIM) | Customer onboarding | Blocks RBAC on Internal Console |
| ITSM integrations (ServiceNow + Jira) | Integrations team | Blocks action delivery for many classes |
| IaC integrations (GitHub App + GitLab + Bitbucket) | Integrations team | Blocks IaC PR delivery — can fall back to ITSM |
| APM provider integrations (Datadog + NR + Dynatrace + OTel) | Integrations team | Blocks Band A |
| Data-platform integrations (Snowflake + BQ + Redshift + Databricks) | Integrations team | Blocks A2 |
| LLM provider integrations | Integrations team | Blocks A3 |
| Carbon APIs (CSP) | Integrations team | Blocks D3 |

### 12.2 Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Customer cannot map cost-attribution tags well enough to support D1 | High | High | Ship a tag-coverage advisor as a pre-requisite Hypothesis ("D0"); refuse to emit D1 findings under 75% coverage |
| APM joins blow up cardinality and tank evaluator latency | Med | High | Aggressive pre-aggregation at ingest (per service per minute); join-cardinality warnings at author time |
| Custom Function Runtime security | Low | Critical | Sandbox with isolate-vm/firejail; no network; signed binaries; per-tenant resource quotas; pre-flight lint |
| Findings drown the user | High | Med | Severity gating + dedupe fingerprint + per-tenant rate limit on notifications + digest mode |
| Realized savings less than estimated → trust loss | High | High | Confidence bands shown up front; outcomes dashboard surfaces variance; Hypothesis Analytics surfaces this to the author for tuning |
| Commitment Orchestrator (C1) makes a wrong purchase | Low | Critical | Never auto-applied; dual approval for purchases > 30% of monthly spend; ladder plan with reversal points |
| Carbon savings disputed | Med | Med | Conservative methodology citing CSP-published intensity figures only; no proprietary modelling |

---

## 13. Rollout & Migration Plan

| Phase | Scope | Timeline | Notes |
|---|---|---|---|
| **Phase 0** — Backbone (also serves Basic) | Internal alpha | Weeks 1–6 | Advisory + Provider Registry + Signal Catalog + Product Catalog + Reconciler + DAG scheduler + Custom Function Runtime |
| **Phase 1** — P0 integrations | Internal alpha | Weeks 5–10 | All Basic providers + Datadog + Snowflake + ServiceNow + Slack + Okta |
| **Phase 2** — Bands A & B | Design partners (3 tenants) | Weeks 10–18 | A1, A2, A3, B1, B2, B3 ship with first-party Hypotheses; Internal Console GA for FinOps team |
| **Phase 3** — Bands C & D | Design partners | Weeks 16–24 | C1, C2, C3, D1, D2, D3 ship; auto-apply for safe action types behind policy-as-code; LP solver for C1 |
| **Phase 4** — GA | All paying tenants | Weeks 24+ | Pricing tier defined; customer Internal Console (limited) opens for Author add-on role |

Migration from Basic:
- No data migration; Advanced is additive.
- A "Promote to Advanced" CTA appears on Basic Hypotheses that have features only Advanced supports (e.g., needs APM signal); clicking it scaffolds an Advanced Hypothesis with the Basic rule's intent.

---

## 14. Open Questions

| # | Question | Blocking? | Owner | Target | Status |
|---|---|---|---|---|---|
| 1 | OTel-first vs APM-vendor-first — which do we ship first for Band A? | Yes | Platform Eng | 2026-05-10 | Open |
| 2 | IaC PR target — Terraform vs Pulumi vs Terragrunt-aware | Yes | Platform Eng | 2026-05-10 | Open |
| 3 | Custom Function Runtime — host vs delegate-to-customer-webhook | Yes | Security + Platform Eng | 2026-05-17 | Open |
| 4 | Reconciler scope — claim realized savings for actions we didn't apply (user applied via console)? | No, but UX | Product | 2026-05-03 | Open |
| 5 | Commitment orchestrator — operate autonomously or human-in-the-loop only for v1? | Yes | Product + Platform Eng | 2026-05-24 | Open |
| 6 | Internal Console for paying customers — add-on role or separate SKU? | Yes | Product + GTM | 2026-05-31 | Open |
| 7 | Data-residency constraints on cross-tenant Custom Functions (FinOps-published) | Yes | Security + Legal | 2026-05-24 | Open |
| 8 | CRM integration for D1 — required (block D1) or optional (degrade D1)? | No | Product | 2026-05-17 | Open |

---

## 15. Appendix

### 15.1 Glossary

| Term | Definition |
|---|---|
| Signal graph | DAG of signal nodes, transform nodes, and condition nodes that defines an Advanced Hypothesis |
| Custom Function | Sandboxed signed transform (JS / Python) that extends the transform node vocabulary |
| Workload fingerprint | Classification of a workload as steady / bursty / batch / diurnal / seasonal / mixed |
| Spot readiness score | Composite 0–100 score of a workload's eligibility for spot / preemptible |
| Peer comparison | Anti-noise statistical control comparing a finding against similar resources |
| Evidence binding | Mandatory attachment of structured evidence (traces, billing, fingerprint, peer set) to every finding |
| Shadow mode | Required ≥7-day period where Advanced findings are emitted but hidden from end users |
| Provider Registry | Manifest-driven integration runtime |
| Internal Console | Power-user authoring + ops surface for FinOps team and customer admins |
| End-User Findings Viewer | Customer surface for resource owners to see and act on findings |

### 15.2 Reference documents

- `prd-basic.md` — Basic tier PRD
- `docs/architecture/finops-recommendation-engine.md` — technical design
- `docs/finops_finops_capability_inventory.md` — current ADV-* surface area to compare against
- `docs/finops_finops_question_taxonomy.md` — FinOps Agent question coverage; Advanced will close several "out of scope" rows there

### 15.3 API Contract additions (over Basic)

```
POST   /api/v1/hypotheses                     — { tier: "advanced", signal_graph: {...} }
POST   /api/v1/hypotheses/{id}/shadow-review  — append review classification on shadow finding
GET    /api/v1/custom-functions               — list registered CFs in catalog
POST   /api/v1/custom-functions               — register new CF (signed bundle upload)
POST   /api/v1/custom-functions/{id}/promote  — draft → active (security review + signing)
GET    /api/v1/hypotheses/{id}/analytics      — precision, recall, dismissal-reason rollup
POST   /api/v1/findings/{id}/owner-review     — request owner review with comment
GET    /api/v1/outcomes/variance              — variance distribution per Hypothesis
```

### 15.4 State Machine (Hypothesis — Advanced)

```
                ┌──────────┐
                │  draft   │
                └────┬─────┘
                     │ promote (validate + backtest)
                     ▼
                ┌──────────┐  reject
                │  shadow  │ ◀──────────────┐
                └────┬─────┘                │
                     │ activate (≥7d + ≥80% accept rate + 0 P0 FP)
                     ▼                      │
                ┌──────────┐                │
                │  active  │ ──── monitoring fail
                └────┬─────┘
                     │ deprecate
                     ▼
                ┌──────────────┐
                │  deprecated  │
                └──────────────┘
```

---

*PRD version: 1.0 · Tier: Advanced · 12 recommendation classes · 60 worked examples · Companion: prd-basic.md, docs/architecture/finops-recommendation-engine.md*
