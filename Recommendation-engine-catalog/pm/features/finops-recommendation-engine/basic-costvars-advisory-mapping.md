# Basic Recommendation Engine - CostVars Advisory Mapping

This document maps the advisories extracted from `FinOps_CostVars_Tooling_v2.docx` into the expanded Basic global recommendation catalog.

## Catalog output

- Source seed retained: `basic-recommendation-catalog-500.csv` (500 rows)
- Expanded PM catalog: `basic-recommendation-catalog-global.csv` (1030 rows)
- UI-local catalog copy: `web/CXP Optimization/FinOps Recommendation Engine/data/basic-recommendation-catalog-global.csv`
- CostVars advisory families configured: 43
- Each advisory family is configured as 10 provider/mode rows: AWS, Azure, GCP, SaaS, and FinOps, each with standard and strict variants.

## What the configurator should show

- Advisory ID and source document so users can trace why the rule exists.
- Plain-language recommendation definition and expected benefits before threshold editing.
- Required telemetry, source integration health, metric coverage, and missing-signal blockers.
- Editable threshold, lookback window, strict-mode behavior, and suppression policy.
- Savings or avoidance formula, Product Catalog dependency, unit-rate evidence, and compatibility group.
- Owner, approver, backtest result, audit history, and production-safe guardrails.

## Advisory mapping

