# FinOps Basic Recommendation Engine - Project Map and Roadmap

## Scope

This project map covers the Basic rule-based recommendation engine only. Advanced signal-fusion recommendations, trace-level optimization, query-plan optimization, and workload classifiers remain out of scope until the separate Advanced ask.

## Target Outcome

Build a production-ready Basic Recommendation Engine that can:

- Connect CSP, billing, Kubernetes, Product Catalog, SaaS, and AI aggregate metric providers.
- Onboard the 1,030-row global recommendation library as rule templates, with the original 500-row seed retained for comparison.
- Author, backtest, approve, publish, evaluate, and reconcile rule-based recommendations.
- Show Product Catalog coverage and pricing snapshots used for savings estimates.
- Import CSP-native and SaaS recommendations as normalized FinOps Findings.
- Route typed actions through approval, ITSM, and outcome reconciliation.

## Completed in Requirements and Demo UI

| Area | Completed artifact | Status |
|---|---|---|
| Basic critical review | `basic-requirements-critical-review.md` | Completed |
| Global recommendation library | `basic-recommendation-catalog-global.csv`, `basic-recommendation-catalog.md`, and `basic-costvars-advisory-mapping.md` | Completed |
| Metrics and thresholds | Catalog CSV includes primary metrics, thresholds, lookback, sources, complexity, and priority | Completed |
| Integration guide | `basic-integration-framework-guide.md` | Completed |
| Product Catalog coverage | `basic-product-catalog-coverage.md` | Completed |
| User guide | `basic-system-user-guide.md` | Completed |
| Basic PRD | `prd-basic.md` | Completed for engineering review |
| Architecture | `docs/architecture/finops-recommendation-engine.md` | Completed for engineering review |
| Action vocabulary in UI | Basic SPA now exposes Basic and canvas target action types | Completed demo |
| Product Catalog UI | Basic SPA now has filterable Product Catalog review view | Completed demo |
| Readiness UI | Basic SPA now has Basic Readiness / Recommendation Library view | Completed demo |
| Backtest-on-publish UI | Authoring wizard includes synthetic backtest preview | Completed demo |
| RBAC approver UI | Approval flow uses SSO-group picker | Completed demo |
| Realized savings UI | Recommendation detail includes realized savings tab | Completed demo |

## Pending Production Build

