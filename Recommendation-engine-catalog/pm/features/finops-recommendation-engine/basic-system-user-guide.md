# Basic Recommendation Engine - System User Guide

## Purpose

This guide explains how customers, FinOps admins, and FinOps operators use the Basic Recommendation Engine end to end. It covers setup, recommendation selection, authoring, backtest, activation, findings review, action approval, and realized-savings reconciliation.

## 1. Connect data sources

Start in the Integrations area.

1. Choose one or more providers: AWS, Azure, GCP, Kubernetes, Product Catalog, third-party SaaS, or AI usage/GPU telemetry.
2. Review the generated setup guide for required permissions and expected customer-side costs.
3. Enter credentials and select account/subscription/project/cluster scope.
4. Run permission test.
5. Run health probe.
6. Review estimated API calls, metric volume, storage/query cost, and backfill duration.
7. Start historical backfill.
8. Wait for signal coverage summary.

An integration is not considered usable until it has:

- Healthy credentials.
- Successful backfill.
- Signal coverage mapped to at least one recommendation category.
- Product Catalog pricing coverage for savings-producing actions.

## 2. Review Product Catalog coverage

Open Product Catalog before enabling cost-saving recommendations.

Use filters:

- Provider.
- Category.
- Sub-category.
- Region.
- SKU / meter search.
- Pricing model.
- OS/license.
- Technical specs.
- Recommendation eligibility.
- Freshness.

Use this view to validate:

- Source SKU exists.
- Target SKU exists.
- Pricing snapshot is current.
- Region has rate coverage.
- Estimated savings can be defended during approval.

## 3. Select recommendations from the global library

Open the recommendation library backed by `basic-recommendation-catalog-global.csv`. The original 500-row seed remains available for comparison, but the UI uses the expanded global catalog.

Recommended filters for the first enablement wave:

- `priority = P0`.
- `end_user_value in (Very High, High)`.
- `implementation_complexity in (Low, Medium)`.
- Provider scope matching connected integrations.
- Product Catalog dependency available.
- Advisory source/ID where available, especially `CVAR-*` rows from the CostVars tooling document.

Do not enable a recommendation whose required metrics are missing. The UI must show which metric or source is blocking activation.

## 4. Author or configure a rule

For FinOps-authored Basic rules:

1. Fill basic information: name, category, owner group, business justification.
2. Select scope: CSPs, accounts/subscriptions/projects, regions, environment, BU/cost center, tags.
3. Select signals from Signal Catalog.
4. Configure rule groups and thresholds.
5. Configure action type and SKU/tier/target parameters where relevant.
6. Review Product Catalog pricing basis.
7. Run backtest.

For imported native or SaaS recommendations:

1. Select import provider.
2. Select native recommendation types to import.
3. Map native finding types to FinOps action types.
4. Review sample imported findings.
5. Enable sync schedule.

## 5. Run backtest

Backtest is mandatory before activation.

Backtest output must show:

- Sample coverage.
- Hit count.
- Distinct resources.
- Estimated savings.
- Suppressed findings.
- Missing metric count.
- Data quality failures.
- Prior dismissal / false-positive overlap where available.

Promotion gates:

- Coverage must be at least 90%.
- Backtest must not be older than 7 days.
- Recommendation must produce at least one finding, unless overridden with justification.
- Savings-producing recommendations must have Product Catalog or billing-rate coverage.

## 6. Publish to shadow and activate

Recommended lifecycle:

1. Draft.
2. Backtest.
3. Shadow.
4. Review findings internally.
5. Activate.

Shadow mode validates that the recommendation is not noisy before it reaches end users.

## 7. Review findings

End users see normalized FinOps Findings regardless of source:

- FinOps-authored rule.
- AWS native recommendation.
- Azure native recommendation.
- GCP native recommendation.
- Third-party SaaS recommendation.
- AI aggregate metric recommendation.

Each Finding must show:

- Resource impacted.
- Owner / cost center / application.
- Evidence metrics.
- Thresholds that fired.
- Source provider.
- Estimated savings.
- Pricing snapshot.
- Risk and guardrails.
- Proposed action.

## 8. Approve and deliver actions

Basic supports manual and ITSM delivery.

Available Basic actions include:

- `Shutdown`.
- `RightsizeSku`.
- `SchedulePause`.
- `TierMove`.
- `DeleteOrphan`.
- `VolumeTypeSwap`.
- `CommitmentReview`.
- `TagFix`.
- `BudgetReview`.
- `ModelRoute`.
- `SpotReview`.
- `LicenseReview`.

Approvals must resolve to SSO groups, not free text. All decisions are written to the audit log.

## 9. Reconcile realized savings

After an action is applied, Reconciler runs at T+30, T+60, and T+90.

It compares:

- Pre-action baseline cost.
- Post-action observed cost.
- Usage-normalized counterfactual where possible.
- Product Catalog estimate.

Outcome status:

- `pending`.
- `realized`.
- `regressed`.
- `dismissed`.

The Recommendation detail view must show estimated vs realized savings and variance.

## 10. Operating model

FinOps PM owns the seed recommendation library and thresholds.

Platform Engineering owns:

- Advisory Service.
- Provider Registry.
- Signal Catalog.
- Product Catalog.
- Reconciler.

Customer FinOps admins own:

- Integration credentials.
- Scope selection.
- Threshold overrides.
- Approval group mappings.

Resource owners own:

- Finding approval.
- Action execution where manual.
- Dismissal reason accuracy.

## 11. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Recommendation cannot be enabled | Missing required metric or Product Catalog rate | Open signal coverage report and connect required integration |
| Backtest has zero findings | Rule too strict, scope too narrow, or insufficient history | Loosen thresholds, broaden scope, or extend lookback |
| Savings show stale-rate warning | Product Catalog refresh older than 7 days | Refresh catalog for provider/region |
| Native recommendations missing | Native advisor not enabled or API permissions missing | Re-run permission test and provider sync |
| AI recommendations unavailable | No LLM gateway/GPU/model telemetry connected | Connect supported AI usage or GPU integration |
| Reconciler skipped | Billing export missing or not backfilled | Configure billing export and rerun reconciliation |