| Advisory ID | Advisory from document | Layer | Configured recommendation IDs |
|---|---|---|---|
| `CVAR-001` | GPU Idle Time | Layer 1 - GPU & Compute - Idle · Utilisation · MIG · CPU stall · Spot waste | `BR-0501` - `BR-0510` |
| `CVAR-002` | GPU Utilisation Rate | Layer 1 - GPU & Compute - Idle · Utilisation · MIG · CPU stall · Spot waste | `BR-0511` - `BR-0520` |
| `CVAR-003` | GPU Memory Utilisation | Layer 1 - GPU & Compute - Idle · Utilisation · MIG · CPU stall · Spot waste | `BR-0521` - `BR-0530` |
| `CVAR-004` | GPU MIG Efficiency | Layer 1 - GPU & Compute - Idle · Utilisation · MIG · CPU stall · Spot waste | `BR-0531` - `BR-0540` |
| `CVAR-005` | CPU-GPU Stall | Layer 1 - GPU & Compute - Idle · Utilisation · MIG · CPU stall · Spot waste | `BR-0541` - `BR-0550` |
| `CVAR-006` | Spot Preemption Waste | Layer 1 - GPU & Compute - Idle · Utilisation · MIG · CPU stall · Spot waste | `BR-0551` - `BR-0560` |
| `CVAR-007` | Model Checkpoint Storage | Layer 2 - Memory & Storage - Checkpoints · Dataset I/O · Model weights · Vector DB · KV Cache | `BR-0561` - `BR-0570` |
| `CVAR-008` | Training Dataset I/O | Layer 2 - Memory & Storage - Checkpoints · Dataset I/O · Model weights · Vector DB · KV Cache | `BR-0571` - `BR-0580` |
| `CVAR-009` | Model Weight Storage | Layer 2 - Memory & Storage - Checkpoints · Dataset I/O · Model weights · Vector DB · KV Cache | `BR-0581` - `BR-0590` |
| `CVAR-010` | Vector DB Cost | Layer 2 - Memory & Storage - Checkpoints · Dataset I/O · Model weights · Vector DB · KV Cache | `BR-0591` - `BR-0600` |
| `CVAR-011` | KV Cache Efficiency | Layer 2 - Memory & Storage - Checkpoints · Dataset I/O · Model weights · Vector DB · KV Cache | `BR-0601` - `BR-0610` |
| `CVAR-012` | Redundant Data Copies | Layer 2 - Memory & Storage - Checkpoints · Dataset I/O · Model weights · Vector DB · KV Cache | `BR-0611` - `BR-0620` |
| `CVAR-013` | Egress Costs | Layer 3 - Network - Egress · InfiniBand · NVLink · API retries · Service mesh | `BR-0621` - `BR-0630` |
| `CVAR-014` | InfiniBand / RDMA Efficiency | Layer 3 - Network - Egress · InfiniBand · NVLink · API retries · Service mesh | `BR-0631` - `BR-0640` |
| `CVAR-015` | NVLink Fabric Efficiency | Layer 3 - Network - Egress · InfiniBand · NVLink · API retries · Service mesh | `BR-0641` - `BR-0650` |
| `CVAR-016` | API Retry Network Waste | Layer 3 - Network - Egress · InfiniBand · NVLink · API retries · Service mesh | `BR-0651` - `BR-0660` |
| `CVAR-017` | Service Mesh Overhead | Layer 3 - Network - Egress · InfiniBand · NVLink · API retries · Service mesh | `BR-0661` - `BR-0670` |
| `CVAR-018` | Cluster Idle Capacity | Layer 4 - Platform / Kubernetes - Cluster idle · Pod over-requests · Scheduling · Image pull · Observability self-cost | `BR-0671` - `BR-0680` |
| `CVAR-019` | Over-requested Pod Resources | Layer 4 - Platform / Kubernetes - Cluster idle · Pod over-requests · Scheduling · Image pull · Observability self-cost | `BR-0681` - `BR-0690` |
| `CVAR-020` | GPU Scheduling Fragmentation | Layer 4 - Platform / Kubernetes - Cluster idle · Pod over-requests · Scheduling · Image pull · Observability self-cost | `BR-0691` - `BR-0700` |
| `CVAR-021` | Container Image Pull Latency | Layer 4 - Platform / Kubernetes - Cluster idle · Pod over-requests · Scheduling · Image pull · Observability self-cost | `BR-0701` - `BR-0710` |
| `CVAR-022` | Observability Self-Cost | Layer 4 - Platform / Kubernetes - Cluster idle · Pod over-requests · Scheduling · Image pull · Observability self-cost | `BR-0711` - `BR-0720` |
| `CVAR-023` | Namespace / Tenant Policy Overhead | Layer 4 - Platform / Kubernetes - Cluster idle · Pod over-requests · Scheduling · Image pull · Observability self-cost | `BR-0721` - `BR-0730` |
| `CVAR-024` | Training Compute (FLOPs) | Layer 5 - Model Operations - Training FLOPs · Fine-tuning · Serving efficiency · Version bloat · Quantisation · Sweeps | `BR-0731` - `BR-0740` |
| `CVAR-025` | Fine-tuning Cost | Layer 5 - Model Operations - Training FLOPs · Fine-tuning · Serving efficiency · Version bloat · Quantisation · Sweeps | `BR-0741` - `BR-0750` |
| `CVAR-026` | Inference Serving Efficiency | Layer 5 - Model Operations - Training FLOPs · Fine-tuning · Serving efficiency · Version bloat · Quantisation · Sweeps | `BR-0751` - `BR-0760` |
| `CVAR-027` | Model Version Proliferation | Layer 5 - Model Operations - Training FLOPs · Fine-tuning · Serving efficiency · Version bloat · Quantisation · Sweeps | `BR-0761` - `BR-0770` |
| `CVAR-028` | Quantisation Efficiency | Layer 5 - Model Operations - Training FLOPs · Fine-tuning · Serving efficiency · Version bloat · Quantisation · Sweeps | `BR-0771` - `BR-0780` |
| `CVAR-029` | Hyperparameter Sweep Cost | Layer 5 - Model Operations - Training FLOPs · Fine-tuning · Serving efficiency · Version bloat · Quantisation · Sweeps | `BR-0781` - `BR-0790` |
| `CVAR-030` | Prompt Token Cost | Layer 6 - Token & API - Prompt · Completion · Context bloat · Embeddings · Agent loops · Routing · Rate limits | `BR-0791` - `BR-0800` |
| `CVAR-031` | Completion Token Cost | Layer 6 - Token & API - Prompt · Completion · Context bloat · Embeddings · Agent loops · Routing · Rate limits | `BR-0801` - `BR-0810` |
| `CVAR-032` | Context Window Bloat | Layer 6 - Token & API - Prompt · Completion · Context bloat · Embeddings · Agent loops · Routing · Rate limits | `BR-0811` - `BR-0820` |
| `CVAR-033` | Embedding Call Cost | Layer 6 - Token & API - Prompt · Completion · Context bloat · Embeddings · Agent loops · Routing · Rate limits | `BR-0821` - `BR-0830` |
| `CVAR-034` | Agent Loop Token Waste | Layer 6 - Token & API - Prompt · Completion · Context bloat · Embeddings · Agent loops · Routing · Rate limits | `BR-0831` - `BR-0840` |
| `CVAR-035` | Multi-model Routing | Layer 6 - Token & API - Prompt · Completion · Context bloat · Embeddings · Agent loops · Routing · Rate limits | `BR-0841` - `BR-0850` |
| `CVAR-036` | Rate Limit Retry Waste | Layer 6 - Token & API - Prompt · Completion · Context bloat · Embeddings · Agent loops · Routing · Rate limits | `BR-0851` - `BR-0860` |
| `CVAR-037` | RAG Pipeline Cost | Layer 7 - Application Layer - RAG pipelines · DB query stalls · API latency · Guardrails · Evals · Warm pools · Shadow models | `BR-0861` - `BR-0870` |
| `CVAR-038` | Slow DB Query to GPU Stall | Layer 7 - Application Layer - RAG pipelines · DB query stalls · API latency · Guardrails · Evals · Warm pools · Shadow models | `BR-0871` - `BR-0880` |
| `CVAR-039` | API Latency to Cost Amplifier | Layer 7 - Application Layer - RAG pipelines · DB query stalls · API latency · Guardrails · Evals · Warm pools · Shadow models | `BR-0881` - `BR-0890` |
| `CVAR-040` | Guardrail Processing Cost | Layer 7 - Application Layer - RAG pipelines · DB query stalls · API latency · Guardrails · Evals · Warm pools · Shadow models | `BR-0891` - `BR-0900` |
| `CVAR-041` | Inference Warm Pool Cost | Layer 7 - Application Layer - RAG pipelines · DB query stalls · API latency · Guardrails · Evals · Warm pools · Shadow models | `BR-0901` - `BR-0910` |
| `CVAR-042` | Evaluation Pipeline Cost | Layer 7 - Application Layer - RAG pipelines · DB query stalls · API latency · Guardrails · Evals · Warm pools · Shadow models | `BR-0911` - `BR-0920` |
| `CVAR-043` | Shadow Model Traffic Cost | Layer 7 - Application Layer - RAG pipelines · DB query stalls · API latency · Guardrails · Evals · Warm pools · Shadow models | `BR-0921` - `BR-0930` |

