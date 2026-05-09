import { el, setPageTitle } from "../ui.js";
import { getRecoControlsForConnection, getSelectedGcpConnection } from "../store.js";
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
  return state?.ui?.recoGpuComputeGcp || { evidenceId: null, evidenceTab: "summary", listQuery: "", statusFilter: "all" };
}

function setRecoUi(state, patch) {
  if (!state.ui) state.ui = {};
  state.ui.recoGpuComputeGcp = { ...getRecoUi(state), ...(patch || {}) };
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
  // Same recommendation set, GCP-flavored resources and evidence sources.
  return [
    {
      recoKey: "rightsize_gpu_sku",
      id: "gcp-reco-rightsize-1",
      type: "Rightsize GPU machine type",
      description: "Recommends a smaller/better-fit GCE machine type (or GPU config) when sustained utilization is low to reduce hourly compute cost.",
      service: "gce",
      resourceName: "gce-gpu-lab-01",
      resourceId: "projects/gcp-prod-ml/zones/us-central1-a/instances/gce-gpu-lab-01",
      region: "us-central1",
      severity: "medium",
      estimatedSavingsMonthly: 980,
      currency: "USD",
      confidence: "high",
      requires: { gpuMetrics: true, historyDays: 14, activitySignal: false },
      parameters: { currentType: "a2-highgpu-2g", recommendedType: "a2-highgpu-1g", resizeType: "downsize" },
      evidence: {
        window: "Last 14 days",
        rule: "Recommend downsize if avg GPU util < 15% AND p95 GPU util < 40% AND p95 GPU memory < 50% over the last 14 days.",
        decision: "Triggered: avg=9%, p95=24%, mem_p95=39%.",
        metricsUsed: [
          { name: "gpu_utilization_pct", source: "Cloud Monitoring (mock)", unit: "Percent", aggregation: "avg + p95", samples: [{ ts: "2025-12-08", value: 8.1 }], derived: { avg: 9.0, p95: 24.0 } },
          { name: "gpu_memory_utilization_pct", source: "Cloud Monitoring (mock)", unit: "Percent", aggregation: "p95", samples: [{ ts: "2025-12-08", value: 36.0 }], derived: { p95: 39.0 } },
          { name: "cpu_utilization_pct", source: "Cloud Monitoring (mock)", unit: "Percent", aggregation: "avg", samples: [{ ts: "2025-12-08", value: 18.0 }], derived: { avg: 16.4 } },
        ],
      },
    },
    {
      recoKey: "idle_shutdown",
      id: "gcp-reco-idle-1",
      type: "Idle shutdown / stop instance",
      description: "Identifies GPU VMs running with no active workload and near-zero utilization and recommends stopping them to eliminate idle-hour spend.",
      service: "gce",
      resourceName: "gce-gpu-lab-01",
      resourceId: "projects/gcp-prod-ml/zones/us-central1-a/instances/gce-gpu-lab-01",
      region: "us-central1",
      severity: "high",
      estimatedSavingsMonthly: 720,
      currency: "USD",
      confidence: "high",
      requires: { gpuMetrics: true, historyDays: 0, activitySignal: true },
      parameters: { action: "stop", idleWindowMinutes: 120 },
      evidence: {
        window: "Last 2 hours",
        rule: "Recommend stop if no active workload AND GPU util < 5% for ≥ 60–120 minutes.",
        decision: "Triggered: GPU util stayed < 1% for 120 minutes and workload signal indicates no active jobs.",
        metricsUsed: [
          { name: "gpu_utilization_pct", source: "Cloud Monitoring (mock)", unit: "Percent", aggregation: "time-series", samples: [{ ts: "11:00", value: 0.4 }], derived: { max: 0.6 } },
          { name: "workload_active", source: "Job/pod signal (mock)", unit: "Count", aggregation: "current", samples: [{ ts: "current", value: 0 }], derived: { current: 0 } },
        ],
      },
    },
    {
      recoKey: "commitment",
      id: "gcp-reco-cud-1",
      type: "Buy commitments (CUDs)",
      description: "Detects steady baseline GPU usage and recommends GCP commitments (CUDs) to lower unit rates for the predictable always-on portion.",
      service: "gce",
      resourceName: "gce-gpu-lab-01",
      resourceId: "projects/gcp-prod-ml/zones/us-central1-a/instances/gce-gpu-lab-01",
      region: "us-central1",
      severity: "medium",
      estimatedSavingsMonthly: 1400,
      currency: "USD",
      confidence: "high",
      requires: { gpuMetrics: false, historyDays: 30, activitySignal: false },
      parameters: { commitmentTerm: "1 year", commitmentType: "CUD", baselineGpuCount: 1 },
      evidence: {
        window: "Last 30 days",
        rule: "Recommend commitment if sustained baseline usage ≥ 60–70% of hours with low variance.",
        decision: "Triggered: baseline running ~90% of hours.",
        metricsUsed: [{ name: "running_hours", source: "Instance running state (mock)", unit: "Hours", aggregation: "sum", samples: [{ ts: "Week-1", value: 300 }], derived: { pctOfMonth: 0.9 } }],
      },
    },
    {
      recoKey: "cleanup_orphans",
      id: "gcp-reco-cleanup-1",
      type: "Cleanup orphan artifacts",
      description: "Finds unused disks/snapshots left behind by GPU projects and recommends deleting/tiering them to stop paying for unused storage.",
      service: "gce",
      resourceName: "project gcp-prod-ml (unattached storage)",
      resourceId: "projects/gcp-prod-ml",
      region: "us-central1",
      severity: "low",
      estimatedSavingsMonthly: 80,
      currency: "USD",
      confidence: "high",
      requires: { gpuMetrics: false, historyDays: 0, activitySignal: false },
      parameters: { unattachedDisks: 2, oldSnapshots: 4, ruleAgeDays: 30 },
      evidence: {
        window: "Inventory snapshot (current)",
        rule: "Recommend cleanup if disks/snapshots are unattached and older than 30–90 days (and not tagged retain).",
        decision: "Triggered: 2 unattached disks and 4 snapshots older than 30 days without retain label.",
        metricsUsed: [{ name: "unattached_disks_count", source: "Inventory (mock)", unit: "Count", aggregation: "current", samples: [{ ts: "current", value: 2 }], derived: { value: 2 } }],
      },
    },
  ];
}

