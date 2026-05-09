# Basic Recommendation Catalog - Global Recommendation Library

This document explains how to use the expanded Basic engine recommendation library. The original seed remains in `basic-recommendation-catalog-500.csv`; the UI now loads `basic-recommendation-catalog-global.csv`, which contains 1,030 recommendation definitions across CSP-native, SaaS benchmark, AI CostVars, Kubernetes, Product Catalog, and FinOps-authored Basic rules.

## CSV columns

- `id`
- `recommendation_name`
- `category`
- `sub_category`
- `provider_scope`
- `source_provider`
- `recommendation_type`
- `priority`
- `end_user_value`
- `implementation_complexity`
- `primary_metrics`
- `baseline_thresholds`
- `lookback_window`
- `native_or_saas_data_source`
- `third_party_saas_options`
- `product_catalog_dependency`
- `compatibility_group`
- `onboarding_to_engine`
- `basic_engine_support`
- `notes_and_guardrails`
- `recommendation_definition`
- `expected_benefits`
- `configurator_showcase`
- `advisory_source`
- `advisory_id`
- `advisory_layer`

## Distribution by category

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

## Advisory mapping

The CostVars document `FinOps_CostVars_Tooling_v2.docx` is mapped into stable advisory IDs `CVAR-001` through `CVAR-043`. Each advisory family is configured as 10 rows: AWS, Azure, GCP, SaaS, and FinOps, each with standard and strict variants.

The advisory-to-recommendation ID map is in `basic-costvars-advisory-mapping.md`.

## How to use

1. Filter `priority = P0` and `implementation_complexity != High` for the first GA tranche.
2. Filter by `provider_scope` to build AWS, Azure, GCP, SaaS, or FinOps-native workstreams.
3. Bind `primary_metrics` to Signal Catalog canonical signals.
4. Bind `product_catalog_dependency` to Product Catalog pricing snapshots.
5. Bind `compatibility_group` to Product Catalog `compatibilityGroupId`; targets outside the group are blocked in Basic.
6. Configure the `baseline_thresholds` as tenant defaults, then allow per-tenant overrides.
7. Review `recommendation_definition` and `expected_benefits` with the configuring user before thresholds are edited.
8. Show `configurator_showcase` fields in the UI: advisory ID, signal coverage, unit-cost basis, thresholds, compatibility group, suppressions, owner, approval, backtest, and audit trail.
9. Backtest every selected row before activation.

## Compatibility group policy

Each recommendation now carries a `compatibility_group` so rightsizing and tier-change recommendations do not suggest unsafe cross-family movement. For example, CPU-only VM rightsizing stays within `compute.vm.same-architecture-family`, GPU movement stays within `compute.gpu.same-accelerator-architecture`, object storage lifecycle recommendations stay within `storage.object.same-bucket-storage-class-policy`, and AI model routing stays within `ai.model.same-modality-context-window-and-slo-tier`.

The detailed definitions and research basis are in `basic-product-compatibility-groups.md`.

## Threshold policy

The CSV thresholds are recommended baselines. Provider-native thresholds should be preserved when importing provider recommendations. FinOps-authored thresholds must be versioned, visible in audit logs, and overrideable by environment, SLO tier, business unit, and risk appetite.

## Basic vs Advanced boundary

Rows in this catalog are Basic when they can be evaluated from metric, billing, resource, gateway, or SaaS API data. If a recommendation requires traces, SQL plan analysis, learned workload classification, or cross-signal probabilistic inference, it must move to Advanced.