## Expanded catalog summary

### By category

- AI: 360 rows
- Compute: 110 rows
- Containers: 100 rows
- Cost Allocation: 30 rows
- Database: 70 rows
- Network: 100 rows
- Observability: 30 rows
- Pricing: 60 rows
- Serverless: 40 rows
- Storage: 130 rows

### By provider scope

- AWS: 206 rows
- Azure: 206 rows
- FinOps: 206 rows
- GCP: 206 rows
- SaaS: 206 rows

### By recommendation action

- BudgetReview: 80 rows
- CommitmentReview: 30 rows
- DeleteOrphan: 160 rows
- LicenseReview: 10 rows
- ModelRoute: 170 rows
- RightsizeSku: 260 rows
- SchedulePause: 120 rows
- Shutdown: 60 rows
- SpotReview: 20 rows
- TagFix: 20 rows
- TierMove: 90 rows
- VolumeTypeSwap: 10 rows

## Notes

- The original 500-row seed remains unchanged as a stable reference.
- The global catalog adds columns for `recommendation_definition`, `expected_benefits`, `configurator_showcase`, `advisory_source`, `advisory_id`, and `advisory_layer`.
- `CVAR-*` rows come from the CostVars document. `GLOBAL-*` rows cover additional provider-native recommendation patterns not explicitly listed in that document.
