# FinOps Recommendation Engine

## Status
Basic requirements revamped and ready for engineering scoping; Advanced remains documented but out of scope for current Basic review

## ADO Work Item IDs
- (Pending — to be created after PRD review)

## Current Phase
Basic requirements review complete → recommendation catalog + integration guide added → Engineering scoping

## What's shipped (demo)

| Artifact | Path | Notes |
|---|---|---|
| Basic PRD | `prd-basic.md` | Rule-based gap closures for today's SPA |
| Basic critical review | `basic-requirements-critical-review.md` | Gap review, revamped Basic scope, prioritization model, AI aggregate metric inclusion |
| Basic recommendation catalog guide | `basic-recommendation-catalog.md` | How to use the 1,030-row global recommendation catalog |
| Basic recommendation seed CSV | `basic-recommendation-catalog-500.csv` | Stable 500-row seed catalog retained for reference |
| Basic recommendation global CSV | `basic-recommendation-catalog-global.csv` | 1,030 recommendation definitions with definitions, benefits, metrics, thresholds, priority, data sources, onboarding path, compatibility group, and advisory mapping |
| CostVars advisory mapping | `basic-costvars-advisory-mapping.md` | Maps `FinOps_CostVars_Tooling_v2.docx` advisories to `CVAR-*` IDs and configured `BR-*` recommendation rows |
| Basic integration framework guide | `basic-integration-framework-guide.md` | CSP, SaaS, Kubernetes, Product Catalog, AI usage, and GPU telemetry setup guide |
| Basic product catalog coverage | `basic-product-catalog-coverage.md` | Current Azure/AWS/GCP extracted catalog inventory and Product Catalog review view requirements |
| Basic product compatibility groups | `basic-product-compatibility-groups.md` | Research-backed movement boundaries and group IDs used by recommendations and Product Catalog rows |
| Basic UI flow simulation review | `basic-ui-flow-simulation-review.md` | UI configurability simulation, gaps found, fixes made, and remaining backend gaps |
| Basic system user guide | `basic-system-user-guide.md` | End-to-end operating guide: setup, catalog selection, authoring/import, backtest, activation, findings, actions, reconciliation |
| Basic project map and roadmap | `basic-project-map-roadmap.md` | Completed/pending build map across requirements, integrations, backend, frontend, data, security, QA, and rollout phases |
| Advanced PRD | `prd-advanced.md` | 12 classes × 5 examples = 60 worked findings; Internal + End-User UX spec |
| Technical design | `../../docs/architecture/finops-recommendation-engine.md` | Services, data contracts, Provider Registry manifest, action runtime |
| Basic SPA (upgraded) | `web/CXP Optimization/FinOps Recommendation Engine/index.html` | Persists custom rules, SSO-group approver picker, Backtest-on-Publish, Realized Savings tab, Product Catalog review tab, Basic Readiness / Recommendation Library tab, expanded action vocabulary |
| Basic SPA catalog data | `web/CXP Optimization/FinOps Recommendation Engine/data/basic-recommendation-catalog-global.csv` | UI-local copy of the expanded global catalog so the static SPA can load all templates at the current URL |
| Advanced SPA (new) | `web/CXP Optimization/FinOps Advanced Recommendations/index.html` | Internal Console (Hypothesis Studio / Backtest / Shadow / Provider Registry / Analytics) + End-User Findings Viewer (list / detail / outcomes / subscriptions) |

## Basic SPA upgrades (gap closures from critical review)

- **Persistence** — User-authored Hypotheses now persist to a localStorage-backed registry (mock of the Advisory Service DB). Submitted rules appear in the list immediately.
- **Basic Evaluator** — Deterministic `evaluateRuleGroups(record, ruleGroups, outerConnectors)` interpreter that walks the authored rule graph against resource records. Used by both Simulate Now and the new Backtest.
- **Backtest-on-Publish** — Step 6 of the authoring wizard runs the draft Hypothesis against a synthetic 30-day sample (100 / 300 / 1000 resources) and surfaces projected hits, suppressions, projected savings, hit rate, and failure reasons before submission.
- **RBAC Approver** — Free-text approver input replaced with an SSO-group picker (FinOps Leads / Platform SREs / Data Platform / Network / Security Council / Eng Managers) with scoped policies. Approved state records both the approver email and the group they're acting under.
- **Realized Savings tab** — Recommendation detail now has a dedicated tab showing billing-verified realized savings (last 30d) alongside engine projection, realization %, and the action funnel (accepted / rejected / suppressed). Shows reconciler method with counterfactual framing.
- **Expanded Action Vocabulary** — Authoring and detail views now expose Basic actions plus the canvas target actions: `Shutdown`, `RightsizeSku`, `SchedulePause`, `TierMove`, `DeleteOrphan`, `VolumeTypeSwap`, `CommitmentReview`, `TagFix`, `BudgetReview`, `ModelRoute`, `SpotReview`, `LicenseReview`, `CommitmentPurchase`, `SpotMigrate`, `RegionConsolidate`, and `LicenseBYOB`.
- **Product Catalog review view** — Basic SPA now has a dedicated Product Catalog tab with provider/category/subcategory/region/pricing/search filters, coverage cards, pricing snapshot IDs, blocked coverage warnings, and source-to-target compare example.
- **Compatibility groups** — Product Catalog product types and all global recommendation rows now carry compatibility group IDs so rightsize/tier/model-route actions stay within workload-compatible boundaries.
- **Global Recommendation Library** — Basic SPA now loads `basic-recommendation-catalog-global.csv` directly, shows all 1,030 templates, including CostVars advisory IDs, validates UI configurability, and can import a selected template as a draft.
- **Basic Readiness / Recommendation Library view** — Basic SPA now surfaces the global catalog distribution, P0 prioritization, integration onboarding readiness, and critical review fix tracker.