function statusForReco(conn, reco, controls) {
  if (!conn) return { status: "blocked", reason: "No Google Cloud metrics connection selected" };
  const enabled = Boolean(controls?.[reco.recoKey] ?? true);
  if (!enabled) return { status: "paused", reason: "Paused by user (see Metrics Readiness → Processing controls)" };
  const cov = coveragePct(conn);
  const historyOk = hasSufficientHistory(conn);
  if (reco.requires?.gpuMetrics && cov < 0.8) return { status: "blocked", reason: "GPU metrics coverage < 80%" };
  if (reco.requires?.historyDays && reco.requires.historyDays >= 7 && !historyOk) return { status: "blocked", reason: "Insufficient metrics history (collecting)" };
  return { status: "available", reason: "Ready" };
}

function applyPriorityAndSuppression(candidates, baseStatusById) {
  const out = {};
  for (const c of candidates) out[c.id] = { ...baseStatusById[c.id] };
  const byResource = new Map();
  for (const c of candidates) {
    const k = c.resourceId || "__none__";
    if (!byResource.has(k)) byResource.set(k, []);
    byResource.get(k).push(c);
  }
  const vmPriority = ["idle_shutdown", "pattern_change", "rightsize_gpu_sku", "commitment"];
  for (const [, list] of byResource.entries()) {
    const runnable = list.filter((c) => baseStatusById[c.id]?.status === "available");
    if (!runnable.length) continue;
    const winner = vmPriority.map((k) => runnable.find((c) => c.recoKey === k)).find(Boolean) || runnable[0];
    for (const c of runnable) {
      if (c.id === winner.id) continue;
      out[c.id] = { status: "suppressed", reason: `Suppressed by higher priority: ${winner.type}` };
    }
  }
  return out;
}

