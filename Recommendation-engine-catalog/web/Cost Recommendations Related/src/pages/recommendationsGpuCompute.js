import { el, setPageTitle } from "../ui.js";
import { getRecoControlsForConnection, getSelectedAzureConnection } from "../store.js";
import { navigate } from "../router.js";

function hasSufficientHistory(conn) {
  return Boolean(conn?.runtime?.lastMetricsPullAt);
}

function coveragePct(conn) {
  const cov = conn?.runtime?.coverage;
  if (!cov || !cov.totalGpuResources) return 0;
  return cov.resourcesWithGpuMetrics / cov.totalGpuResources;
}

function getRecoUi(state) {
  return state?.ui?.recoGpuCompute || { evidenceId: null, evidenceTab: "summary", listQuery: "", statusFilter: "all" };
}

function setRecoUi(state, patch) {
  if (!state.ui) state.ui = {};
  state.ui.recoGpuCompute = { ...getRecoUi(state), ...(patch || {}) };
}

function money(n, currency = "USD") {
  const v = Number(n) || 0;
  try {
    return new Intl.NumberFormat(undefined, { style: "currency", currency }).format(v);
  } catch {
    return `${v.toFixed(2)} ${currency}`.trim();
  }
}

function computeRecommendationCatalog() {
  // One example of each cost recommendation type discussed earlier.
  // Mock objects show: fields, parameters, metrics used, and rule evaluation.
  return [
    {
      recoKey: "rightsize_gpu_sku",
      id: "reco-rightsize-vm-1",
      type: "Rightsize GPU SKU",
      description:
        "Recommends a smaller (or better-fit) GPU VM size when sustained utilization is low, reducing hourly compute cost without impacting workloads that don’t need the larger SKU.",
      service: "vm",
      resourceName: "vm-gpu-lab-01",
      resourceId: "/subscriptions/2222/resourceGroups/rg-lab/providers/Microsoft.Compute/virtualMachines/vm-gpu-lab-01",
      region: "eastus",
      severity: "medium",
      estimatedSavingsMonthly: 1260,
      currency: "USD",
      confidence: "high",
      requires: { gpuMetrics: true, historyDays: 14, activitySignal: false },
      parameters: {
        currentSku: "Standard_NC24s_v3",
        recommendedSku: "Standard_NC12s_v3",
        resizeType: "downsize",
        rationale: "Low GPU utilization and low GPU memory pressure over the lookback window.",
      },
      evidence: {
        window: "Last 14 days",
        rule: "Recommend downsize if avg GPU util < 15% AND p95 GPU util < 40% AND p95 GPU memory < 50% over the last 14 days.",
        decision: "Triggered: avg=8%, p95=22%, mem_p95=41%.",
        metricsUsed: [
          {
            name: "gpu_utilization_pct",
            source: "Azure Monitor Metrics API (mock)",
            unit: "Percent",
            aggregation: "avg + p95",
            samples: [
              { ts: "2025-12-08", value: 7.1 },
              { ts: "2025-12-09", value: 10.2 },
              { ts: "2025-12-10", value: 6.4 },
              { ts: "2025-12-11", value: 8.9 },
              { ts: "2025-12-12", value: 7.6 },
            ],
            derived: { avg: 8.0, p95: 22.0 },
          },
          {
            name: "gpu_memory_utilization_pct",
            source: "Azure Monitor Metrics API (mock)",
            unit: "Percent",
            aggregation: "p95",
            samples: [
              { ts: "2025-12-08", value: 38.0 },
              { ts: "2025-12-09", value: 44.0 },
              { ts: "2025-12-10", value: 35.0 },
              { ts: "2025-12-11", value: 42.0 },
              { ts: "2025-12-12", value: 39.0 },
            ],
            derived: { p95: 41.0 },
          },
          {
            name: "cpu_utilization_pct",
            source: "Azure Monitor Metrics API (mock)",
            unit: "Percent",
            aggregation: "avg",
            samples: [
              { ts: "2025-12-08", value: 12.0 },
              { ts: "2025-12-09", value: 14.0 },
              { ts: "2025-12-10", value: 9.0 },
              { ts: "2025-12-11", value: 11.0 },
              { ts: "2025-12-12", value: 13.0 },
            ],
            derived: { avg: 11.8 },
          },
        ],
      },
    },
    {
      recoKey: "idle_shutdown",
      id: "reco-idle-shutdown-1",
      type: "Idle shutdown / deallocate",
      description:
        "Identifies GPUs that are running with no active workload and near-zero utilization, then recommends deallocate/schedule shutdown to eliminate idle-hour spend.",
      service: "vm",
      // Same VM as rightsizing/commitment candidates to demonstrate priority/suppression.
      resourceName: "vm-gpu-lab-01",
      resourceId: "/subscriptions/2222/resourceGroups/rg-lab/providers/Microsoft.Compute/virtualMachines/vm-gpu-lab-01",
      region: "westus2",
      severity: "high",
      estimatedSavingsMonthly: 910,
      currency: "USD",
      confidence: "high",
      requires: { gpuMetrics: true, historyDays: 0, activitySignal: true },
      parameters: { action: "deallocate", idleWindowMinutes: 120, scheduleSuggestion: "Mon–Fri 7pm–7am (local)" },
      evidence: {
        window: "Last 2 hours",
        rule: "Recommend deallocate if no active workload AND GPU util < 5% for ≥ 60–120 minutes.",
        decision: "Triggered: GPU util stayed < 1% for 120 minutes and workload signal indicates no active jobs.",
        metricsUsed: [
          {
            name: "gpu_utilization_pct",
            source: "Azure Monitor Metrics API (mock)",
            unit: "Percent",
            aggregation: "time-series",
            samples: [
              { ts: "10:00", value: 0.2 },
              { ts: "10:30", value: 0.4 },
              { ts: "11:00", value: 0.3 },
              { ts: "11:30", value: 0.2 },
              { ts: "12:00", value: 0.5 },
            ],
            derived: { max: 0.5 },
          },
          {
            name: "workload_active",
            source: "Job/pod signal (mock)",
            unit: "Count",
            aggregation: "current",
            samples: [
              { ts: "10:00", value: 0 },
              { ts: "10:30", value: 0 },
              { ts: "11:00", value: 0 },
              { ts: "11:30", value: 0 },
              { ts: "12:00", value: 0 },
            ],
            derived: { current: 0 },
          },
        ],
      },
    },
    {
      recoKey: "autoscale_scale_to_zero",
      id: "reco-autoscale-aml-1",
      type: "Enable autoscale / scale-to-zero",
      description:
        "Recommends enabling autoscaling (including scale-to-zero) so GPU nodes exist only when there’s queued work, cutting baseline idle capacity costs.",
      service: "aml",
      resourceName: "aml-cluster-train",
      resourceId: "/subscriptions/2222/resourceGroups/rg-ml/providers/Microsoft.MachineLearningServices/workspaces/ws1/computes/cluster-train",
      region: "eastus",
      severity: "high",
      estimatedSavingsMonthly: 1480,
      currency: "USD",
      confidence: "medium",
      requires: { gpuMetrics: false, historyDays: 7, activitySignal: true },
      parameters: {
        currentMinNodes: 2,
        recommendedMinNodes: 0,
        currentMaxNodes: 10,
        recommendedMaxNodes: 10,
        scaleRule: "queueDepth > 0 => scale out; queueDepth == 0 for 30m => scale to 0",
      },
      evidence: {
        window: "Last 14 days",
        rule: "Recommend autoscale/scale-to-zero if nodes remain provisioned with long idle gaps and queue depth is near zero for extended periods.",
        decision: "Triggered: cluster held 2 nodes while queueDepth was 0 for ~9 hours/day on average.",
        metricsUsed: [
          {
            name: "queue_depth",
            source: "AML runs queued (mock)",
            unit: "Count",
            aggregation: "time-series",
            samples: [
              { ts: "Day-1", value: 0 },
              { ts: "Day-2", value: 3 },
              { ts: "Day-3", value: 0 },
              { ts: "Day-4", value: 0 },
              { ts: "Day-5", value: 1 },
            ],
            derived: { pctZero: 0.68 },
          },
          {
            name: "node_count",
            source: "AML cluster size (mock)",
            unit: "Count",
            aggregation: "time-series",
            samples: [
              { ts: "Day-1", value: 2 },
              { ts: "Day-2", value: 4 },
              { ts: "Day-3", value: 2 },
              { ts: "Day-4", value: 2 },
              { ts: "Day-5", value: 2 },
            ],
            derived: { min: 2, max: 4 },
          },
        ],
      },
    },
    {
      recoKey: "spot",
      id: "reco-spot-batch-1",
      type: "Use Spot GPUs for interruptible workloads",
      description:
        "Recommends Spot/low-priority GPUs for retryable training/batch workloads to significantly reduce GPU rates while accepting interruptions.",
      service: "batch",
      resourceName: "batch-pool-train",
      resourceId: "/subscriptions/2222/resourceGroups/rg-batch/providers/Microsoft.Batch/batchAccounts/ba1/pools/pool1",
      region: "centralus",
      severity: "medium",
      estimatedSavingsMonthly: 2100,
      currency: "USD",
      confidence: "medium",
      requires: { gpuMetrics: false, historyDays: 7, activitySignal: true },
      parameters: { workloadType: "training", interruptible: true, checkpointing: true, suggestedSpotMaxPrice: "Pay-as-you-go cap (default)" },
      evidence: {
        window: "Last 30 days",
        rule: "Recommend Spot when workload is retryable/interruptible and consumes meaningful GPU-hours.",
        decision: "Triggered: retryable tasks + checkpointing enabled; avg GPU-hours/day ~ 35.",
        metricsUsed: [
          {
            name: "gpu_hours_per_day",
            source: "Batch tasks × runtime × GPU count (mock)",
            unit: "GPU-hours",
            aggregation: "avg",
            samples: [
              { ts: "2025-12-15", value: 34 },
              { ts: "2025-12-16", value: 38 },
              { ts: "2025-12-17", value: 29 },
              { ts: "2025-12-18", value: 41 },
              { ts: "2025-12-19", value: 33 },
            ],
            derived: { avg: 35.0 },
          },
          { name: "retryable", source: "User/workload metadata (mock)", unit: "Boolean", aggregation: "current", samples: [{ ts: "current", value: 1 }], derived: { value: true } },
        ],
      },
    },
    {
      recoKey: "commitment",
      id: "reco-commitment-vm-1",
      type: "Buy commitment (Savings Plan / RI)",
      description:
        "Detects steady baseline GPU usage and recommends commitments (Savings Plan/Reservations) to lower unit rates for the portion of usage that is predictably always on.",
      service: "vm",
      // Same VM as idle/rightsizing candidates to demonstrate that commitments are suppressed.
      resourceName: "vm-gpu-lab-01",
      resourceId: "/subscriptions/2222/resourceGroups/rg-lab/providers/Microsoft.Compute/virtualMachines/vm-gpu-lab-01",
      region: "eastus",
      severity: "medium",
      estimatedSavingsMonthly: 1750,
      currency: "USD",
      confidence: "high",
      requires: { gpuMetrics: false, historyDays: 30, activitySignal: false },
      parameters: { skuFamily: "NCasT4_v3", baselineGpuCount: 2, commitmentTerm: "1 year", commitmentType: "Savings Plan (compute)" },
      evidence: {
        window: "Last 30 days",
        rule: "Recommend commitment if sustained baseline usage ≥ 60–70% of hours with low variance.",
        decision: "Triggered: baseline of 2 GPUs running ~92% of hours with low variance.",
        metricsUsed: [
          {
            name: "running_hours",
            source: "Compute running state (mock)",
            unit: "Hours",
            aggregation: "sum",
            samples: [
              { ts: "Week-1", value: 310 },
              { ts: "Week-2", value: 322 },
              { ts: "Week-3", value: 315 },
              { ts: "Week-4", value: 318 },
            ],
            derived: { monthHours: 1265, pctOfMonth: 0.92 },
          },
        ],
      },
    },
    {
      recoKey: "aks_binpack",
      id: "reco-aks-binpack-1",
      type: "AKS GPU bin-packing / scheduling fixes",
      description:
        "Recommends changes that reduce GPU node fragmentation (requests/limits, autoscaler, scheduling) so workloads pack onto fewer GPU nodes, lowering node count and cost.",
      service: "aks",
      resourceName: "aks-gpu-pool",
      resourceId: "/subscriptions/2222/resourceGroups/rg-aks/providers/Microsoft.ContainerService/managedClusters/aks1/agentPools/gpu",
      region: "eastus",
      severity: "medium",
      estimatedSavingsMonthly: 980,
      currency: "USD",
      confidence: "medium",
      requires: { gpuMetrics: true, historyDays: 7, activitySignal: true },
      parameters: {
        currentNodeCount: 6,
        targetNodeCount: 4,
        issue: "fragmentation",
        suggestedActions: ["set accurate GPU requests/limits", "enable cluster autoscaler", "reduce anti-affinity where safe"],
      },
      evidence: {
        window: "Last 7 days",
        rule: "Recommend consolidation if multiple GPU nodes stay up due to fragmentation while utilization remains low.",
        decision: "Triggered: avg GPU used per node < 35% but requests cause 6 nodes to remain allocated.",
        metricsUsed: [
          { name: "gpu_allocatable", source: "Kubernetes node capacity (mock)", unit: "GPUs", aggregation: "current", samples: [{ ts: "current", value: 6 }], derived: { value: 6 } },
          { name: "gpu_requested", source: "Kubernetes pod requests (mock)", unit: "GPUs", aggregation: "current", samples: [{ ts: "current", value: 5 }], derived: { value: 5 } },
          {
            name: "gpu_utilization_pct",
            source: "DCGM/Monitor (mock)",
            unit: "Percent",
            aggregation: "avg",
            samples: [
              { ts: "Day-1", value: 28 },
              { ts: "Day-2", value: 31 },
              { ts: "Day-3", value: 22 },
              { ts: "Day-4", value: 33 },
              { ts: "Day-5", value: 26 },
            ],
            derived: { avg: 28.0 },
          },
        ],
      },
    },
    {
      recoKey: "pattern_change",
      id: "reco-pattern-change-1",
      type: "Move always-on VM to job-native pattern (AML/Batch)",
      description:
        "Recommends shifting from always-on GPU VMs to job-native, ephemeral compute (AML clusters / Batch pools) so capacity scales down when no jobs run, reducing idle waste.",
      service: "vm",
      resourceName: "vm-ds-notebook",
      resourceId: "/subscriptions/2222/resourceGroups/rg-ds/providers/Microsoft.Compute/virtualMachines/vm-ds-notebook",
      region: "eastus",
      severity: "medium",
      estimatedSavingsMonthly: 640,
      currency: "USD",
      confidence: "medium",
      requires: { gpuMetrics: true, historyDays: 14, activitySignal: true },
      parameters: { from: "Always-on VM", to: "AML compute cluster (scale-to-zero) or Batch pool", reason: "High idle time with job-based usage pattern" },
      evidence: {
        window: "Last 30 days",
        rule: "Recommend pattern change if VM idle > 40–50% and work is job-based with bursts.",
        decision: "Triggered: idle ~55% and work occurs in short bursts; scale-to-zero would capture idle savings.",
        metricsUsed: [
          { name: "idle_pct", source: "Derived from GPU util + workload signal (mock)", unit: "Percent", aggregation: "avg", samples: [{ ts: "Week-1", value: 52 }, { ts: "Week-2", value: 58 }, { ts: "Week-3", value: 54 }, { ts: "Week-4", value: 56 }], derived: { avg: 55.0 } },
        ],
      },
    },
    {
      recoKey: "cleanup_orphans",
      id: "reco-cleanup-1",
      type: "Cleanup orphan artifacts (disks/snapshots)",
      description:
        "Finds unattached disks/snapshots left behind by GPU projects and recommends deleting or tiering them to stop paying for unused storage.",
      service: "vm",
      resourceName: "rg-ml (unattached storage)",
      resourceId: "/subscriptions/2222/resourceGroups/rg-ml",
      region: "eastus",
      severity: "low",
      estimatedSavingsMonthly: 120,
      currency: "USD",
      confidence: "high",
      requires: { gpuMetrics: false, historyDays: 0, activitySignal: false },
      parameters: { unattachedDisks: 3, oldSnapshots: 7, ruleAgeDays: 30 },
      evidence: {
        window: "Inventory snapshot (current)",
        rule: "Recommend cleanup if disks/snapshots are unattached and older than 30–90 days (and not tagged retain).",
        decision: "Triggered: 3 unattached disks and 7 snapshots older than 30 days without retain tag.",
        metricsUsed: [
          { name: "unattached_disks_count", source: "Inventory/ARM (mock)", unit: "Count", aggregation: "current", samples: [{ ts: "current", value: 3 }], derived: { value: 3 } },
          { name: "old_snapshots_count", source: "Inventory/ARM (mock)", unit: "Count", aggregation: "current", samples: [{ ts: "current", value: 7 }], derived: { value: 7 } },
        ],
      },
    },
  ];
}

