import { el, setPageTitle } from "../ui.js";
import { navigate } from "../router.js";

function inr(n) {
  const v = Number(n) || 0;
  try {
    return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 2 }).format(v);
  } catch {
    return `₹ ${v.toFixed(2)}`;
  }
}

function badge(text, kind = "neutral") {
  return el("span", { class: `cmStatus cmStatus--${kind}`, text });
}

function mkRows(key) {
  // Mock rows per recommendation type. We keep the columns consistent per template to match screenshots.
  // Note: values are intentionally dummy (prototype only).
  const isGpu = key.includes("gpu");
  const isRightSize = key.includes("rightsize");
  const isIdle = key.includes("idle");

  const defaultAdvisory = isRightSize ? "Resize application load..." : isIdle ? "Stop idle resource" : "Enable Auto Scale...";

  const providers = [
    { csp: "Azure", project: "Proj-AZ", subscription: "Sub-AZ", baseSavings: 412000, recoType: "Predictive" },
    { csp: "GCP", project: "Proj-GCP", subscription: "Sub-GCP", baseSavings: 296536.91, recoType: "Absolute" },
    { csp: "AWS", project: "Proj-AWS", subscription: "Sub-AWS", baseSavings: 278000, recoType: "Predictive" },
    { csp: "AI Cloud", project: "AI-Proj", subscription: "AI-Sub", baseSavings: 355500, recoType: "Absolute" },
  ];

  const base = providers.map((p, idx) => {
    const n = idx + 1;
    const assetId = `${n}212432423323${n}`;
    return {
      csp: p.csp,
      project: p.project,
      subscription: p.subscription,
      assetId,
      resource: isGpu ? `gpu-vm-0${n}` : `Resource${n}`,
      creationDate: ["11-04-2025", "13-04-2025", "15-04-2025", "16-04-2025"][idx] || "11-04-2025",
      advisory: defaultAdvisory,
      savings: p.baseSavings,
      recoType: p.recoType,
      alertAgeing: String([4, 2, 3, 5][idx] || 2),
      lastUpdated: ["11-05-2025", "13-05-2025", "15-05-2025", "16-05-2025"][idx] || "11-05-2025",
      acknowledgedBy: "john.doe@ril.com",
      acknowledgedOn: ["15-04-2025", "16-04-2025", "16-04-2025", "17-04-2025"][idx] || "15-04-2025",
      status: "Open",
      scope: "vm",
      scheduleCategory: ["Night Only", "Weekend Only", "Night + Weekend", "Night Only"][idx] || "Night Only",
      schedule: ["8 pm - 8 am daily", "Fri(8pm) to Mon (8am)", "8pm-8am + Fri to Mon", "8 pm - 8 am daily"][idx] || "8 pm - 8 am daily",
      utilDetails: "—",
    };
  });

  // Tweak status for a bit of realism per screenshot variants.
  if (key === "instance_rightsizing") {
    base[1].status = "Not Scheduled";
    base[2].status = "Scheduled";
  }

  // GPU-specific scope: we need to clarify whether action applies to GPU, VM, or both.
  if (key === "idle_gpu_resource") {
    // Ensure we show one example per CSP.
    base[0].scope = "gpu+vm";
    base[0].advisory = "Stop GPU + VM (both idle)";
    base[1].scope = "gpu";
    base[1].advisory = "Stop GPU only (GPU idle, VM active)";
    base[2].scope = "gpu+vm";
    base[2].advisory = "Stop GPU + VM (both idle)";
    base[3].scope = "gpu";
    base[3].advisory = "Stop GPU only (GPU idle, VM active)";
    // Removed: "Stop VM only (VM idle, GPU active)" — considered highly unlikely for GPU workloads.
    return base;
  }
  if (key === "gpu_rightsizing") {
    // Ensure we show one example per CSP.
    base[0].scope = "gpu+vm";
    base[0].advisory = "Rightsize GPU + VM (both underutilized)";
    base[1].scope = "gpu";
    base[1].advisory = "Rightsize GPU only (GPU underutilized)";
    base[2].scope = "gpu+vm";
    base[2].advisory = "Rightsize GPU + VM (both underutilized)";
    base[3].scope = "gpu";
    base[3].advisory = "Rightsize GPU only (GPU underutilized)";
    // Removed: "Rightsize VM only (GPU utilized, VM underutilized)" — treated as highly unlikely for GPU workloads.
    return base;
  }

  return base;
}