export function renderRecommendationsGpuComputeGcpPage(ctx) {
  const { state, setState } = ctx;
  setPageTitle("Cost recommendations · GPU compute (Google Cloud)", "GCP GPU cost recommendations are shown only when required metrics are available.");

  const conn = getSelectedGcpConnection(state);
  const controls = conn ? getRecoControlsForConnection(state, conn.id) : null;
  const catalog = computeRecommendationCatalog();
  const ui = getRecoUi(state);
  const selectedReco = catalog.find((r) => r.id === ui.evidenceId) || null;
  const query = String(ui.listQuery || "").trim().toLowerCase();
  const statusFilter = ui.statusFilter || "all";

  const baseStatusById = Object.fromEntries(catalog.map((r) => [r.id, statusForReco(conn, r, controls)]));
  const finalStatusById = applyPriorityAndSuppression(catalog, baseStatusById);
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
        el("h2", { class: "card__title", text: "Connect Google Cloud to unlock GPU cost recommendations" }),
        el("p", { class: "card__subtitle", text: "Create a Google Cloud connection so FinOps can pull inventory and GPU metrics." }),
        el("div", { class: "card__footer" }, [el("button", { class: "btn btn--primary", type: "button", text: "Connect Google Cloud", onclick: () => navigate("/integrations/gcp/connections/new") })]),
      ])
    : el("div", { class: "card" }, [
        el("h2", { class: "card__title", text: "Google Cloud GPU compute cost recommendations (sample + gating demo)" }),
        el("p", { class: "card__subtitle", text: "Includes evidence payloads and priority/suppression behavior." }),
        el("div", { class: "card__footer" }, [
          el("button", { class: "btn", type: "button", text: "View GCP metrics readiness", onclick: () => navigate("/integrations/gcp/gpu-metrics") }),
        ]),
      ]);

  const table = el("table", { class: "table" }, [
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
      filtered.map((r) => {
        const st = finalStatusById[r.id] || { status: "unknown", reason: "—" };
        const isSelected = ui.evidenceId === r.id;
        const isMuted = st.status === "suppressed";
        return el("tr", {}, [
          el("td", {}, [el("div", { text: r.type }), el("div", { class: "mono muted", text: `id=${r.id}` })]),
          el("td", {}, [el("div", { text: r.description }), el("div", { class: "mono muted", text: `severity=${r.severity}` })]),
          el("td", { class: "mono", text: r.service.toUpperCase() }),
          el("td", { class: "mono", text: r.resourceName }),
          el("td", { class: "mono", text: money(r.estimatedSavingsMonthly, r.currency) }),
          el("td", { class: "mono", text: r.confidence }),
          el("td", {}, [el("div", { class: "mono", text: st.status }), el("div", { class: "muted", text: st.reason })]),
          el("td", {}, [
            el("button", {
              class: "linkBtn",
              type: "button",
              text: "View metrics used",
              onclick: () => {
                setRecoUi(state, { evidenceId: r.id, evidenceTab: "summary" });
                setState({ ...state });
              },
            }),
          ]),
        ]);
      })
    ),
  ]);

  const listCard = el("div", { class: "card" }, [
    el("div", { class: "wizardHeader" }, [
      el("div", {}, [el("h3", { class: "card__title", text: "GPU compute cost recommendations (Google Cloud)" }), el("p", { class: "card__subtitle", text: "Search/filter + master-detail layout for consistency with Cost Management UI patterns." })]),
      el("div", { class: "btnRow" }, [el("button", { class: "btn btn--sm", type: "button", text: "User guide", onclick: () => window.open("docs/gpu-compute-recommendations-user-guide.md", "_blank") })]),
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
    // Rebuild rows with selection styling + click-to-open details
    el("table", { class: "table table--brand" }, [
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
          return el(
            "tr",
            {
              class: `${isSelected ? "isSelected" : ""} ${isMuted ? "isMuted" : ""}`.trim(),
              onclick: () => {
                setRecoUi(state, { evidenceId: r.id, evidenceTab: "summary" });
                setState({ ...state });
              },
            },
            [
              el("td", {}, [el("div", { text: r.type }), el("div", { class: "mono muted", text: `id=${r.id}` })]),
              el("td", {}, [el("div", { text: r.description }), el("div", { class: "mono muted", text: `severity=${r.severity}` })]),
              el("td", { class: "mono", text: r.service.toUpperCase() }),
              el("td", { class: "mono", text: r.resourceName }),
              el("td", { class: "mono", text: money(r.estimatedSavingsMonthly, r.currency) }),
              el("td", { class: "mono", text: r.confidence }),
              el("td", {}, [el("div", { class: "mono", text: st.status }), el("div", { class: "muted", text: st.reason })]),
              el("td", {}, [
                el("button", {
                  class: "linkBtn",
                  type: "button",
                  text: "View metrics used",
                  onclick: (e) => {
                    e.stopPropagation();
                    setRecoUi(state, { evidenceId: r.id, evidenceTab: "summary" });
                    setState({ ...state });
                  },
                }),
              ]),
            ]
          );
        })
      ),
    ]),
  ]);

  const detailsCard = selectedReco
    ? el("div", { class: "card" }, [
        el("div", { class: "wizardHeader" }, [
          el("div", {}, [el("h3", { class: "card__title", text: `Evidence: ${selectedReco.type}` }), el("p", { class: "card__subtitle", text: selectedReco.resourceId })]),
          el("div", { class: "btnRow" }, [el("button", { class: "btn btn--sm", type: "button", text: "Close", onclick: () => (setRecoUi(state, { evidenceId: null }), setState({ ...state })) })]),
        ]),
        el("div", { class: "callout" }, [el("div", { class: "callout__title", text: "Rule" }), el("p", { class: "callout__body", text: selectedReco.evidence.rule })]),
        el("div", { class: "callout", style: "margin-top:10px" }, [el("div", { class: "callout__title", text: "Decision" }), el("p", { class: "callout__body", text: selectedReco.evidence.decision })]),
        el("div", { class: "callout", style: "margin-top:10px" }, [
          el("div", { class: "callout__title", text: "Metrics used (summary)" }),
          el("p", { class: "callout__body mono", text: JSON.stringify(selectedReco.evidence.metricsUsed.map((m) => ({ name: m.name, derived: m.derived })), null, 0) }),
        ]),
      ])
    : el("div", { class: "card" }, [el("h3", { class: "card__title", text: "Recommendation details" }), el("p", { class: "card__subtitle", text: "Select a row from the list to view evidence." })]);

  return el("div", { class: "grid" }, [banner, el("div", { class: "grid grid--2" }, [listCard, detailsCard])]);
}


