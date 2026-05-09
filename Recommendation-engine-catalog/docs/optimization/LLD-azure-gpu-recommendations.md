# LLD: Azure GPU Compute Recommendations (Onboarding + Ingestion + Advisory)

## 1. Overview
This LLD specifies:
- Data models (connection, readiness, metrics, recommendations, evidence)
- Backend endpoints and worker jobs
- Rule definitions (metrics + thresholds)
- UI behavior for gating and evidence display

## 2. Data models

### 2.1 AzureConnection
```json
{
  "id": "conn_123",
  "orgId": "org_abc",
  "cloudProvider": "azure",
  "name": "Azure - Prod subscriptions",
  "tenantId": "…",
  "subscriptionIds": ["…"],
  "resourceScopeFilters": {
    "includeResourceGroups": [],
    "excludeResourceGroups": [],
    "tagFilters": { "doNotOptimize": "true" }
  },
  "auth": {
    "type": "servicePrincipal",
    "clientId": "…",
    "credentialType": "keyVaultRef|clientSecret|certificate",
    "credentialRef": "kv://… or secretId://…"
  },
  "metricIngestion": {
    "method": "azureMonitorMetricsPull",
    "pollCadenceMinutes": 30,
    "lookbackDays": 30
  },
  "timestamps": { "createdAt": "…", "updatedAt": "…" }
}
```

### 2.2 ConnectionRuntimeState (Readiness)
```json
{
  "health": "disconnected|degraded|connected",
  "lastInventorySyncAt": "…",
  "lastMetricsPullAt": "…",
  "coverage": { "totalGpuResources": 24, "resourcesWithGpuMetrics": 12 },
  "blockingItems": [
    {
      "reason": "missingGpuMetrics|missingPermissions|insufficientData",
      "title": "…",
      "description": "…",
      "services": ["vm","aks","aml","batch"]
    }
  ]
}
```

### 2.3 ResourceCatalogItem
Keyed by Azure `resourceId`.
```json
{
  "resourceId": "/subscriptions/.../providers/Microsoft.Compute/virtualMachines/vm1",
  "orgId": "org_abc",
  "service": "vm|aks|aml|batch",
  "region": "eastus",
  "sku": "Standard_NC12s_v3",
  "tags": { "env": "prod", "owner": "ml-team" },
  "meta": { "rg": "rg-ml", "subscriptionId": "…" },
  "timestamps": { "seenAt": "…" }
}
```

### 2.4 NormalizedMetricPoint
```json
{
  "orgId": "org_abc",
  "provider": "azure",
  "resourceId": "…",
  "timestamp": "2025-12-19T10:00:00Z",
  "metricName": "gpu_utilization_pct|gpu_memory_utilization_pct|cpu_utilization_pct|running_state|workload_active|queue_depth|node_count|gpu_requested|gpu_allocatable",
  "value": 12.3,
  "unit": "Percent|Count|Hours|Boolean",
  "dimensions": { "service": "vm", "cluster": null, "node": null }
}
```

### 2.5 Recommendation
```json
{
  "id": "reco_123",
  "orgId": "org_abc",
  "type": "rightsize|idle_shutdown|autoscale|spot|commitment|aks_binpack|pattern_change|cleanup",
  "service": "vm|aks|aml|batch",
  "resourceId": "…",
  "title": "…",
  "description": "…",
  "status": "available|blocked|dismissed|accepted",
  "severity": "low|medium|high",
  "confidence": "low|medium|high",
  "estimatedSavingsMonthly": 1260,
  "currency": "USD",
  "parameters": {},
  "evidenceId": "ev_456",
  "timestamps": { "createdAt": "…", "evaluatedAt": "…" }
}
```

### 2.6 Evidence
```json
{
  "id": "ev_456",
  "orgId": "org_abc",
  "recommendationId": "reco_123",
  "window": { "start": "…", "end": "…", "lookbackDays": 30 },
  "rule": { "name": "RightSizeGpuVm", "version": "1.0", "expression": "…" },
  "metricsUsed": [
    { "metricName": "gpu_utilization_pct", "aggregation": "avg,p95", "derived": { "avg": 8, "p95": 22 } }
  ],
  "decision": { "triggered": true, "reason": "avg<15 and p95<40" }
}
```

## 3. Backend APIs