function bySavingsDesc(rows) {
  return [...(rows || [])].sort((a, b) => {
    const av = Number(a?.savings) || 0;
    const bv = Number(b?.savings) || 0;
    if (bv !== av) return bv - av;
    // Secondary sort: CSP A→Z for deterministic display when savings tie.
    const c = String(a?.csp || "").localeCompare(String(b?.csp || ""));
    if (c) return c;
    return String(a?.resource || "").localeCompare(String(b?.resource || ""));
  });
}

function useCaseConfig(key) {
  const map = {
    instance_rightsizing: { title: "Instance Rightsizing", actions: ["Acknowledge", "View Asset Utilization Data"], template: "rightsizing" },
    database_rightsizing: { title: "Database Rightsizing (IaaS)", actions: ["Acknowledge", "View Asset Utilization Data"], template: "rightsizing" },
    gpu_rightsizing: {
      title: "GPU rightsizing recommendation",
      actions: ["Acknowledge", "View Asset Utilization Data"],
      template: "rightsizing",
      scopeHint:
        "GPU resources are typically attached to a VM. FinOps evaluates both GPU (utilization + memory) and VM CPU (utilization + memory) to decide whether to rightsize GPU, VM, or both. The Advisory column shows the recommended scope.",
    },

    idle_compute_instance: { title: "Idle Compute Instance", actions: ["Acknowledge", "View Usage Metric Details"], template: "idle" },
    idle_database_instance: { title: "Idle Database Instance", actions: ["Acknowledge", "View Usage Metric Details"], template: "idle" },
    idle_gpu_resource: {
      title: "Idle GPU resource",
      actions: ["Acknowledge", "View Asset Utilization Data"],
      template: "idle",
      scopeHint:
        "GPU resources are typically attached to a VM. FinOps evaluates both GPU (utilization + memory) and VM CPU (utilization + memory) to decide whether to stop GPU, VM, or both. The Advisory column shows the recommended scope.",
    },

    instance_scheduling: { title: "Resource Scheduler", actions: ["Acknowledge", "Apply Schedule", "View Usage Metric Details"], template: "scheduler" },

    reservation_purchase: { title: "Reservation Purchase Recommendation", actions: ["Acknowledge", "View Savings Estimate"], template: "generic" },
    paas_services: { title: "PaaS Services Recommendation", actions: ["Acknowledge", "View Usage Metric Details"], template: "generic" },
    old_snapshot_images: { title: "Old Snapshot and Images", actions: ["Acknowledge", "View Usage Metric Details"], template: "generic" },
    orphaned_resources: { title: "Orphaned Resources", actions: ["Acknowledge", "View Usage Metric Details"], template: "generic" },
  };

  return map[key] || { title: key, actions: ["Acknowledge"], template: "generic" };
}

function actionBar(actions) {
  // Placeholder; actions are wired in render function where we have selected-row context.
  return el("div", { class: "cmDetailActions" });
}

function tableRightsizing(rows) {
  // Matches screenshot: grouped headers Asset Details / Recommendation Details / Action Details
  const header1 = el("tr", {}, [
    el("th", { class: "cmChkHead", text: "" }),
    el("th", { colSpan: "4", class: "cmGroupHead", text: "Asset Details" }),
    el("th", { colSpan: "5", class: "cmGroupHead", text: "Recommendation Details" }),
    el("th", { colSpan: "3", class: "cmGroupHead", text: "Action Details" }),
  ]);

  const header2 = el("tr", {}, [
    el("th", { text: "" }),
    el("th", { text: "CSP" }),
    el("th", { text: "Subscription" }),
    el("th", { text: "Asset ID" }),
    el("th", { text: "Resource" }),
    el("th", { text: "Creation Date" }),
    el("th", { text: "Advisory" }),
    el("th", { text: "Cost Monthly Savings" }),
    el("th", { text: "Recommendation Type" }),
    el("th", { text: "Alert Ageing" }),
    el("th", { text: "Last Updated" }),
    el("th", { text: "Acknowledged By" }),
    el("th", { text: "Status" }),
  ]);

  const body = el(
    "tbody",
    {},
    rows.map((r, idx) =>
      el("tr", {}, [
        el("td", {}, [el("input", { type: "checkbox", checked: idx === 0 ? "checked" : null, "data-select": String(idx) })]),
        el("td", { text: r.csp }),
        el("td", { text: r.subscription }),
        el("td", { class: "mono", text: r.assetId }),
        el("td", { text: r.resource }),
        el("td", { text: r.creationDate }),
        el("td", { class: "cmTruncate", text: r.advisory }),
        el("td", { class: "cmMoney", text: inr(r.savings) }),
        el("td", { text: r.recoType }),
        el("td", { class: "mono", text: r.alertAgeing }),
        el("td", { text: r.lastUpdated }),
        el("td", { class: "mono", text: r.acknowledgedBy }),
        el("td", {}, [badge(r.status, r.status === "Open" ? "warn" : r.status === "Scheduled" ? "good" : "neutral")]),
      ])
    )
  );

  return el("table", { class: "table cmDetailTable" }, [el("thead", {}, [header1, header2]), body]);
}

