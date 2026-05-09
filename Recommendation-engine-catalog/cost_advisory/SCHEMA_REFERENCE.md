# Cost Advisory – CSV Schema Reference

> Last updated to reflect full rebuild: technology column, SaaS accuracy review, agent requirements, native API names.



Quick reference for column meanings and allowed values.

---

## recommendations_master.csv

| Column | Type | Description | Example values |
|--------|------|-------------|----------------|
| recommendation_id | string | Unique ID. R### = standard; RS### = SaaS-specialized | R001, RS001 |
| recommendation_name | string | Short display name | Idle Compute Instance |
| recommendation_type | string | cost_saving \| performance \| saas_specialized | cost_saving |
| category | string | Top-level category | Compute, Storage, Database, Container |
| subcategory | string | Finer grouping | Virtual Machine, Disk, Serverless |
| **technology** | string | **Specific services/products this applies to** | EC2; Azure VM; GCE; OCI Compute |
| description | string | What the advisory is and how it is triggered | Free text |
| business_impact | string | Impact narrative: $ magnitude, frequency, customer segment | Free text |
| estimated_savings_notes | string | Formula or method for estimating savings | Free text |
| feasibility | string | **Practical** (auto-detectable from metrics) \| **Specialized** (needs DB/observability agent) \| **Reference** (architectural, not auto-triggerable) | Practical |
| feasibility_notes | string | Reason if Specialized or Reference | Free text |
| performance_gain_type | string | For performance type only: Efficiency \| Error reduction \| Both | Efficiency |
| performance_gain_parameter | string | For performance type: how to quantify the gain | Free text |
| csp_aws, csp_azure, csp_gcp, csp_oci | string | **Public CSP availability** — Yes \| No \| Partial — with native tool note | "Yes – native (Compute Optimizer)" |
| saas_finops | string | FinOps advisory availability | Yes |
| saas_flexera | string | Flexera One / Optima | Yes \| Partial \| blank |
| saas_apptio | string | Apptio (IBM Cloudability) | Yes \| Partial \| blank |
| saas_harness | string | Harness Cloud Cost Management (CCM) | Yes \| Partial \| blank |
| saas_datadog | string | Datadog Cloud Cost Management | Yes \| Partial \| blank |
| saas_cloudhealth | string | CloudHealth by VMware | Yes \| Partial \| blank |
| savings_pct_typical | string | Typical savings range or descriptor | 10-40%, 30-72%, High, Variable |
| problem_severity | string | How common and impactful: Top \| High \| Medium \| Low | Top |
| implementation_complexity | string | Effort to implement the recommendation action: Low \| Medium \| High | Low |
| priority_notes | string | Rationale for priority and build order | Free text |
| remarks | string | Special notes: SaaS-specialized marker, caveats, dependencies | "SaaS-specialized: Harness CCM proprietary" |
| documentation_link | string | URL to CSP or SaaS docs | Optional |

**CSP vs SaaS**: `csp_*` = public clouds with their native tooling. `saas_*` = Cloud Cost Management SaaS platforms.  
**SaaS-specialized rows** (RS001–RS008): recommendations only available in specific SaaS tools; `remarks` field contains "SaaS-specialized" marker.

---

## recommendation_rules_metrics.csv

| Column | Type | Description | Example values |
|--------|------|-------------|----------------|
| rule_id | string | Unique rule ID | RL001 |
| recommendation_id | string | FK to recommendations_master | R001 |
| rule_name | string | Display name for the rule | VM CPU Rightsizing |
| technology | string | Specific service/product (aligns with master) | EC2; Azure VM; GCE |
| metric_name | string | Metric(s) used to evaluate the rule | CPU Utilization %; Memory % |
| **metric_collection_method** | string | **How metrics are collected**: Native API \| CSP Recommender API \| Agent Required \| Metrics Server \| CSP Billing API \| DB Observability Agent \| Manual / Architecture Review | Native API |
| native_api_available | string | Yes \| No \| Partial (for the primary metric) | Yes |
| **native_api_name** | string | **Full API name / endpoint for fetching the metric** | CloudWatch GetMetricStatistics namespace=AWS/EC2 MetricName=CPUUtilization |
| **agent_required** | string | **Yes \| No \| Optional** — whether an agent must be installed | Optional |
| **agent_name** | string | **Name of the agent if required** | CloudWatch Agent; GCP Ops Agent; Azure Monitor Agent; Kubernetes Metrics Server; Oracle EM Agent |
| trend_days_required | integer | Minimum days of metric history needed | 7, 14, 30 |
| rule_trigger | string | Exact condition that fires the recommendation | Avg CPU < 40% AND peak CPU < 60% for 14 days |
| feasibility | string | Practical \| Specialized \| Reference | Practical |
| savings_pct_typical | string | Typical savings range (aligns with master) | 10-40% |
| problem_severity | string | Top \| High \| Medium \| Low | Top |
| implementation_complexity | string | Low \| Medium \| High | Low |
| priority_score | integer | 1–5 (1 = highest; derived from severity + savings + complexity) | 1 |
| savings_priority_rank | integer | Rank ordering by estimated savings impact | 1 |
| notes | string | Engineering implementation notes and caveats | Free text |

**metric_collection_method values:**
- `Native API` — standard CSP service metrics API; no agent installation required
- `CSP Recommender API` — consume a pre-built ML recommendation from the CSP (Cost Optimizer, GCP Recommender, Azure Advisor, OCI Cloud Advisor)
- `Agent Required (CloudWatch Agent)` — requires AWS CloudWatch Agent installed on the instance (for memory, disk, processes)
- `Agent Required (Ops Agent)` — requires GCP Ops Agent installed (memory, disk)
- `Agent Required (Azure Monitor Agent)` — requires Azure Monitor Agent or Log Analytics Agent (memory, disk, processes)
- `Metrics Server` — requires Kubernetes Metrics Server deployed in cluster
- `CSP Billing API` — uses billing export / Cost and Usage Report for coverage/commitment analysis
- `DB Observability Agent` — requires Oracle Enterprise Manager or AWR access; not available via CSP native APIs
- `Manual / Architecture Review` — cannot be auto-triggered; requires human review

**Priority**: Derived from (1) problem_severity (top problems = most customers affected), (2) savings_pct_typical (higher % = higher priority), (3) implementation_complexity (lower = higher priority for early builds).

---

## governance_policies.csv

| Column | Type | Description | Example values |
|--------|------|-------------|----------------|
| policy_id | string | Unique ID | POL001 |
| policy_name | string | Short name | Idle VM Auto-Stop |
| policy_type | string | Preventive \| Detective \| Corrective | Preventive |
| description | string | What the policy does | Free text |
| applies_to_categories | string | Categories or recommendation IDs | Compute; Virtual Machine |
| reduces_cost | string | Yes \| No \| Indirect | Yes |
| implementation_notes | string | How to implement | Free text |
| status | string | **Design / Reference** — policy creation to be built later | Design / Reference |

Governance policies are **design/reference only** for now; how to create and enforce them will be built later.