### 3.1 Connections
- `POST /api/connections/azure` create connection
- `GET /api/connections/azure` list
- `GET /api/connections/azure/{id}` get
- `PATCH /api/connections/azure/{id}` update
- `DELETE /api/connections/azure/{id}` delete

### 3.2 Validation / readiness
- `POST /api/connections/azure/{id}/validate`
  - Steps:
    - acquire token (AAD)
    - query sample inventory (Resource Graph / ARM)
    - query sample metrics (Azure Monitor Metrics)
  - Returns: `ConnectionRuntimeState`

### 3.3 Ingestion control
- `POST /api/connections/azure/{id}/enable-ingestion`
  - persists schedules and enables jobs

### 3.4 Recommendations & evidence
- `GET /api/recommendations/gpu-compute?status=available&service=vm&region=eastus`
- `GET /api/recommendations/{id}/evidence`

## 4. Worker jobs

### 4.1 InventorySyncJob
- cadence: daily + on-demand
- pulls resources in scope:
  - VM/AKS/AML/Batch inventory
  - tags and SKU metadata
- upserts into `ResourceCatalogItem`

### 4.2 MetricsPullJob (Azure Monitor Metrics API)
- cadence: 15–60 minutes
- queries a defined set of metrics per resource type
- writes raw points and triggers normalization

### 4.3 NormalizeJob
- maps provider-specific metric names → internal canonical metric names
- attaches dimensions (service, cluster/node/pool)
- stores in time-series store

### 4.4 EvaluateRecommendationsJob
- cadence: hourly (or event-driven after metrics ingest)
- reads cost baseline + inventory + metrics
- produces recommendations + evidence
- updates readiness coverage and blocking items

## 5. Rule definitions (default)

### 5.1 Rightsize GPU SKU
- window: 14–30 days
- metrics:
  - gpu_utilization_pct: avg, p95
  - gpu_memory_utilization_pct: p95
- trigger:
  - avg GPU util < 15% AND p95 GPU util < 40% AND p95 GPU mem < 50%
- output parameters:
  - currentSku, recommendedSku, resizeType, rationale

### 5.2 Idle shutdown/deallocate
- window: last 60–120 minutes
- metrics:
  - gpu_utilization_pct: time-series
  - workload_active: current/time-series
- trigger:
  - workload_active == 0 AND gpu_utilization_pct < 5% for ≥ 60–120 minutes
- output parameters:
  - action, idleWindowMinutes, scheduleSuggestion (optional)

### 5.3 Autoscale / scale-to-zero
- window: 7–14 days
- metrics:
  - queue_depth: time-series
  - node_count: time-series
- trigger:
  - long queue_depth==0 periods while node_count stays > 0
- output parameters:
  - currentMinNodes, recommendedMinNodes, currentMaxNodes, scaleRule

### 5.4 Spot suitability
- window: 7–30 days
- metrics/inputs:
  - gpu_hours_per_day (derived)
  - workload metadata: interruptible/retryable/checkpointing
- trigger:
  - interruptible=true AND retryable=true AND avg gpu_hours_per_day > 2–4

### 5.5 Commitment recommendation
- window: 30 days
- metrics:
  - running_hours per skuFamily/region
- trigger:
  - baseline usage ≥ 60–70% of hours with low variance

### 5.6 AKS bin-packing/scheduling
- window: 7 days
- metrics:
  - gpu_allocatable, gpu_requested (current)
  - gpu_utilization_pct (avg)
- trigger:
  - node_count high due to fragmentation; avg GPU per node < 35%

### 5.7 Pattern change (always-on → job-native)
- window: 14–30 days
- metrics:
  - idle_pct (derived from GPU util + activity)
- trigger:
  - idle_pct > 40–50% with bursty workload pattern

### 5.8 Cleanup orphans
- window: inventory snapshot
- inputs:
  - unattached disks/snapshots older than 30–90 days, not tagged retain

## 6. UI behaviors (implementation)
- **Readiness page** shows:
  - health + coverage + blockers from `ConnectionRuntimeState`
- **Recommendations page**:
  - show recommendation rows and allow “View metrics used”
  - block rows when requirements aren’t satisfied
  - evidence view reads `Evidence` payload and renders metrics + derived stats + rule text

## 7. Observability and audit
- Log all ingestion and evaluation job runs with correlation IDs.
- Store evidence versioned by rule version.
- Expose last-success timestamps and failure reasons in readiness.