| Workstream | Activity | Owner | Priority | Complexity | Status |
|---|---|---|---|---|---|
| Product | Finalize GA tranche from global catalog: P0, very high/high value, low/medium complexity | PM + FinOps SME | P0 | Medium | Pending |
| Product | Convert catalog rows into typed rule-template specs with IDs, default thresholds, and guardrails | PM + Eng | P0 | Medium | Pending |
| Backend | Build Advisory Service persistence for Hypothesis, Finding, Action, Outcome, AuditEvent | Backend | P0 | High | Pending |
| Backend | Implement Basic Evaluator service for deterministic metric/threshold rules | Backend | P0 | High | Pending |
| Backend | Implement backtest API over historical metrics and billing data | Backend | P0 | High | Pending |
| Backend | Implement scheduler and run orchestration for active Hypotheses | Backend | P0 | Medium | Pending |
| Backend | Implement suppression engine: savings <= 0, stale pricing, missing owner, missing metric, duplicate finding | Backend | P0 | Medium | Pending |
| Backend | Implement realized-savings Reconciler against CUR, Azure Cost Export, and BigQuery billing export | Backend | P0 | High | Pending |
| Backend | Implement Product Catalog API: coverage, SKU search, pricing snapshots, stale-rate detection, compare source/target | Backend | P0 | High | Pending |
| Backend | Implement Provider Registry manifest runtime and health checks | Platform | P0 | High | Pending |
| Backend | Implement signal coverage API per tenant and recommendation definition | Platform | P0 | Medium | Pending |
| Backend | Implement telemetry cost estimator before enabling integrations | Platform | P0 | Medium | Pending |
| Backend | Import AWS Compute Optimizer, Trusted Advisor, Cost Optimization Hub, and Cost Explorer recommendations | Integrations | P0 | Medium | Pending |
| Backend | Import Azure Advisor, Cost Management, Monitor, Resource Graph, and Retail Prices data | Integrations | P0 | Medium | Pending |
| Backend | Import GCP Recommender, Monitoring, Asset Inventory, Billing Export, and Billing Catalog data | Integrations | P0 | High | Pending |
| Backend | Implement third-party SaaS connectors for CloudHealth, Cloudability, Flexera, Densify, Datadog, Kubecost/OpenCost, Spot.io | Integrations | P1 | High | Pending |
| Backend | Implement AI aggregate metric connectors for LiteLLM, Portkey, Helicone, LangSmith/Langfuse, DCGM, run:ai, W&B, MLflow | Integrations | P1 | High | Pending |
| Frontend | Connect SPA to real Advisory Service APIs and remove localStorage-only persistence | Frontend | P0 | Medium | Pending |
| Frontend | Replace synthetic BacktestPreview with backend backtest result, failure reasons, and coverage warnings | Frontend | P0 | Medium | Pending |
| Frontend | Connect Product Catalog tab to live catalog API with filters, snapshots, stale warnings, and blocked definitions | Frontend | P0 | Medium | Pending |
| Frontend | Connect Basic Readiness view to catalog, coverage, provider-health, and roadmap APIs | Frontend | P1 | Medium | Pending |
| Frontend | Add native/SaaS imported Finding review flow with source evidence and dedup status | Frontend | P1 | Medium | Pending |
| Frontend | Add ITSM action delivery setup for ServiceNow and Jira | Frontend + Integrations | P1 | Medium | Pending |
| Security | Implement tenant RBAC, SSO group mapping, approval policy, and audit immutability | Security + Backend | P0 | High | Pending |
| Data | Build tenant signal model for account, subscription, project, resource, owner, tag, service, SKU, region, and cost center | Data Platform | P0 | High | Pending |
| QA | Build recommendation-template test harness for metric thresholds, missing metrics, stale price, and false-positive fixtures | QA + Backend | P0 | Medium | Pending |
| Ops | Add observability for evaluator runs, provider health, backtest latency, finding volume, and reconciler lag | SRE | P1 | Medium | Pending |

## Roadmap

### Phase 0 - Engineering Scoping and GA Tranche

Goal: lock the first production slice.

- Select 80-120 GA templates from the global catalog.
- Confirm each selected template has metric source, threshold, Product Catalog dependency, action type, owner requirement, and suppression rules.
- Produce ADO epics and stories from this project map.

Exit criteria:

- GA template list is approved.
- Backend API contracts are accepted.
- Product Catalog source coverage for AWS and Azure is confirmed.

### Phase 1 - Core Rule Engine MVP

Goal: make authored Basic recommendations real.

- Build Advisory Service persistence.
- Build Basic Evaluator and scheduler.
- Build backtest API over historical signal data.
- Connect UI authoring, backtest, approval, and findings list to APIs.
- Support executable Basic actions: `Shutdown`, `RightsizeSku`, `SchedulePause`, `TierMove`, `DeleteOrphan`, `VolumeTypeSwap`.

Exit criteria:

- A user can author a rule, backtest it, submit it, approve it, activate it, and see live Findings.
- Suppressed findings are visible with reason codes.
- Every cost-saving finding references a pricing snapshot ID.

### Phase 2 - Integrations and Product Catalog

Goal: make the engine useful with real provider data.

- Productionize AWS, Azure, and GCP source connectors.
- Build Product Catalog API and freshness controls.
- Add integration setup cost estimator and signal coverage gate.
- Import CSP-native recommendations as FinOps Findings.
- Connect Product Catalog UI to live data.

Exit criteria:

- AWS and Azure Product Catalog coverage is usable for GA recommendations.
- GCP Product Catalog blocker is either resolved or explicitly marked as not GA.
- Customer sees permission, cost, health, and coverage before enabling each provider.

### Phase 3 - SaaS, Kubernetes, and AI Aggregate Cost

Goal: expand value beyond CSP-native data.

- Add Kubernetes/OpenCost/Kubecost and Prometheus signal coverage.
- Add Datadog, Densify, CloudHealth/Cloudability, Flexera, Spot.io ingestion where APIs are available.
- Add AI aggregate telemetry connectors for token, retry, model, vector index, GPU, checkpoint, and warm-pool metrics.
- Support review actions: `CommitmentReview`, `TagFix`, `BudgetReview`, `ModelRoute`, `SpotReview`, `LicenseReview`.

Exit criteria:

- AI and Kubernetes recommendation templates can run without trace-level or prompt-level data.
- SaaS-imported recommendations are deduplicated against FinOps-native findings.
- Review-only actions route through approval and ITSM.

### Phase 4 - Reconciliation, Governance, and GA Hardening

Goal: prove savings and make operations reliable.

- Build Reconciler for T+30/T+60/T+90 realized savings.
- Add audit immutability and export.
- Add run observability and operational dashboards.
- Add QA regression suite over selected recommendation templates.
- Run pilot tenants and refine threshold defaults.

Exit criteria:

- Realized savings can be shown per Hypothesis, Finding, Action, provider, BU, and owner.
- False-positive and realization-rate reporting is available.
- GA readiness checklist is complete.

## Dependency Map

| Dependency | Needed by | Current state | Risk |
|---|---|---|---|
| Product Catalog builders | Savings estimates, rightsizing, tier moves, volume swaps | AWS/Azure extracted; GCP blocked | High for GCP GA |
| Billing exports | Reconciler, budget/anomaly findings, CSP-native normalization | Requirements documented | High |
| CSP metrics APIs | Evaluator and backtest | Requirements documented | Medium |
| Provider Registry | Integration setup, health, coverage | Requirements documented | Medium |
| Tenant ownership/tag model | Approvals, routing, suppression | Requirements documented | Medium |
| SSO groups | Approval and RBAC | UI demo mocked | Medium |
| ITSM connectors | Action delivery | Requirements documented | Low for MVP, medium for GA |
| AI aggregate telemetry | AI recommendations | Requirements documented | Medium |

## Requirement Completion Tracker

| Requirement | Completed in docs | Visible in demo UI | Production pending |
|---|---:|---:|---:|
| Global recommendation library | Yes | Summary visible | Template import service |
| Per-recommendation metrics and thresholds | Yes | Summary visible | Evaluator contracts |
| Product Catalog review view | Yes | Yes | Live API integration |
| Action vocabulary from critical review/canvas | Yes | Yes | Action workflow backend |
| CSP-native recommendation imports | Yes | Partially represented | Provider ingestion |
| Third-party SaaS integration framework | Yes | Onboarding readiness visible | Connectors |
| AI aggregate metric recommendations | Yes | Catalog/readiness visible | Connectors + templates |
| Customer telemetry cost visibility | Yes | Onboarding readiness visible | Estimator API |
| Rule persistence | Yes | localStorage demo | Advisory DB |
| Backtest-on-publish | Yes | Synthetic demo | Historical data API |
| Realized savings | Yes | Mock demo | Reconciler |
| SSO-group approvals | Yes | Mock demo | RBAC/IdP integration |

## Next Engineering Inputs Needed

- Confirm target backend stack and database for Advisory Service.
- Confirm tenant identity model and SSO group source.
- Confirm current Product Catalog builder ownership and whether GCP API key can be provisioned.
- Confirm first two pilot tenants or representative data fixtures.
- Confirm ITSM priority: Jira first, ServiceNow first, or both after MVP.