## Advanced SPA surfaces

### Internal Console (for product / SRE / FinOps authors)
- **Hypothesis Studio** — 12 authored Hypotheses (one per class), filterable by band / status, each opening to a detail page with Signal Graph (5-stage DAG lanes), Data Contract, Technical + Business Rules, Shadow Mode queue, Analytics, Versions
- **Backtest Workbench** — Replay any Hypothesis against 30d / 90d / 365d historical signals across tenants with guardrail feedback before promotion
- **Shadow Review** — Cross-hypothesis reviewer queue with per-finding Confirm TP / Mark FP / View evidence trace actions; aggregate precision & FP rate
- **Provider Registry** — Live health view of all 22 integrations grouped by category (APM / Warehouse / LLM / Metrics / K8s / Billing / License / Flow Logs / Product Analytics / SLO / Carbon)
- **Portfolio Analytics** — Engine-wide roll-up: live vs. shadow hypothesis counts, findings & realized savings by band

### End-User View (for customers)
- **Advisories list** — All 60 findings (shadow findings are filtered out at source), sorted by savings, with band / severity / status filters and CSV / subscribe CTAs
- **Finding detail** — 5 tabs per advisory: Evidence (why we flagged it, signal lineage), Action (proposed action + 3 delivery options: Terraform PR / Jira-ServiceNow ticket / Direct apply), Impact (cost, latency, risk, rollback, downstream dependencies), Outcome (realized $ post-action, reconciliation method), Owners (primary owner / approver / watcher / on-call)
- **Outcomes dashboard** — Realized savings (30d), committed in-flight, realization rate, breakdown by band
- **Subscriptions** — Customer-configurable filters delivered to Slack / email

## Documents in this folder

- `prd-basic.md` — PRD for the Basic (rule-based) engine, closing all rule-based-achievable gaps in today's SPA
- `basic-requirements-critical-review.md` — critical review of current Basic requirements and gaps filled for engineering readiness
- `basic-recommendation-catalog.md` — usage guide for the Basic global recommendation library
- `basic-recommendation-catalog-500.csv` — stable 500-row seed recommendation library retained for comparison
- `basic-recommendation-catalog-global.csv` — 1,030 prioritized Basic recommendation definitions, including CSP-native, SaaS, K8s, AI aggregate-metric, CostVars, and global provider-native recommendations
- `basic-costvars-advisory-mapping.md` — CostVars advisory ID to recommendation row mapping
- `basic-integration-framework-guide.md` — complete setup guide for CSPs, third-party SaaS, Kubernetes, Product Catalog, and AI telemetry integrations
- `basic-product-catalog-coverage.md` — current extracted Product Catalog coverage for Azure, AWS, and GCP plus the required catalog review UI
- `basic-product-compatibility-groups.md` — compatibility group definitions and research basis for safe source-to-target movements
- `basic-ui-flow-simulation-review.md` — simulation results for configuring recommendation rows via the UI
- `basic-system-user-guide.md` — how to use the Basic engine end to end
- `basic-project-map-roadmap.md` — project map and roadmap with completed and pending requirements, integrations, backend, frontend, data, security, QA, and rollout activities
- `prd-advanced.md` — PRD for the Advanced engine, including per-band data contracts, integration mappings, 60 worked examples (5 × 12 classes), and separate UI spec with internal-team and end-user views
- `ui-flows/` (planned) — screenshots and Figma exports of Advanced Internal Console + Findings Viewer once design partner review closes

## Two-tier summary

Single product, two tiers that are **co-authored, co-governed, but architecturally separate** so customers can adopt incrementally and FinOps can price-discriminate.

| Tier | Offering | Engine | What it does |
|---|---|---|---|
| **Basic** | FinOps Recommendation Engine (today's SPA, upgraded) | Deterministic rule-based evaluator over CSP metrics, billing, K8s, FinOps Observability | Rightsize / idle / orphaned detection with catalog-priced savings, backtest-on-publish, realized-savings reconciliation, RBAC approvals |
| **Advanced** | FinOps Advanced Recommendations | Signal fusion engine over APM traces, query history, AI/LLM usage, workload fingerprints, commitment portfolios, flow logs, product analytics | 12 differentiated recommendation classes (Bands A–D) that cite trace / unit-economic / workload-behaviour evidence and propose typed actions (Terraform PR, commitment purchase, schedule, tier move, etc.) |

Both tiers share a common backbone: **Hypothesis → Finding → Action → Outcome** data model, Provider Registry for integrations, Product Catalog priced from live CSP APIs, and a realized-savings reconciler against billing.

## Related folders

- `docs/architecture/finops-recommendation-engine.md` — technical design spanning both tiers (services, data contracts, Provider Registry manifest schema, action runtime)
- `web/CXP Optimization/FinOps Recommendation Engine/` — Basic SPA (upgraded in-place)
- `web/CXP Optimization/FinOps Advanced Recommendations/` — Advanced SPA (new standalone, Internal Console + End-User Findings Viewer)
- `pm/features/advisory/` — legacy CSP-forwarded advisories (ADV-READ-01 in capability inventory)
- `pm/features/optimization-recommendations/` — legacy umbrella feature; superseded by this one
- `pm/features/kubernetes-opencost/`, `pm/features/license-management/`, `pm/features/reserved-instances/`, `pm/features/savings-plans/` — related sub-surfaces that Advanced consumes
- `pm/features/third-party-integrations/` — integration shell; Provider Registry (this feature) is the canonical integration runtime
- `docs/finops_finops_capability_inventory.md` — ADV-* capability rows this feature replaces/extends
