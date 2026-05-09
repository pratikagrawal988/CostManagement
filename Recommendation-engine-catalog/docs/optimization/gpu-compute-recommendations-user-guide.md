# Azure GPU compute recommendations: user guide (types, metrics, thresholds)

This guide explains **how each GPU compute recommendation type works**, **which metrics are used**, and the **default thresholds** (rules) that trigger a recommendation. These rules are intended as **general defaults** and are **backend-configured by FinOps/FinOps policy** (not customer self-serve UI settings in this prototype).

## General gating (applies to all types)

- **Data sufficiency**
  - Rightsizing / commitment recommendations: require **≥ 7–14 days** of history (recommended: 30 days lookback).
  - Near-real-time idle detection: can use **60–120 minutes**.
- **Confidence**
  - Use **avg** + **p95** (or p90) across the evaluation window.
- **Savings threshold**
  - Only surface if estimated savings ≥ configured **$/month** or ≥ **% of spend**.
- **Exclusions**
  - Exclude resources tagged `doNotOptimize=true` (or other protected scopes).

## Priority and compatibility (what can be generated together)

FinOps FinOps aims to show the **best possible outcome** per resource. Some cost recommendation types are **mutually exclusive** because one action makes the other irrelevant or unsafe.

### VM priority (GPU VMs)
Default priority order (highest → lowest):
1. **Idle shutdown / deallocate**
2. **Move always-on VM to job-native pattern**
3. **Rightsize GPU SKU**
4. **Buy commitments (Savings Plan / RI)**

### Mutual exclusion rules (VM)
- If a VM is **idle**, FinOps will generate **Idle shutdown** and **suppress**:
  - Rightsizing
  - Commitments
  - Pattern change (optional depending on org preference; default: idle wins)
- If a VM is **recommended to move to job-native pattern**, FinOps will **suppress**:
  - Rightsizing
  - Commitments
- If a VM is **recommended to rightsize**, FinOps will **suppress**:
  - Commitments

### When multiple recommendations are valid
Multiple cost recommendations can be valid when they target **different layers** or **different scopes**, for example:
- **Cleanup orphan artifacts** can coexist with any compute recommendation (it targets storage artifacts).
- For **AKS GPU pools**, it can be valid to show both:
  - **Bin-packing/scheduling fixes** (reduce fragmentation) and
  - **Autoscale/scale-to-zero** (reduce idle baseline)

FinOps should clearly label any suppressed recommendations as **suppressed by higher priority** so users understand why they are not being generated/shown.

## 1) Rightsize / change GPU SKU (VM / node / pool)

### What it does (cost impact)
Recommends a **smaller** or **better-fit GPU SKU** when sustained GPU usage is low or mismatched, reducing hourly compute cost while meeting performance needs.

### Metrics used
- **GPU utilization %** (avg, p95)
- **GPU memory utilization %** (p95)
- Optional: **CPU utilization %** (avg) to spot CPU-bound workloads

### Default thresholds / rules
- Recommend **downsize** when (over **14–30 days**):
  - **avg GPU util < 15%** AND **p95 GPU util < 40%**, AND
  - **p95 GPU memory util < 50%**
- Recommend **change family** when:
  - GPU util low but **GPU memory p95 high** → prefer more VRAM-per-GPU options (if available)
  - GPU util high but **GPU memory p95 low** → prefer more compute-per-GPU options (if available)

## 2) Idle shutdown / deallocate (VM / compute instance / pool)

### What it does (cost impact)
Identifies GPUs that are **running while unused** and recommends **deallocate** or a **shutdown schedule**, eliminating idle-hour spend.

### Metrics used
- **GPU utilization %** (near-real-time)
- Optional: **GPU memory utilization %**
- **Workload activity signal** (jobs running / pods running / tasks running)

### Default thresholds / rules
- Recommend **deallocate / stop** if:
  - **workload_active == 0** AND
  - **GPU util < 5%** continuously for **≥ 60–120 minutes**
- Recommend **schedule-based** shutdown if:
  - repeating idle windows exist (example: **≥ 30%** of weekly hours are idle)

## 3) Enable autoscale / scale-to-zero (AKS/AML/Batch)

### What it does (cost impact)
Recommends enabling autoscaling so GPU nodes exist **only when demand exists**, reducing baseline capacity costs.

### Metrics used
- **Queue depth / pending work** (queued runs, queued tasks, pending pods)
- **Node count** (time series)
- Optional: **GPU utilization %** for validation

### Default thresholds / rules
- Recommend autoscale if:
  - node count is flat while queue depth fluctuates, OR
  - nodes remain provisioned with idle windows ≥ **10–20%** of time
- Recommend **min nodes = 0** if:
  - long idle gaps exist (example: **≥ 4 hours/day** idle) and warm-up time is acceptable

## 4) Use Spot GPUs (interruptible workloads)

### What it does (cost impact)
Recommends running eligible workloads on **Spot** capacity to reduce unit rate, trading off reliability/interruptions.

### Metrics / inputs used
- **Workload interruptibility** (user/workload metadata)
- **Retry/checkpoint support** (metadata)
- **GPU-hours/day** (derived from runtime × GPU count)

### Default thresholds / rules
- Recommend Spot when:
  - workload is flagged **interruptible/retryable**, AND
  - there is meaningful usage (example: **> 2–4 GPU-hours/day**), AND
  - the platform can detect/assume checkpointing or retries are configured

## 5) Commitments (Savings Plan / Reserved Instances)

### What it does (cost impact)
Recommends commitments for the **steady baseline** of GPU usage to reduce unit price for that predictable portion.

### Metrics used
- **Running hours** per SKU family/region (or normalized GPU-hours)
- **Baseline stability** (variance of baseline)

### Default thresholds / rules
- Recommend commitment if, over **30 days**:
  - baseline usage is ≥ **60–70%** of hours, AND
  - baseline is stable (low variance day-to-day)

## 6) AKS GPU bin-packing / scheduling fixes

### What it does (cost impact)
Reduces GPU node count by improving **packing efficiency** (less fragmentation) so pods fit on fewer nodes.

### Metrics used
- **GPU requested vs allocatable** (current)
- **GPU utilization %** (avg per node)
- **Pending GPU pods** (count)

### Default thresholds / rules
- Recommend consolidation when:
  - multiple GPU nodes are running, AND
  - average utilization per node is low (example: **avg < 35%**) but requests force extra nodes
- Recommend request/limit tuning when:
  - requested GPU consistently >> actual used GPU (requires per-node/per-pod GPU usage telemetry)

## 7) Move always-on VM to job-native pattern (Batch/AML cluster)

### What it does (cost impact)
Recommends shifting from always-on GPU VMs to **ephemeral job clusters** that scale down when idle.

### Metrics used
- **Idle %** (derived from GPU utilization + workload activity)
- **Job submission pattern** (bursty vs steady)

### Default thresholds / rules
- Recommend pattern change if:
  - idle time is **> 40–50%** and usage is job-based (bursty)

## 8) Cleanup orphan artifacts (disks/snapshots/unattached)

### What it does (cost impact)
Finds unused artifacts left behind by GPU projects and recommends deletion or tiering to stop paying for unused storage.

### Metrics / inputs used
- Inventory: attachment status (unattached), age, tags (retain)

### Default thresholds / rules
- Recommend cleanup if:
  - resource is unattached and older than **30–90 days** and not tagged retain


