# Basic Recommendation UI Flow Simulation Review

## Scope

This review simulates the Basic recommendation configuration flow as if a product/FinOps author configured the global Basic recommendation catalog one row at a time from the UI.

The simulated flow is:

1. Load the recommendation from `basic-recommendation-catalog-global.csv`.
2. Map `recommendation_type` to a visible UI action type.
3. Map `sub_category` to a wizard resource type.
4. Bind `primary_metrics`.
5. Bind `baseline_thresholds`.
6. Bind `product_catalog_dependency`.
7. Bind `compatibility_group`.
8. Resolve the savings formula.
9. Identify whether the row can be configured in the UI or needs backend/API work.

## Validation Result

- Total rows checked: 1,030.
- Rows with missing CSV fields: 0.
- Rows with unsupported action type: 0.
- Rows without compatibility group: 0.
- Rows without metrics: 0.
- Rows without thresholds: 0.
- Rows now visible in UI: 1,030, through the `Global Rec Library` tab.

## Action Type Coverage

- `BudgetReview`: 80 rows.
- `CommitmentReview`: 30 rows.
- `DeleteOrphan`: 160 rows.
- `LicenseReview`: 10 rows.
- `ModelRoute`: 170 rows.
- `RightsizeSku`: 260 rows.
- `SchedulePause`: 120 rows.
- `Shutdown`: 60 rows.
- `SpotReview`: 20 rows.
- `TagFix`: 20 rows.
- `TierMove`: 90 rows.
- `VolumeTypeSwap`: 10 rows.

All action types above are now present in the UI action picker or handled by the catalog validation/import layer.

## Compatibility Group Coverage

- `ai.model.same-modality-context-window-and-slo-tier`: 250 rows.
- `compute.gpu.same-accelerator-architecture`: 140 rows.
- `network.managed-service.same-provider-region-and-routing-domain`: 100 rows.
- `compute.vm.same-architecture-family`: 90 rows.
- `container.k8s.same-node-pool-architecture`: 90 rows.
- `data.managed-service.same-engine-edition-and-ha-model`: 70 rows.
- `ai.artifact.same-format-storage-and-retention-policy`: 50 rows.
- `pricing.commitment.same-provider-region-family-and-os`: 50 rows.
- `compute.serverless.same-runtime-plan`: 40 rows.
- `storage.object.same-bucket-storage-class-policy`: 40 rows.
- `governance.metadata.not-a-resource-move`: 30 rows.
- `observability.telemetry.same-signal-pipeline-and-retention-policy`: 30 rows.
- `storage.block.same-volume-performance-family`: 30 rows.
- `storage.backup.same-snapshot-service-and-retention-policy`: 20 rows.

## Gaps Found and Fixed

### Product Catalog filters were not discoverable

Gap: The dedicated Product Catalog tab had a small filter row and only showed a few sample SKU rows. A user could not easily see extracted product types or understand that AWS/Azure/GCP coverage existed by product family.

Fix: The Product Catalog tab now has a visible `Catalog Filters` panel with reset, provider, category, sub-category, region, pricing, product type, compatibility group, and search filters.

### Product types were not visible

Gap: Extracted product types from `basic-product-catalog-coverage.md` were documented but not visible in the SPA.

Fix: Added a `Product Type Browser` to the Product Catalog tab. It shows AWS, Azure, and GCP product types, entries, regions, categories, sub-categories, and compatibility groups.

### Workload compatibility was missing

Gap: The UI could compare source/target rates but did not define whether a workload can safely move from one product/SKU to another.

Fix: Added `compatibility_group` to every recommendation catalog row and `compatibilityGroupId` to Product Catalog UI rows. Movement recommendations are now scoped by group, for example VM same architecture, GPU same accelerator architecture, object storage same lifecycle policy, managed database same engine/HA model, and AI model same modality/SLO tier.

### The global recommendation library was not visible in the UI

Gap: The UI only showed the small `SAMPLE_RECOMMENDATIONS` set. The expanded global library existed in PM artifacts but could not be reviewed or configured from the SPA.

Fix: Added the `Global Rec Library` tab. It loads `basic-recommendation-catalog-global.csv`, shows all rows, provides filters, shows definition/benefits/advisory ID/metrics/thresholds/formulas/Product Catalog dependencies/compatibility groups, and allows a selected row to be imported as a draft.

### Some catalog metrics were not selectable in the wizard

Gap: The authoring wizard's metric picker only allowed hard-coded CSP/FinOps metric names. Catalog metrics such as `p95_cpu_pct`, `token_cost_usd`, `gpu_sm_util_pct`, or provider/SaaS-specific canonical metrics could be blocked until the backend Signal Catalog shipped.

Fix: Added a `Manual Signal Catalog Metric` section in Step 3. A user can now add any canonical metric name, unit, and field mapping, which allows all catalog rows to be configured while backend signal mapping matures.

### No bulk validation of UI configurability

Gap: There was no way to see whether each recommendation row had the fields required for the UI flow.

Fix: Added per-row `UI Flow Simulation` in the `Global Rec Library` detail panel and summary counters for loaded rows, configurable rows, action gaps, resource gaps, and group gaps.

## Remaining Backend/Product Gaps

- The UI can configure/import all 1,030 rows, but production still needs backend APIs for bulk import, versioning, approvals, run scheduling, and tenant overrides.
- Manual Signal Catalog metric entry is a UI bridge. Production should replace it with canonical signal search, schema validation, and provider field binding.
- Product Catalog product types are visible in the SPA, but live Product Catalog APIs must supply the full SKU/meter list, freshness, and compare candidates.
- Compatibility groups are defined at the template/product-type level. Production target selection must enforce them server-side, not only in the UI.
- Real backtests still require historical metric/billing data. The current UI validation proves configurability, not tenant-specific recommendation accuracy.
