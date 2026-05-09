# Recommendation readiness & gating rules (GPU compute)

These are the general rules for **when the platform should show GPU compute recommendations** vs showing “collecting metrics” or “fix readiness”.

## Global gating rules

- **Data sufficiency**
  - Rightsizing / commitment: require **≥ 7–14 days** of metrics history per resource.
  - Near-real-time idleness: can use **last 60–120 minutes** of metrics.
- **Confidence**
  - Use both **avg** and **p95** (or p90) so recommendations aren’t driven by outliers.
- **Savings threshold**
  - Only show if projected savings ≥ **backend-configured** threshold (**$/month**) or ≥ **backend-configured % of spend**.
- **Actionability**
  - Don’t recommend Spot unless the workload is marked **interruptible** (user metadata).
- **Exclusions**
  - Exclude resources tagged `doNotOptimize=true` or in protected scopes.

## Readiness states (used by UI)

### 1) Not onboarded
- Condition: no Azure connection exists
- UI: show “Connect Azure” CTA

### 2) Connected but collecting history
- Condition: connection validated but < 7–14 days history
- UI: show “Collecting metrics” state; allow inventory-only recommendations

### 3) Degraded / partial coverage
- Condition: GPU metrics missing for a material portion of GPU resources (example threshold: < 80% coverage)
- UI: show available recommendations for covered resources; list blocked recommendation types

### 4) Connected / ready
- Condition: ≥ 80% GPU metric coverage and sufficient history
- UI: show full recommendation set