function tableScheduler(rows) {
  // Matches scheduler screenshot: grouped headers Asset Details / Recommendation Details
  const header1 = el("tr", {}, [
    el("th", { class: "cmChkHead", text: "" }),
    el("th", { colSpan: "5", class: "cmGroupHead", text: "Asset Details" }),
    el("th", { colSpan: "5", class: "cmGroupHead", text: "Recommendation Details" }),
  ]);

  const header2 = el("tr", {}, [
    el("th", { text: "" }),
    el("th", { text: "CSP" }),
    el("th", { text: "Project" }),
    el("th", { text: "Subscription" }),
    el("th", { text: "Asset ID" }),
    el("th", { text: "Resource" }),
    el("th", { text: "Recommendation Category" }),
    el("th", { text: "Recommended Schedule" }),
    el("th", { text: "Created Date" }),
    el("th", { text: "Potential Monthly Cost Savings" }),
    el("th", { text: "Alert Ageing" }),
  ]);

  const body = el(
    "tbody",
    {},
    rows.map((r, idx) =>
      el("tr", {}, [
        el("td", {}, [el("input", { type: "checkbox", checked: idx === 0 ? "checked" : null, "data-select": String(idx) })]),
        el("td", { text: r.csp }),
        el("td", { text: r.project }),
        el("td", { text: r.subscription }),
        el("td", { class: "mono", text: r.assetId }),
        el("td", { text: r.resource }),
        el("td", { text: r.scheduleCategory }),
        el("td", { text: r.schedule }),
        el("td", { text: r.creationDate }),
        el("td", { class: "cmMoney", text: inr(r.savings) }),
        el("td", { class: "mono", text: r.alertAgeing }),
      ])
    )
  );

  return el("table", { class: "table cmDetailTable" }, [el("thead", {}, [header1, header2]), body]);
}

function tableGeneric(rows) {
  // A simplified generic table for other categories; still uses grouped headers for consistency.
  const header1 = el("tr", {}, [
    el("th", { class: "cmChkHead", text: "" }),
    el("th", { colSpan: "4", class: "cmGroupHead", text: "Asset Details" }),
    el("th", { colSpan: "4", class: "cmGroupHead", text: "Recommendation Details" }),
  ]);

  const header2 = el("tr", {}, [
    el("th", { text: "" }),
    el("th", { text: "CSP" }),
    el("th", { text: "Subscription" }),
    el("th", { text: "Asset ID" }),
    el("th", { text: "Resource" }),
    el("th", { text: "Created Date" }),
    el("th", { text: "Advisory" }),
    el("th", { text: "Potential Monthly Cost Savings" }),
    el("th", { text: "Alert Ageing" }),
  ]);

  const body = el(
    "tbody",
    {},
    rows.map((r, idx) =>
      el("tr", {}, [
        el("td", {}, [el("input", { type: "checkbox", checked: idx === 0 ? "checked" : null, "data-select": String(idx) })]),
        el("td", { text: r.csp }),
        el("td", { text: r.subscription }),
        el("td", { class: "mono", text: r.assetId }),
        el("td", { text: r.resource }),
        el("td", { text: r.creationDate }),
        el("td", { class: "cmTruncate", text: r.advisory }),
        el("td", { class: "cmMoney", text: inr(r.savings) }),
        el("td", { class: "mono", text: r.alertAgeing }),
      ])
    )
  );

  return el("table", { class: "table cmDetailTable" }, [el("thead", {}, [header1, header2]), body]);
}