function statusForReco(conn, reco, controls) {
  if (!conn) return { status: "blocked", reason: "No Azure metrics connection selected" };
  const enabled = Boolean(controls?.[reco.recoKey] ?? true);
  if (!enabled) return { status: "paused", reason: "Paused by user (see Metrics Readiness → Processing controls)" };
  const cov = coveragePct(conn);
  const historyOk = hasSufficientHistory(conn);

  if (reco.requires?.gpuMetrics && cov < 0.8) return { status: "blocked", reason: "GPU metrics coverage < 80%" };
  if (reco.requires?.historyDays && reco.requires.historyDays >= 7 && !historyOk) return { status: "blocked", reason: "Insufficient metrics history (collecting)" };
  return { status: "available", reason: "Ready" };
}

function applyPriorityAndSuppression(candidates, baseStatusById) {
  // Returns a map: recoId -> {status, reason} where status may become "suppressed".
  const out = {};

  // Helper: mark suppressed by winner.
  function suppress(recoId, winner) {
    out[recoId] = { status: "suppressed", reason: `Suppressed by higher priority: ${winner.type}` };
  }

  // Start with base statuses.
  for (const c of candidates) out[c.id] = { ...baseStatusById[c.id] };

  // Group by resourceId for resource-scoped recommendations.
  const byResource = new Map();
  for (const c of candidates) {
    const k = c.resourceId || "__none__";
    if (!byResource.has(k)) byResource.set(k, []);
    byResource.get(k).push(c);
  }

  // Priority policy for VMs: idle > pattern_change > rightsize > commitment.
  const vmPriority = ["idle_shutdown", "pattern_change", "rightsize_gpu_sku", "commitment"];

  for (const [resourceId, list] of byResource.entries()) {
    const service = list[0]?.service;

    // Only apply mutual exclusivity within the same resource/service for VM.
    if (service === "vm") {
      // Filter to only candidates that are runnable (base status available).
      const runnable = list.filter((c) => baseStatusById[c.id]?.status === "available");
      if (!runnable.length) continue;

      // Pick first by priority list.
      const winner =
        vmPriority.map((k) => runnable.find((c) => c.recoKey === k)).find(Boolean) || runnable[0];

      // Suppress other VM candidates that are also runnable.
      for (const c of runnable) {
        if (c.id === winner.id) continue;
        suppress(c.id, winner);
      }

      // Also suppress commitments even if they would otherwise be available when a higher-priority VM reco is chosen.
      // (Already covered above for runnable set; we keep this explicit for clarity.)
      continue;
    }

    // For AKS pools, allow binpack + autoscale to coexist, but prioritize binpack as primary.
    if (service === "aks") {
      const runnable = list.filter((c) => baseStatusById[c.id]?.status === "available");
      if (!runnable.length) continue;
      const binpack = runnable.find((c) => c.recoKey === "aks_binpack");
      if (binpack) {
        for (const c of runnable) {
          if (c.id === binpack.id) continue;
          // only suppress lower value/overlapping types if we add them later; keep both for now.
        }
      }
    }
  }

  return out;
}

