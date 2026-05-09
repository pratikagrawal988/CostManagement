# Basic Recommendation Engine - Integration Framework and Setup Guide

## Purpose

This guide defines how the Basic engine connects to CSPs, CSP-native recommenders, billing exports, Kubernetes tooling, third-party FinOps SaaS, Product Catalog sources, and rule-based AI cost telemetry.

## Provider Registry manifest

Each integration must declare: `provider_id`, `category`, `auth`, `scopes`, `signals`, `recommendation_imports`, `health_probe`, `rate_limits`, `cost_model`, and `setup_steps`.

## Setup flow

1. Choose provider from Integration Catalog.
2. Review required permissions and customer-side cost estimate.
3. Enter credentials and scopes.
4. Run permission test.
5. Estimate metric volume, API calls, storage/query costs, and SaaS license dependency.
6. Run historical backfill.
7. Show signal coverage by recommendation category.
8. Enable only recommendation definitions with sufficient signal coverage.
9. Run first backtest and publish to shadow.

## AWS setup

Required details: payer/linked account IDs, IAM role ARN, external ID, region allowlist, CUR bucket/prefix/report, Compute Optimizer/Cost Optimization Hub status, optional CloudWatch agent and GPU/DCGM status.

Permissions: CloudWatch metric read, EC2/RDS/EBS/ELB/ASG/EKS/Lambda describe/list, Compute Optimizer read/export, Cost Explorer read, Pricing read, S3 CUR read, Athena/Glue if CUR queried via Athena.

Customer costs/challenges: CloudWatch custom/detail metrics, API quotas, CUR S3 storage, Athena scans, memory metrics needing agent, GPU metrics needing DCGM/exporters.

## Azure setup

Required details: tenant ID, subscription IDs or management group, app registration, billing scope, Cost Export storage account/container, Advisor enabled status.

Permissions: Reader, Monitoring Reader, Cost Management Reader, Advisor Reader, Storage Blob Data Reader, optional Log Analytics Reader.

Customer costs/challenges: Azure Monitor custom metrics, Log Analytics ingestion/retention, storage for Cost Exports, Advisor lag after rightsizing, guest metrics requiring AMA/DCR, Retail Prices API mapping for global/zone products.

## GCP setup

Required details: org/folder/project IDs, service account or WIF, billing account, BigQuery Billing Export dataset/table, Recommender API enabled, Cloud Billing Catalog API key.

Permissions: recommender viewer, monitoring viewer, cloud asset viewer, billing export BigQuery read, billing viewer, optional container/logging viewer.

Customer costs/challenges: BigQuery storage and scan cost, Cloud Monitoring read quotas, GCP pricing API key/service enablement, project/region-specific recommenders, memory/GPU metrics needing Ops Agent or DCGM.

## Kubernetes setup

Supported sources: Kubernetes API, kube-state-metrics, Prometheus/Thanos/Mimir, Kubecost/OpenCost, Datadog, Cloudability containers.

Required data: cluster ID, provider account mapping, namespace/workload labels, CPU/memory requests and usage, node SKU, PVC class/size, optional GPU allocation.

Customer costs/challenges: Prometheus cardinality, agent footprint, retention window, Kubecost billing integration requirement.

## AI and LLM setup

Basic supports AI recommendations only from deterministic aggregate metrics. Supported sources: OpenAI usage/cost APIs, Azure OpenAI via Azure Monitor/Cost Management, Bedrock via CUR/CloudWatch, Vertex/Gemini via billing export, LiteLLM, Portkey, Helicone, LangSmith, Langfuse, W&B, MLflow, DCGM, run:ai, vector DB APIs.

Required metrics: prompt tokens, completion tokens, cached tokens, model, project, user, service tier, request count, retry count, 429 rate, latency, embedding calls, cache hit rate, GPU utilization, GPU memory, MIG profile, checkpoint size/count, warm replicas, concurrency, KV cache hit rate.

Customer costs/challenges: usage API delay, limited attribution without gateway, prompt privacy, GPU exporter cardinality, SaaS plan limits for export granularity.

## Third-party SaaS provider matrix

| Provider | Data provided | Setup |
|---|---|---|
| CloudHealth | Rightsizing, zombie resources, commitments, policies | API token, org/account mapping, reports |
| Cloudability / Apptio | RI/SP, rightsizing, allocation, Kubernetes | API token, cloud mappings, business dimensions |
| Densify | VM/DB rightsizing, risk-aware fit scores | API credentials, connector/report export |
| Datadog | Cloud cost, K8s waste, custom metric/log/APM cost | API/app keys, cloud integration, org/site |
| Kubecost/OpenCost | K8s allocation, request sizing, idle namespace/cluster | endpoint/token, cluster mapping |
| Spot.io/CAST AI | Spot and node-pool optimization | API token, cloud/cluster account |
| Flexera/Snow | License and SaaS entitlement data | API token, entitlement exports |
| LiteLLM/Portkey/Helicone | LLM usage, retry, token, model cost | API token, project/key mapping |
| LangSmith/Langfuse | Agent/session/tool usage and cost | API token, project mapping |
| W&B/MLflow | Experiments, artifacts, sweeps, model registry | API token, workspace/project mapping |

## Health indicators

Every integration must show credential status, last sync, quota remaining, backfill lag, signal coverage, estimated customer telemetry cost, and recommendation categories enabled/blocked.
