# Operations guide: Azure GPU Compute Recommendations (Support + Troubleshooting)

## 1. What the product does (plain language)
This feature helps customers **reduce Azure GPU compute costs** by:
- Connecting their Azure scope (tenant/subscriptions)
- Pulling inventory + required telemetry
- Generating recommendations (rightsizing, idle shutdown, autoscale, Spot, commitments, AKS packing, cleanup)
- Showing the recommendation with **evidence** (“metrics used”) so it’s explainable

## 2. What customers must do (prerequisites)
- Create a **service principal** (App Registration)
- Assign roles:
  - `Reader`
  - `Monitoring Reader`
- (Often required) enable GPU telemetry export so GPU utilization can be queried

If GPU utilization is missing, we can still show partial recommendations and the readiness view must indicate why.

## 3. Key customer-facing states and what they mean

### 3.1 Not onboarded
- Symptoms: Recommendations page shows “Connect Azure”
- Action: guide customer through onboarding wizard

### 3.2 Disconnected
- Symptoms: Readiness shows disconnected; validation fails
- Likely causes:
  - Invalid client secret / expired cert
  - Wrong tenant/client ID
  - SP missing required roles
  - Conditional access / policy blocking token
- Ops actions:
  - Check validation logs (token acquisition)
  - Confirm roles applied at correct subscription scope
  - Ask customer to rotate secret if expired

### 3.3 Degraded / partial coverage
- Symptoms: “Partial GPU metric coverage”, some recommendation types blocked
- Likely causes:
  - GPU utilization metrics not available
  - AKS/AML/Batch activity signals not configured
  - Telemetry flowing but missing dimensions (node/pool mapping)
- Ops actions:
  - Confirm which metrics are missing (coverage report)
  - Provide the telemetry enablement guide; confirm exporter/agent paths
  - Verify metrics API queries return data for at least one resource

### 3.4 Connected / ready
- Symptoms: full recommendations visible
- Ops actions:
  - Monitor ingestion freshness and rule evaluation freshness

## 4. Common customer tickets (symptoms → root causes → resolution)

### Ticket A: “Stuck on Collecting metrics”
- Root causes:
  - Not enough history yet (< 7–14 days)
  - Metrics pulls failing silently
  - Time range mismatch (timezone/UTC) in query window
- Resolution:
  - Verify metrics pull job succeeds and writes normalized metrics
  - Confirm lookback window and schedule cadence
  - Confirm lastMetricsPullAt is updating

### Ticket B: “GPU utilization is always missing”
- Root causes:
  - Azure Monitor Metrics doesn’t expose GPU util by default for that resource type
  - Customer hasn’t enabled guest-level GPU telemetry export
  - Wrong metric namespace/metric name for that SKU/service
- Resolution:
  - Identify resource types affected (VM vs AKS)
  - Ask customer to enable approved telemetry (agent/exporter)
  - Validate metrics existence for a single resource via sample query

### Ticket C: “Recommendations don’t match what we see”
- Root causes:
  - Customer uses custom thresholds/SLAs not captured
  - Metrics aggregation mismatch (avg vs p95)
  - Incomplete activity signal (jobs/pods) causing false “idle”
- Resolution:
  - Use evidence view to compare derived stats and rule evaluation
  - Verify activity signal sources; adjust gating thresholds as policy

### Ticket D: “Access denied / 403”
- Root causes:
  - Missing Monitoring Reader role
  - Scope mismatch (subscription not included)
  - RBAC propagation delay
- Resolution:
  - Confirm subscription IDs in connection scope
  - Confirm roles assigned at the right scope
  - Retry after propagation; rerun validate

### Ticket E: “Too many API calls / throttling”
- Root causes:
  - Large subscription scopes + frequent cadence
  - Missing batching/caching
- Resolution:
  - Increase cadence (e.g., 60 min)
  - Implement batching and backoff
  - Stagger schedules by subscription

### Ticket F: “Secret expired / rotated”
- Root causes:
  - Client secret expired
  - Key Vault reference changed permissions
- Resolution:
  - Re-run validation; show credential expiry warnings
  - Guide customer to rotate secret/cert

## 5. Operational dashboards (recommended)
- Connection counts by health (connected/degraded/disconnected)
- Job success/failure:
  - InventorySyncJob
  - MetricsPullJob
  - EvaluateRecommendationsJob
- Freshness:
  - lastInventorySyncAt
  - lastMetricsPullAt
  - lastRecommendationsEvaluatedAt
- Coverage distribution:
  - % resources with GPU metrics by subscription/service
- API error rates (Azure Monitor 4xx/5xx, throttling)

## 6. Alerts (recommended)
- Connection health changed to disconnected
- Metrics pull failures > N in a row
- Inventory sync stale > 36 hours
- Recommendation evaluation stale > 4 hours
- Throttling errors above threshold

## 7. Support runbook (triage steps)
1. Identify customer orgId and connectionId
2. Check readiness payload:
   - health, blockers, coverage, last pull timestamps
3. Check validation logs:
   - token acquisition, inventory query, metrics query
4. Check job logs:
   - ingestion pipeline (inventory/metrics), normalization, evaluation
5. Confirm data presence:
   - inventory contains target resourceId(s)
   - metrics exist for required metricNames in the relevant windows
6. Confirm evidence:
   - verify rule version and derived statistics

## 8. Information to request from customer in tickets
- Tenant ID + subscription ID(s) in scope
- Whether they serve the workload via VM/AKS/AML/Batch
- Whether GPU telemetry is enabled (and which method)
- Example resourceId(s) where metrics are missing
- Time window when they observed the issue