function renderEvidencePanel(ctx, reco) {
  const { state, setState } = ctx;
  const ui = getRecoUi(state);

  let tab = ui?.evidenceTab || "summary";
  const setTab = (t) => {
    setRecoUi(state, { evidenceTab: t });
    setState({ ...state });
  };

  const tabRow = el("div", { class: "tabs" }, [
    el("button", { class: `tab ${tab === "summary" ? "isActive" : ""}`, type: "button", text: "Summary", onclick: () => setTab("summary") }),
    el("button", { class: `tab ${tab === "metrics" ? "isActive" : ""}`, type: "button", text: "Metrics used", onclick: () => setTab("metrics") }),
    el("button", { class: `tab ${tab === "rule" ? "isActive" : ""}`, type: "button", text: "Rule evaluation", onclick: () => setTab("rule") }),
  ]);

  const header = el("div", { class: "wizardHeader" }, [
    el("div", {}, [
      el("h3", { class: "card__title", text: `Evidence: ${reco.type}` }),
      el("p", { class: "card__subtitle", text: `${reco.resourceName} · ${reco.service.toUpperCase()} · ${reco.region}` }),
    ]),
    el("div", { class: "btnRow" }, [
      el("button", {
        class: "btn btn--sm",
        type: "button",
        text: "Close",
        onclick: () => {
          setRecoUi(state, { evidenceId: null });
          setState({ ...state });
        },
      }),
    ]),
  ]);

  const kv = el("table", { class: "kvTable" }, [
    el("tbody", {}, [
      el("tr", {}, [el("td", { class: "kvKey", text: "Cost recommendation ID" }), el("td", { class: "mono", text: reco.id })]),
      el("tr", {}, [el("td", { class: "kvKey", text: "Resource ID" }), el("td", { class: "mono", text: reco.resourceId })]),
      el("tr", {}, [el("td", { class: "kvKey", text: "Description" }), el("td", { text: reco.description || "—" })]),
      el("tr", {}, [el("td", { class: "kvKey", text: "Estimated savings / month" }), el("td", { class: "mono", text: money(reco.estimatedSavingsMonthly, reco.currency) })]),
      el("tr", {}, [el("td", { class: "kvKey", text: "Confidence" }), el("td", { class: "mono", text: reco.confidence })]),
      el("tr", {}, [
        el("td", { class: "kvKey", text: "Requirements" }),
        el("td", { class: "mono", text: `gpuMetrics=${reco.requires.gpuMetrics}, historyDays=${reco.requires.historyDays}, activitySignal=${reco.requires.activitySignal}` }),
      ]),
    ]),
  ]);

  const params = el("table", { class: "kvTable", style: "margin-top:12px" }, [
    el("tbody", {}, Object.entries(reco.parameters || {}).map(([k, v]) => el("tr", {}, [el("td", { class: "kvKey", text: k }), el("td", { class: "mono", text: Array.isArray(v) ? v.join(", ") : String(v) })]))),
  ]);

  const renderMetrics = () => {
    const rows = [];
    for (const m of reco.evidence.metricsUsed || []) {
      rows.push(
        el("div", { class: "card", style: "box-shadow:none" }, [
          el("h4", { class: "card__title", text: m.name }),
          el("p", { class: "card__subtitle", text: `${m.source} · unit=${m.unit} · aggregation=${m.aggregation}` }),
          el("table", { class: "table" }, [
            el("thead", {}, [el("tr", {}, [el("th", { text: "Timestamp" }), el("th", { text: "Value" })])]),
            el("tbody", {}, (m.samples || []).map((s) => el("tr", {}, [el("td", { class: "mono", text: s.ts }), el("td", { class: "mono", text: String(s.value) })]))),
          ]),
          el("div", { class: "callout", style: "margin-top:10px" }, [
            el("div", { class: "callout__title", text: "Derived stats (used by rule)" }),
            el("p", { class: "callout__body mono", text: JSON.stringify(m.derived || {}, null, 0) }),
          ]),
        ])
      );
    }
    return el("div", { class: "evidenceGrid" }, rows);
  };

  const renderRule = () =>
    el("div", { class: "grid" }, [
      el("div", { class: "callout" }, [el("div", { class: "callout__title", text: "Rule" }), el("p", { class: "callout__body", text: reco.evidence.rule })]),
      el("div", { class: "callout", style: "border-color:rgba(122,167,255,0.35);background:rgba(122,167,255,0.10)" }, [
        el("div", { class: "callout__title", text: "Decision" }),
        el("p", { class: "callout__body", text: reco.evidence.decision }),
      ]),
      el("div", { class: "callout" }, [el("div", { class: "callout__title", text: "Evaluation window" }), el("p", { class: "callout__body", text: reco.evidence.window })]),
    ]);

  const body =
    tab === "summary"
      ? el("div", { class: "grid" }, [
          el("div", {}, [kv]),
          el("div", {}, [
            el("h4", { class: "card__title", text: "Parameters (available fields)" }),
            el("p", { class: "card__subtitle", text: "Per cost recommendation parameter payload developers can expect." }),
            params,
          ]),
        ])
      : tab === "metrics"
      ? renderMetrics()
      : renderRule();

  return el("div", { class: "card" }, [header, tabRow, el("div", { style: "height:12px" }), body]);
}