export function renderCostAdvisoryRecommendationDetailPage(ctx, key) {
  const cfg = useCaseConfig(key);
  setPageTitle(`Cost Advisory · ${cfg.title}`, "Mock detail view (second layer) for recommendations list drilldown.");

  const crumb = el("div", { class: "cmBreadcrumb" }, [
    el("span", { class: "cmBreadcrumb__item", text: "FinOps" }),
    el("span", { class: "cmBreadcrumb__sep", text: "/" }),
    el("span", { class: "cmBreadcrumb__item", text: "Cost Advisory" }),
    el("span", { class: "cmBreadcrumb__sep", text: "/" }),
    el("span", { class: "cmBreadcrumb__item isActive", text: "Dashboard" }),
  ]);

  const topShell = el("div", { class: "cmDetailShell" }, [
    el("div", { class: "cmDetailTop" }, [
      el("button", { class: "cmBackLink", type: "button", text: "‹ Back", onclick: () => navigate("/cost-advisory/dashboard") }),
      crumb,
    ]),
    el("div", { class: "cmDetailTitleRow" }, [
      el("div", { class: "cmDetailTitle", text: `Description: ${cfg.title}` }),
    ]),
    cfg.scopeHint ? el("div", { class: "cmDetailHint", text: cfg.scopeHint }) : null,
    actionBar(cfg.actions),
    el("div", { class: "cmRuleLine" }),
  ]);

  const toolbar = el("div", { class: "cmDetailToolbar" }, [
    el("div", { class: "cmSearch" }, [
      el("span", { class: "cmSearch__icon", text: "🔍" }),
      el("input", { class: "cmSearch__input", type: "search", placeholder: "Search" }),
    ]),
    el("div", { class: "cmDetailToolbar__right" }, [
      el("button", { class: "cmIconBtn", type: "button", text: "⟳", onclick: () => alert("Mock refresh") }),
      el("button", { class: "cmIconBtn", type: "button", text: "⬇︎", onclick: () => alert("Mock download") }),
    ]),
  ]);

  // Always show highest savings potential at the top.
  const rows = bySavingsDesc(mkRows(key));
  const table =
    cfg.template === "scheduler" ? tableScheduler(rows) : cfg.template === "rightsizing" || cfg.template === "idle" ? tableRightsizing(rows) : tableGeneric(rows);

  // Single-selection behavior + action wiring.
  let selectedIdx = 0;
  const checkboxes = Array.from(table.querySelectorAll('input[type="checkbox"][data-select]'));
  function setSelected(nextIdx) {
    selectedIdx = Number(nextIdx) || 0;
    for (const cb of checkboxes) cb.checked = cb.getAttribute("data-select") === String(selectedIdx);
  }
  for (const cb of checkboxes) {
    cb.addEventListener("click", (e) => {
      const idx = Number(e.target?.getAttribute?.("data-select")) || 0;
      setSelected(idx);
    });
  }
  setSelected(0);

  const actionsHost = topShell.querySelector(".cmDetailActions");
  const selectedRow = () => rows[Math.max(0, Math.min(rows.length - 1, selectedIdx))];
  const hasAction = (label) => (cfg.actions || []).includes(label);

  function actionBtn(label, onClick) {
    return el("button", { type: "button", class: "cmActionLink", text: label, onclick: onClick });
  }

  if (actionsHost) {
    actionsHost.innerHTML = "";
    if (hasAction("Acknowledge")) actionsHost.appendChild(actionBtn("Acknowledge", () => alert("Mock acknowledge")));
    if (hasAction("Apply Schedule")) actionsHost.appendChild(actionBtn("Apply Schedule", () => alert("Mock apply schedule")));

    // Both labels should open the same utilization page (title differs there for scheduler).
    const utilLabel = hasAction("View Asset Utilization Data")
      ? "View Asset Utilization Data"
      : hasAction("View Usage Metric Details")
        ? "View Usage Metric Details"
        : null;

    if (utilLabel) {
      actionsHost.appendChild(
        actionBtn(utilLabel, () => {
          const r = selectedRow();
          const assetId = encodeURIComponent(String(r.assetId || ""));
          const resourceName = encodeURIComponent(String(r.resource || ""));
          const scope = encodeURIComponent(String(r.scope || ""));
          navigate(`/cost-advisory/utilization/${key}/${assetId}/${resourceName}/${scope}`);
        })
      );
    }

    if (hasAction("View Savings Estimate")) actionsHost.appendChild(actionBtn("View Savings Estimate", () => alert("Mock savings estimate")));
  }

  return el("div", { class: "grid" }, [
    // Keep the same global module tabs row for continuity with dashboard
    el("div", { class: "cmModuleTabs" }, [
      el("div", { class: "cmModuleTabs__logo", text: "FinOps" }),
      el(
        "div",
        { class: "cmModuleTabs__tabs" },
        ["Resources", "Observability", "Operations", "Security", "Orders & Requests", "Governance", "People", "FinOps"].map((t) =>
          el("div", { class: `cmModuleTab${t === "FinOps" ? " isActive" : ""}`, text: t })
        )
      ),
      el("div", { class: "cmModuleTabs__search" }, [
        el("input", { class: "cmTopSearch", type: "search", placeholder: "Find" }),
        el("span", { class: "cmTopSearch__icon", text: "🔎" }),
      ]),
    ]),
    el("div", { class: "card" }, [topShell, toolbar, el("div", { style: "height:10px" }), table]),
  ]);
}

