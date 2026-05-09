# Basic Recommendation Engine - Critical Requirements Review

## Scope

This review is only for the Basic FinOps Recommendation Engine. Advanced recommendation classes, signal graphs, APM trace attribution, query-plan analysis, and workload classifiers are out of scope for this request.

## Executive assessment

The current Basic PRD correctly fixes the old SPA's biggest problems: authored rules were not real, recommendations did not persist, savings were typed manually, approvals were free text, and realized savings were not reconciled. Those are the right foundations.

However, the requirement is still not engineering-ready because it does not yet define the production recommendation library, exact metric/threshold contracts, native-provider ingestion, third-party SaaS onboarding, customer telemetry cost, AI cost optimization, or a dedicated Product Catalog review view.

## Critical gaps and required fixes

| Area | Gap | Why it matters | Required fix |
|---|---|---|---|
| Recommendation catalog | No ranked global library exists. | A rule engine without content will not deliver user value. | Use `basic-recommendation-catalog-global.csv` as the Basic recommendation library, with the 500-row seed retained for comparison. |
| Metrics and thresholds | PRD lists sources but not per-recommendation metrics. | Evaluator, backtest, QA, and support cannot agree on behavior. | Treat the CSV as the metric and baseline-threshold contract. |
| CSP-native advisors | Open question was unresolved. | Customers expect AWS/Azure/GCP recommendations to appear in one FinOps surface. | Import native advisor recommendations as normalized FinOps Findings. |
| SaaS providers | No complete onboarding guide. | CloudHealth, Cloudability, Densify, Datadog, Kubecost, Spot.io, Flexera cannot be integrated predictably. | Add `basic-integration-framework-guide.md`. |
| AI cost optimization | Original Basic scope excluded LLM usage entirely. | AI/GPU/token spend is now a major FinOps cost area. | Include rule-based AI cost recommendations when data comes from aggregate usage, billing, gateway, GPU, model-registry, or SaaS APIs. |
| Product Catalog UX | Product Catalog is required but not reviewable. | Users cannot defend savings or inspect SKU/region coverage. | Add dedicated Product Catalog browse view in `basic-product-catalog-coverage.md`. |
| Customer telemetry cost | API/metric/billing export cost is undocumented. | Customers may be surprised by monitoring, BigQuery, Athena, Log Analytics, or SaaS costs. | Integration guide must show expected ingestion cost and controls before enablement. |
| Onboarding journey | Provider setup does not include permission tests, cost estimate, signal coverage, or backfill. | Integrations may appear connected but not enable recommendations. | Revamp journey: manifest -> credentials -> permissions -> cost estimate -> health -> coverage -> backtest. |
| Prioritization | No implementation order. | Engineering may build low-value recommendations first. | Prioritize P0 + high value + low/medium complexity + catalog coverage. |

## Revamped Basic scope

Basic includes deterministic rules over:

- CSP resource state and metrics.
- CSP billing exports and native provider recommendations.
- Kubernetes and container metrics from Prometheus, Kubecost/OpenCost, kube-state-metrics, and provider APIs.
- Product Catalog pricing and SKU metadata.
- Third-party SaaS recommendation exports where the SaaS exposes metrics or recommendations.
- AI aggregate metrics from LLM usage APIs, LLM gateways, GPU/DCGM exporters, model registries, vector DB APIs, and experiment trackers.

Basic still excludes:

- APM trace-level cost attribution.
- SQL/query-plan optimization.
- Workload fingerprint classifiers.
- Probabilistic signal-fusion graphs.
- Autonomous execution without explicit rule/action templates and approvals.

## Prioritization model

The global catalog carries `priority`, `end_user_value`, `implementation_complexity`, definitions, benefits, configurator guidance, and advisory mappings.

Current distribution:

| Dimension | Count |
|---|---:|
| Priority P0 | 490 |
| Priority P1 | 490 |
| Priority P2 | 50 |

## Catalog distribution by category

| Category | Rows |
|---|---:|
| AI | 360 |
| Compute | 110 |
| Containers | 100 |
| Cost Allocation | 30 |
| Database | 70 |
| Network | 100 |
| Observability | 30 |
| Pricing | 60 |
| Serverless | 40 |
| Storage | 130 |


## Recommended ship order

1. P0, Very High value, Low/Medium complexity, with Product Catalog support already extracted.
2. P0/P1 native CSP advisor imports, because AWS/Azure/GCP already compute part of the finding and customer trust is high.
3. Kubernetes request/node/namespace/PVC recommendations, because they deliver high value with Prometheus/Kubecost data.
4. AI token/GPU recommendations when the customer has LiteLLM/Portkey/LangSmith/Helicone/DCGM/W&B/run:ai or equivalent telemetry.
5. P2/P3 cleanup, governance, and low-dollar hygiene recommendations.

## Use cases imported from the attached DOCX

The attached `FinOps_CostVars_Tooling_v2.docx` has been incorporated into the Basic catalog where the data can be captured as deterministic metrics. The extracted advisories are configured as `CVAR-001` through `CVAR-043`; see `basic-costvars-advisory-mapping.md` for the advisory-to-`BR-*` recommendation ID map.

## Required PRD updates

- Resolve CSP-native recommendations as first-class provider Findings.
- Add AI aggregate usage and GPU telemetry to Basic scope.
- Make `basic-recommendation-catalog-global.csv` the required recommendation library.
- Add Product Catalog browse/review requirements.
- Add full integration setup and customer telemetry-cost requirements.
- Add acceptance criteria for recommendation onboarding, signal coverage, provider-native imports, and AI metric ingestion.