export function renderRecommendationsGpuComputePage(ctx) {
  const { state, setState } = ctx;
  setPageTitle("Cost recommendations · GPU compute", "Cost recommendations are shown only when required metrics are available.");

  const conn = getSelectedAzureConnection(state);
  const controls = conn ? getRecoControlsForConnection(state, conn.id) : null;
  const catalog = computeRecommendationCatalog();
  const ui = getRecoUi(state);
  const selectedReco = catalog.find((r) => r.id === ui.evidenceId) || null;

  // Compute statuses, then apply priority/suppression so the “best outcome” is shown per resource.
  const baseStatusById = Object.fromEntries(catalog.map((r) => [r.id, statusForReco(conn, r, controls)]));
  const finalStatusById = applyPriorityAndSuppression(catalog, baseStatusById);
  const query = String(ui.listQuery || "").trim().toLowerCase();
  const statusFilter = ui.statusFilter || "all";

  const filtered = catalog.filter((r) => {
    const st = finalStatusById[r.id]?.status || "unknown";
    if (statusFilter !== "all" && st !== statusFilter) return false;
    if (!query) return true;
    const hay = `${r.type} ${r.service} ${r.resourceName} ${r.region} ${r.id}`.toLowerCase();
    return hay.includes(query);
  });
  const filteredSorted = [...filtered].sort((a, b) => {
    const av = Number(a?.estimatedSavingsMonthly) || 0;
    const bv = Number(b?.estimatedSavingsMonthly) || 0;
    if (bv !== av) return bv - av;
    return String(a?.type || "").localeCompare(String(b?.type || ""));
  });

  const banner = !conn
    ? el("div", { class: "card" }, [
        el("h2", { class: "card__title", text: "Developer reference: sample GPU compute cost recommendations" }),
        el("p", { class: "card__subtitle", text: "No Azure connection is selected. The table below still shows a full sample set for developer clarity." }),
        el("div", { class: "card__footer" }, [
          el("button", { class: "btn btn--primary", type: "button", text: "Connect Azure", onclick: () => navigate("/integrations/azure/connections/new") }),
          el("button", { class: "btn", type: "button", text: "Read gating rules", onclick: () => window.open("docs/recommendation-readiness-rules.md", "_blank") }),
        ]),
      ])
    : el("div", { class: "card" }, [
        el("h2", { class: "card__title", text: "GPU compute cost recommendations (sample + gating demo)" }),
        el("p", { class: "card__subtitle", text: "One example of each cost recommendation type and how availability is gated by coverage/history." }),
        el("div", { class: "card__footer" }, [
          el("button", { class: "btn", type: "button", text: "View readiness", onclick: () => navigate("/integrations/azure/gpu-metrics") }),
          el("button", { class: "btn", type: "button", text: "Read gating rules", onclick: () => window.open("docs/recommendation-readiness-rules.md", "_blank") }),
        ]),
      ]);

  const table = el("table", { class: "table table--brand" }, [
    el("thead", {}, [
      el("tr", {}, [
        el("th", { text: "Type" }),
        el("th", { text: "Description" }),
        el("th", { text: "Service" }),
        el("th", { text: "Resource" }),
        el("th", { text: "Savings/mo" }),
        el("th", { text: "Confidence" }),
        el("th", { text: "Status" }),
        el("th", { text: "Evidence" }),
      ]),
    ]),
    el(
      "tbody",
      {},
      filteredSorted.map((r) => {
        const st = finalStatusById[r.id] || { status: "unknown", reason: "—" };
        const isSelected = ui.evidenceId === r.id;
        const isMuted = st.status === "suppressed";
        return el("tr", {
          class: `${isSelected ? "isSelected" : ""} ${isMuted ? "isMuted" : ""}`.trim(),
          onclick: () => {
            setRecoUi(state, { evidenceId: r.id, evidenceTab: "summary" });
            setState({ ...state });
          },
        }, [
          el("td", {}, [
            el("div", { style: "display:flex;flex-direction:column;gap:2px" }, [
              el("div", { text: r.type }),
              el("div", { class: "mono muted", text: `id=${r.id}` }),
            ]),
          ]),
          el("td", {}, [
            el("div", { style: "display:flex;flex-direction:column;gap:2px" }, [
              el("div", { text: r.description || "—" }),
              el("div", { class: "mono muted", text: `severity=${r.severity}` }),
            ]),
          ]),
          el("td", { class: "mono", text: r.service.toUpperCase() }),
          el("td", {}, [
            el("div", { style: "display:flex;flex-direction:column;gap:2px" }, [
              el("div", { text: r.resourceName }),
              el("div", { class: "mono muted", text: r.region }),
            ]),
          ]),
          el("td", { class: "mono", text: money(r.estimatedSavingsMonthly, r.currency) }),
          el("td", { class: "mono", text: r.confidence }),
          el("td", {}, [
            el("div", { style: "display:flex;flex-direction:column;gap:2px" }, [
              el("div", { class: "mono", text: st.status }),
              el("div", { class: "muted", text: st.reason }),
            ]),
          ]),
          el("td", {}, [
            el("button", {
              class: "linkBtn",
              type: "button",
              text: "View metrics used",
              onclick: (e) => {
                e.stopPropagation();
                setRecoUi(state, { evidenceId: r.id, evidenceTab: "metrics" });
                setState({ ...state });
              },
            }),
          ]),
        ]);
      })
    ),
  ]);

  const devNotes = el("div", { class: "card" }, [
    el("h3", { class: "card__title", text: "Developer notes" }),
    el("p", {
      class: "card__subtitle",
      text: "Each cost recommendation includes identifiers, savings/confidence, parameters, evidence, and a priority/suppression policy so users see the best outcome per resource.",
    }),
    el("div", { class: "btnRow" }, [
      el("button", { class: "btn btn--sm", type: "button", text: "Data contract", onclick: () => window.open("docs/data-contract.md", "_blank") }),
      el("button", { class: "btn btn--sm", type: "button", text: "Permissions matrix", onclick: () => window.open("docs/credentials-permissions-matrix.md", "_blank") }),
    ]),
  ]);

  const listCard = el("div", { class: "card" }, [
    el("div", { class: "wizardHeader" }, [
      el("div", {}, [
        el("h3", { class: "card__title", text: "GPU compute cost recommendations" }),
        el("p", { class: "card__subtitle", text: "Search, filter, select a row to view details. Matches the master-detail pattern used in Cost Management UIs." }),
      ]),
      el("div", { class: "btnRow" }, [
        el("button", { class: "btn btn--sm", type: "button", text: "User guide", onclick: () => window.open("docs/gpu-compute-recommendations-user-guide.md", "_blank") }),
      ]),
    ]),
    el("div", { class: "toolbar" }, [
      el("div", { class: "toolbar__left" }, [
        el("input", {
          class: "inputSm",
          placeholder: "Search by resource, type, region, id…",
          value: ui.listQuery || "",
          oninput: (e) => {
            setRecoUi(state, { listQuery: e.target.value });
            setState({ ...state });
          },
        }),
        el(
          "select",
          {
            class: "selectSm",
            value: ui.statusFilter || "all",
            onchange: (e) => {
              setRecoUi(state, { statusFilter: e.target.value });
              setState({ ...state });
            },
          },
          [
            el("option", { value: "all", text: "All statuses" }),
            el("option", { value: "available", text: "Available" }),
            el("option", { value: "blocked", text: "Blocked" }),
            el("option", { value: "paused", text: "Paused" }),
            el("option", { value: "suppressed", text: "Suppressed" }),
          ]
        ),
      ]),
    el("div", { class: "toolbar__right mono muted", text: `${filteredSorted.length}/${catalog.length} shown` }),
    ]),
    table,
  ]);

  const detailsCard = selectedReco
    ? renderEvidencePanel(ctx, selectedReco)
    : el("div", { class: "card" }, [
        el("h3", { class: "card__title", text: "Recommendation details" }),
        el("p", { class: "card__subtitle", text: "Select a row from the list to view evidence (summary, metrics used, rule evaluation)." }),
        devNotes,
      ]);

  return el("div", { class: "grid" }, [
    banner,
    el("div", { class: "grid grid--2" }, [listCard, detailsCard]),
  ]);
}


