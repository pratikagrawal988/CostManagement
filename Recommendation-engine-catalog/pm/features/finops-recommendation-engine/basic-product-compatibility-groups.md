# Basic Product Compatibility Groups

## Purpose

The Basic Recommendation Engine must not recommend a resource movement only because a target SKU is cheaper. A target must also be workload-compatible: the workload should be movable with normal provider resize, tier-change, or lifecycle operations without forcing a re-platforming project.

This document defines the compatibility group model now used by the Basic recommendation catalog and Product Catalog UI. Recommendation definitions carry `compatibility_group`, and Product Catalog entries carry `compatibilityGroupId`. A Basic rightsize, tier move, volume swap, model route, or commitment review can only recommend targets inside the same compatibility group unless an explicit migration workflow is selected.

## Research Summary

### Compute VM Rightsizing

AWS EC2 resizing is constrained by architecture, virtualization, ENA/NVMe driver readiness, Nitro/non-Nitro differences, network adapter support, and whether the instance is EBS-backed. A same-provider, same-architecture family is the safe Basic default. Cross-architecture moves such as x86 to Arm/Graviton, or Xen-era to Nitro-era without driver checks, should be treated as migration work rather than a simple Basic rightsize.

Azure VM resizing is constrained by local temporary disk presence, disk controller/architecture such as SCSI versus remote NVMe, SKU availability in the region and cluster, and sometimes deallocation requirements. The Basic grouping should keep candidates inside the same temp-disk and disk-architecture lane.

GCP supports machine-type changes for stopped instances, but excludes instances with Local SSD and instances in managed instance groups from the simple resize flow. GCP also distinguishes first/second generation machine-series moves from newer generation moves. Cross-generation moves to third generation and later should be migration work unless validated explicitly.

### GPU and Accelerator Workloads

GPU movements require stricter grouping than CPU-only VM moves. The target must preserve accelerator vendor, accelerator memory class, driver/CUDA compatibility, GPU count expectations, local SSD assumptions, and workload scheduling model. Basic should group GPU resources by accelerator architecture and memory class, not just by vCPU and RAM.

### Block Volumes

AWS EBS supports live modification across SSD volume types such as `gp2`, `gp3`, `io1`, and `io2`, but IOPS/throughput limits, modification frequency, and in-flight modification state must be checked. The same concept applies to Azure managed disk tiers and GCP persistent disk classes: movement should remain inside a storage-performance family unless a migration playbook exists.

### Object Storage Tiers

S3, Azure Blob, and GCS lifecycle transitions are compatible only when retrieval fees, minimum storage duration, archive rehydration, early deletion penalties, object lock/legal hold, last access data, and workload access patterns are acceptable. Basic can recommend lifecycle rules within a storage-class policy group; it should not blindly move hot objects to archive tiers.

### Managed Databases

Managed databases have engine, edition, HA/replica, storage, IOPS, license, maintenance window, and downtime constraints. AWS recommends validating allowed RDS modifications with provider APIs such as `DescribeValidDBInstanceModifications`. Azure SQL supports DTU/vCore and service-tier moves with brief connectivity impact, but tier and purchasing-model constraints still matter. Basic should group managed database moves by engine, edition, HA model, and service tier.

### AI Models and Token Routing

AI model routing is not SKU rightsizing. The compatible group is defined by modality, context window, latency/SLO tier, safety capability, data residency, and task quality threshold. A Basic `ModelRoute` can only propose a cheaper model inside the same capability lane unless a quality evaluation workflow has approved the route.

## Compatibility Group Definitions

