# FinOps FinOps – Cost Advisory: Product Execution Plan

This document outlines a phased plan to build and ship **Extended Cost Recommendations** as a major competitor in the Cloud Cost Management SaaS ecosystem.

---

## Goals

1. **Master catalog**: Maintain a single source of truth for all cost and performance recommendations (this repo). Only **practical, feasible** advisories (feasibility = Practical; optionally Specialized when stack supports it) are built in the final product.
2. **CSP + SaaS coverage**: **Public CSPs** (AWS, Azure, GCP, OCI) in `csp_*` columns; **SaaS competitors** (Flexera, Apptio, Harness, Datadog, CloudZero, Vantage, CloudHealth, nOps, Spot, ProsperOps, etc.) in `saas_*` columns.
3. **Prioritization**: Based on (1) **top problems** (problem_severity), (2) **% savings achievable** (savings_pct_typical), (3) **complexity overall** (implementation_complexity). priority_score and savings_priority_rank reflect this.
4. **Governance**: Policies in **governance_policies.csv** are **design/reference only**; how to create and enforce these policies will be built later.
5. **Performance → savings**: Use **performance_gain_type** (Efficiency | Error reduction | Both) and **performance_gain_parameter** to quantify or approximate gains (e.g. efficiency %, incident reduction, deferred scale-up).

---

## Phase 1: Foundation (Weeks 1–4)

| # | Task | Owner | Output |
|---|------|--------|--------|
| 1.1 | Finalize schemas of all three CSVs with stakeholders (Product, Engineering, FinOps) | PM | Signed-off column definitions |
| 1.2 | Populate **recommendations_master.csv** with full list; run **feasibility checks** — only Practical (and optionally Specialized) in implementation backlog | PM / Analyst | Master list with feasibility, CSP/SaaS flags |
| 1.3 | Map each recommendation to rules in **recommendation_rules_metrics.csv**; add trend_days, metric_source, native_api_available, feasibility | Engineering | Rule–recommendation mapping |
| 1.4 | Assign **priority_score** from **top problems + % savings + complexity** per rule (workshop with Eng + FinOps) | PM | Prioritized rule list |
| 1.5 | Document **performance_gain_type** and **performance_gain_parameter** for each performance advisory (efficiency vs error reduction) | FinOps / PM | One-pager in README or docs |

**Exit criteria**: Master list complete; every cost recommendation has at least one rule; priorities and complexity agreed.

---

## Phase 2: Rule Engine & Data (Weeks 5–10)

| # | Task | Owner | Output |
|---|------|--------|--------|
| 2.1 | Implement ingestion of CSP-native recommendations (AWS CE, Azure Advisor, GCP Recommender) into Recommendations DB | Engineering | Connectors + normalized model |
| 2.2 | Implement FinOps advisory rules from **recommendation_rules_metrics.csv** (metrics, trigger, trend window) | Engineering | Rule engine v1 |
| 2.3 | Ensure metrics are sourced per **metric_source** (native API vs third-party); document gaps | Engineering | Metrics sourcing doc |
| 2.4 | Apply **hiding rules** (user vs global) and **action point rules** (ageing, type, escalation) per New Cost Advisory Flow | Engineering | Configurable visibility and action creation |
| 2.5 | Use **governance_policies.csv** as **design/reference**; design policy-creation flow for later build | Engineering / PM | Policy design doc; implementation deferred |

**Exit criteria**: CSP + FinOps recommendations in one place; rules executable; governance policies documented as reference.

---

## Phase 3: UX & Action Lifecycle (Weeks 11–16)

| # | Task | Owner | Output |
|---|------|--------|--------|
| 3.1 | Recommendations UI: list/detail with recommendation type (cost vs performance), savings estimate, CSP source | Product / Eng | UI for viewing recommendations |
| 3.2 | Action point creation from recommendation; link to grace period and escalation (L1/L2) per flow | Engineering | Action point lifecycle |
| 3.3 | Email digest (daily) and in-app notifications for new/high-priority recommendations | Engineering | Notifications |
| 3.4 | Approval / Postpone / Cancel flows with audit trail and “Action Item Closed” state | Engineering | Full journey in product |
| 3.5 | Reporting: savings realized, recommendations acted upon, open action items by owner | Product / Eng | Reports and dashboards |

**Exit criteria**: End-to-end journey from recommendation to action implemented in product.

---

## Phase 4: Governance & Scale (Weeks 17–22)

| # | Task | Owner | Output |
|---|------|--------|--------|
| 4.1 | Design policy-creation flow using **governance_policies.csv**; implement when roadmap allows | Engineering / PM | Policy creation spec |
| 4.2 | Add OCI and any additional CSPs to master list and connectors | Engineering | Multi-CSP parity |
| 4.3 | **Performance recommendations**: Implement 2–3 DB/middleware rules; publish “savings equivalent” methodology | Engineering / PM | Performance advisories with estimated impact |
| 4.4 | Competitive matrix: FinOps vs Flexera, Apptio, Harness, Datadog, CloudZero, Vantage, etc. using **saas_*** columns (public CSPs in **csp_***) | PM / Marketing | Competitive one-pager |
| 4.5 | Customer success: track “recommendations viewed / acted / savings realized” and refine priority and complexity | CS / PM | Feedback loop and iteration |

**Exit criteria**: Governance policies in use; multi-CSP; performance advisories with clear value story; competitive positioning documented.

---

## Phase 5: Optimization & Expansion (Ongoing)

- **Quarterly**: Review **recommendations_master.csv** for new CSP/SaaS advisories; update CSVs and README.
- **Per release**: Add new rules to **recommendation_rules_metrics.csv**; keep **governance_policies.csv** aligned with product.
- **Continuous**: Recalibrate **priority_score** using **top problems + % savings + complexity**; update feasibility when capabilities change.

---

## Dependencies & Risks

| Dependency | Mitigation |
|------------|------------|
| Access to CSP cost/usage and recommendation APIs | Use existing FinOps integrations; document API limits and fallbacks. |
| Quality of utilization metrics for rightsizing | Rely on native APIs where possible; clarify “native_api_available” in rules CSV. |
| Performance recommendation savings are indirect | Publish methodology (e.g. “efficiency gain → deferred scale-up”); use ranges, not point estimates. |
| Governance policies require customer-specific thresholds | Ship with defaults; allow overrides per tenant/tag. |

---

## Success Metrics

- **Coverage**: % of recommendations in master list available in product (target: 80%+ for cost-saving).
- **Adoption**: % of recommendations acted upon within 90 days (target: improve quarter over quarter).
- **Savings**: Reported savings from implemented recommendations (track by recommendation_id).
- **Competitive**: Number of recommendations where FinOps is “Yes” vs. key competitors (table in README or docs).

---

## Repository Maintenance

- **cost_advisory/** is the single source of truth for recommendation and policy definitions.
- All changes to master list, rules, or policies go through this folder; product and rule engine consume these CSVs (or derived config).
- Keep README and this execution plan updated with each phase completion and schema changes.