| Group ID | Applies to | Compatible movement allowed | Hard blocks |
|---|---|---|---|
| `compute.vm.same-architecture-family` | VM rightsizing, VM generation replacement, dev/test schedule, VM spot review | Same provider, region availability, OS/license lane, architecture, hypervisor/driver readiness, temp disk/disk controller lane | x86 to Arm without migration; Local SSD or unsupported temp disk transition; missing ENA/NVMe/accelerated networking readiness |
| `compute.gpu.same-accelerator-architecture` | GPU idle, GPU rightsize, GPU spot review | Same accelerator vendor/family, GPU memory class, driver/CUDA lane, scheduler compatibility | CPU-only target; different GPU architecture without validation; local SSD dependency mismatch |
| `container.k8s.same-node-pool-architecture` | Kubernetes node/pod rightsizing | Same cluster, node OS/architecture, taints/tolerations, GPU labels, storage class assumptions | Cross-cluster moves; incompatible daemonset/node labels; missing autoscaler support |
| `compute.serverless.same-runtime-plan` | Function memory/concurrency/schedule recommendations | Same runtime, trigger type, plan model, region, concurrency semantics | Runtime migration; event trigger rewrite; plan migration without cold-start review |
| `storage.block.same-volume-performance-family` | Block volume type swap and disk rightsizing | Same provider, volume family, IOPS/throughput envelope, encryption/KMS, attachment mode | Lower IOPS/throughput than observed need; in-flight modification; unsupported live modification |
| `storage.object.same-bucket-storage-class-policy` | Object storage lifecycle/tier move | Same bucket/account policy, lifecycle rule support, minimum duration, retrieval-fee guardrail, object lock/legal hold check | Archive move with frequent access; early deletion penalty; legal hold/object lock |
| `storage.backup.same-snapshot-service-and-retention-policy` | Snapshot, AMI/image, backup retention cleanup | Same backup service, retention policy, legal hold, recovery point objective | Golden image, active restore dependency, compliance retention |
| `data.managed-service.same-engine-edition-and-ha-model` | RDS/SQL, NoSQL, cache, warehouse rightsizing | Same engine/edition, HA/replica model, maintenance window, storage/IOPS envelope, license lane | Engine migration; HA topology change; unsupported provider modification |
| `network.managed-service.same-provider-region-and-routing-domain` | NAT, load balancer, IP, CDN recommendations | Same provider, VPC/VNet/routing domain, region, protocol/capacity lane | Cross-region architecture change; DNS/client impact without rollout plan |
| `pricing.commitment.same-provider-region-family-and-os` | RI/SP/CUD/reservation review | Same provider, region/zone, family, OS/license, tenancy, term and utilization pool | Cross-provider commitment; incompatible OS/license or tenancy |
| `ai.model.same-modality-context-window-and-slo-tier` | LLM token/model routing | Same modality, context length, safety/quality tier, latency SLO, data residency | Quality downgrade without eval; different modality; residency or safety policy violation |
| `ai.artifact.same-format-storage-and-retention-policy` | Model artifacts, checkpoints, vector index storage | Same artifact format, restore path, retention policy, registry/storage backend | Active training dependency; restore path missing; compliance retention |
| `governance.metadata.not-a-resource-move` | Tag and budget actions | No resource movement; update metadata, ownership, budget, or policy only | Direct resource mutation |
| `observability.telemetry.same-signal-pipeline-and-retention-policy` | Metrics/log retention and cardinality recommendations | Same telemetry pipeline, retention class, compliance policy, query need | Audit log retention breach; missing SLO/incident dependency review |

## Product Catalog Rules

1. Product Catalog rows must include `compatibilityGroupId`.
2. Recommendation definitions must include `compatibility_group`.
3. Candidate targets are valid only when `source.compatibilityGroupId === target.compatibilityGroupId`.
4. Cross-group recommendations must be labelled as migration work and are not eligible for Basic auto-configuration.
5. Product Catalog compare views must show movement blockers before showing savings.
6. The Basic authoring wizard must support compatibility group selection for SKU, tier, volume, and model-route actions.

## UI Simulation Findings

The review of the current UI flow found these gaps:

- Product Catalog filters existed but were too subtle and only filtered a small SKU sample, not product types.
- Product types from the extracted catalog were not visible as first-class objects.
- There was no compatibility group parameter on recommendations or products.
- The recommendation catalog was documented but not loaded into the UI.
- The authoring wizard could only pick metrics that appeared in the hard-coded metric catalog, which blocked some catalog-defined metrics.
- The UI had no way to validate all templates for action type, resource type, metric, threshold, formula, Product Catalog dependency, and compatibility group coverage.

Fixes made:

- Added `compatibility_group` to every row in `basic-recommendation-catalog-500.csv` and carried it into the expanded `basic-recommendation-catalog-global.csv`.
- Added Product Catalog product-type rows with `compatibilityGroupId`.
- Added a Recommendation Library UI that loads all global CSV rows.
- Added per-row configuration simulation and all-template validation.
- Added a manual custom Signal Catalog metric path in the wizard so catalog metrics not present in the hard-coded picker no longer block template configuration.
