import { useEffect, useMemo, useState } from "react";
import { api, Customer, Dashboard, Finding, Hypothesis, Integration, ProductRate, RecommendationDefinition } from "./api";

const NAV_ITEMS = [
  ["dashboard", "Dashboard"],
  ["recommendations", "Recommendations"],
  ["advisories", "Production Monitor"],
  ["data_sources", "Connection Health"],
  ["aggregations", "Aggregation Engine"],
  ["failures", "Failure Analysis"],
  ["catalog", "Product Catalog"],
  ["rec_library", "Global Rec Library"],
  ["basic_readiness", "Basic Readiness"],
  ["integrations", "Integrations"],
  ["batch_sim", "Batch Simulation"],
  ["customer_view", "Customer Advisories"],
] as const;

type ViewId = (typeof NAV_ITEMS)[number][0];

type LoadState = {
  dashboard: Dashboard | null;
  definitions: RecommendationDefinition[];
  hypotheses: Hypothesis[];
  findings: Finding[];
  integrations: Integration[];
  productRates: ProductRate[];
  customers: Customer[];
  actions: Array<Record<string, unknown>>;
  outcomes: Array<Record<string, unknown>>;
  jobs: Record<string, unknown> | null;
};

const emptyState: LoadState = {
  dashboard: null,
  definitions: [],
  hypotheses: [],
  findings: [],
  integrations: [],
  productRates: [],
  customers: [],
  actions: [],
  outcomes: [],
  jobs: null,
};

export default function App() {
  const [activeView, setActiveView] = useState<ViewId>("dashboard");
  const [data, setData] = useState<LoadState>(emptyState);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [query, setQuery] = useState("");
  const [selectedDefinition, setSelectedDefinition] = useState<RecommendationDefinition | null>(null);
  const [selectedCustomer, setSelectedCustomer] = useState("cust-acme");
  const [lastRun, setLastRun] = useState<Record<string, unknown> | null>(null);

  async function refresh() {
    setLoading(true);
    setError("");
    try {
      const [dashboard, definitions, hypotheses, findings, integrations, productRates, customers, actions, outcomes, jobs] = await Promise.all([
        api.dashboard(),
        api.definitions("?limit=250"),
        api.hypotheses(),
        api.findings(),
        api.integrations(),
        api.productCatalog(),
        api.customers(),
        api.actions(),
        api.outcomes(),
        api.jobs(),
      ]);
      setData({ dashboard, definitions, hypotheses, findings, integrations, productRates, customers, actions, outcomes, jobs });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load recommendation engine data");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  const filteredDefinitions = useMemo(() => {
    const q = query.toLowerCase();
    return data.definitions.filter((definition) => {
      if (!q) return true;
      return [definition.id, definition.name, definition.category, definition.provider_scope, definition.recommendation_type]
        .join(" ")
        .toLowerCase()
        .includes(q);
    });
  }, [data.definitions, query]);

  async function runWorkflow(action: () => Promise<Record<string, unknown> | Hypothesis | Finding | Integration[]>, label: string) {
    setError("");
    try {
      const result = await action();
      setLastRun({ label, result });
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Workflow failed");
    }
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">CXP</span>
          <div>
            <strong>Recommendation Engine</strong>
            <small>Basic deterministic advisor</small>
          </div>
        </div>
        <nav>
          {NAV_ITEMS.map(([id, label]) => (
            <button key={id} className={activeView === id ? "active" : ""} onClick={() => setActiveView(id)}>
              {label}
            </button>
          ))}
        </nav>
      </aside>

      <main className="workspace">
        <header className="topbar">
          <div>
            <p className="eyebrow">FinOps Optimization</p>
            <h1>{NAV_ITEMS.find(([id]) => id === activeView)?.[1]}</h1>
          </div>
          <div className="toolbar">
            <button onClick={() => runWorkflow(api.runIngestion, "Metric ingestion")}>Pull metrics</button>
            <button onClick={() => runWorkflow(api.runEvaluator, "Evaluator run")}>Run evaluator</button>
            <button onClick={() => runWorkflow(api.runReconciler, "Reconciler")}>Reconcile</button>
            <button onClick={refresh}>Refresh</button>
          </div>
        </header>

        {error && <div className="alert error">{error}</div>}
        {lastRun && <div className="alert success">{String(lastRun.label)} completed.</div>}
        {loading ? <div className="card">Loading engine state...</div> : renderView()}
      </main>
    </div>
  );

  function renderView() {
    switch (activeView) {
      case "dashboard":
        return <DashboardView dashboard={data.dashboard} findings={data.findings} hypotheses={data.hypotheses} />;
      case "recommendations":
        return (
          <RecommendationsView
            hypotheses={data.hypotheses}
            definitions={filteredDefinitions}
            query={query}
            setQuery={setQuery}
            onInstantiate={(id) => runWorkflow(() => api.instantiate(id), "Hypothesis created")}
            onBacktest={(id) => runWorkflow(() => api.backtest(id), "Backtest")}
            onPublish={(id, target) => runWorkflow(() => api.publish(id, target), `Publish ${target}`)}
          />
        );
      case "advisories":
        return <ProductionMonitor findings={data.findings} actions={data.actions} outcomes={data.outcomes} onTransition={(id, state) => runWorkflow(() => api.transitionFinding(id, state), `Finding ${state}`)} />;
      case "data_sources":
        return <ConnectionHealth integrations={data.integrations} onSync={() => runWorkflow(api.syncIntegrations, "Integration sync")} />;
      case "aggregations":
        return <AggregationEngine definitions={filteredDefinitions} findings={data.findings} />;
      case "failures":
        return <FailureAnalysis findings={data.findings} />;
      case "catalog":
        return <ProductCatalog rates={data.productRates} />;
      case "rec_library":
        return <RecommendationLibrary definitions={filteredDefinitions} query={query} setQuery={setQuery} selected={selectedDefinition} setSelected={setSelectedDefinition} onEvaluate={(id) => runWorkflow(() => api.evaluateDefinition(id), "Definition evaluation")} />;
      case "basic_readiness":
        return <BasicReadiness data={data} />;
      case "integrations":
        return <IntegrationSetup integrations={data.integrations} />;
      case "batch_sim":
        return <BatchSimulation definitions={filteredDefinitions} onRun={(id) => runWorkflow(() => api.evaluateDefinition(id), "Batch simulation")} />;
      case "customer_view":
        return <CustomerAdvisories customers={data.customers} findings={data.findings} selectedCustomer={selectedCustomer} setSelectedCustomer={setSelectedCustomer} />;
    }
  }
}

function DashboardView({ dashboard, findings, hypotheses }: { dashboard: Dashboard | null; findings: Finding[]; hypotheses: Hypothesis[] }) {
  const totals = dashboard?.totals || {};
  return (
    <section className="grid">
      <Kpi title="Definitions" value={totals.recommendation_definitions ?? 0} />
      <Kpi title="Active hypotheses" value={totals.active_hypotheses ?? 0} />
      <Kpi title="Open findings" value={findings.filter((f) => f.state === "new").length} />
      <Kpi title="Monthly savings" value={`$${Number(totals.estimated_monthly_savings || 0).toLocaleString()}`} />
      <div className="card span-2">
        <h2>Category Savings</h2>
        <div className="bars">
          {(dashboard?.category_savings || []).map((row) => (
            <div key={row.category}>
              <span>{row.category}</span>
              <meter min="0" max="1000" value={Math.min(row.savings, 1000)} />
              <strong>${row.savings.toLocaleString()}</strong>
            </div>
          ))}
        </div>
      </div>
      <div className="card span-2">
        <h2>Lifecycle</h2>
        <Table
          rows={hypotheses.slice(0, 8).map((h) => ({
            Name: h.name,
            State: h.state,
            Version: h.version,
            Owner: h.owner_group,
          }))}
        />
      </div>
    </section>
  );
}

function RecommendationsView(props: {
  hypotheses: Hypothesis[];
  definitions: RecommendationDefinition[];
  query: string;
  setQuery: (value: string) => void;
  onInstantiate: (id: string) => void;
  onBacktest: (id: string) => void;
  onPublish: (id: string, target: string) => void;
}) {
  return (
    <section className="stack">
      <div className="card">
        <div className="split">
          <div>
            <h2>Authored Recommendations</h2>
            <p>Persisted hypotheses can be backtested, promoted to shadow, activated, and evaluated.</p>
          </div>
          <input placeholder="Search library to create..." value={props.query} onChange={(event) => props.setQuery(event.target.value)} />
        </div>
        <Table
          rows={props.hypotheses.map((h) => ({
            Name: h.name,
            State: h.state,
            Category: h.category,
            Severity: h.severity,
            Hits: String(h.last_backtest.hit_count ?? "-"),
            Savings: `$${Number(h.last_backtest.estimated_savings_monthly || 0).toLocaleString()}`,
            Actions: (
              <span className="row-actions">
                <button onClick={() => props.onBacktest(h.id)}>Backtest</button>
                <button onClick={() => props.onPublish(h.id, "shadow")}>Shadow</button>
                <button onClick={() => props.onPublish(h.id, "active")}>Active</button>
              </span>
            ),
          }))}
        />
      </div>
      <div className="card">
        <h2>Create From Global Library</h2>
        <Table
          rows={props.definitions.slice(0, 20).map((d) => ({
            ID: d.id,
            Name: d.name,
            Provider: d.provider_scope,
            Action: d.recommendation_type,
            Priority: d.priority,
            Complexity: d.implementation_complexity,
            Create: <button onClick={() => props.onInstantiate(d.id)}>Import as hypothesis</button>,
          }))}
        />
      </div>
    </section>
  );
}

function ProductionMonitor({ findings, actions, outcomes, onTransition }: { findings: Finding[]; actions: Array<Record<string, unknown>>; outcomes: Array<Record<string, unknown>>; onTransition: (id: string, state: string) => void }) {
  return (
    <section className="stack">
      <div className="card">
        <h2>Normalized Findings</h2>
        <Table
          rows={findings.map((f) => ({
            Resource: f.resource_id,
            Customer: f.customer_id,
            Provider: f.provider,
            State: f.state,
            Action: String(f.proposed_action.type || "Review"),
            Savings: `$${f.estimated_savings_monthly.toLocaleString()}`,
            Approve: (
              <span className="row-actions">
                <button onClick={() => onTransition(f.id, "approved")}>Approve</button>
                <button onClick={() => onTransition(f.id, "dismissed")}>Dismiss</button>
              </span>
            ),
          }))}
        />
      </div>
      <div className="two-col">
        <div className="card">
          <h2>Actions</h2>
          <Table rows={actions.map((a) => ({ Type: String(a.action_type), Status: String(a.status), Channel: String(a.delivery_channel), Approver: String(a.approver_group) }))} />
        </div>
        <div className="card">
          <h2>Outcomes</h2>
          <Table rows={outcomes.map((o) => ({ Window: `T+${String(o.window_days)}`, Status: String(o.status), Realized: `$${Number(o.realized_savings || 0).toLocaleString()}`, Variance: `${String(o.variance_pct || 0)}%` }))} />
        </div>
      </div>
    </section>
  );
}

function ConnectionHealth({ integrations, onSync }: { integrations: Integration[]; onSync: () => void }) {
  return (
    <div className="card">
      <div className="split">
        <h2>Provider Health</h2>
        <button onClick={onSync}>Sync manifests</button>
      </div>
      <Table rows={integrations.map((i) => ({ Provider: i.name, Category: i.category, Status: i.status, Credentials: i.credential_status, Coverage: `${i.signal_coverage_pct}%`, "Est. Cost": `$${i.estimated_monthly_cost}` }))} />
    </div>
  );
}

function AggregationEngine({ definitions, findings }: { definitions: RecommendationDefinition[]; findings: Finding[] }) {
  const signals = new Set(definitions.flatMap((d) => d.primary_metrics));
  return (
    <section className="grid">
      <Kpi title="Canonical signals" value={signals.size} />
      <Kpi title="Evaluated findings" value={findings.length} />
      <Kpi title="Backtest window" value="30d" />
      <div className="card span-3">
        <h2>Supported Deterministic Operators</h2>
        <p className="chips">{["<", ">", "<=", ">=", "==", "!=", "BETWEEN", "IN", "EXISTS", "IS_NULL", "avg", "p95", "p99", "sum", "rate"].map((op) => <span key={op}>{op}</span>)}</p>
      </div>
    </section>
  );
}

function FailureAnalysis({ findings }: { findings: Finding[] }) {
  const missing = findings.flatMap((f) => (f.evidence.missing_signals as string[] | undefined) || []);
  return (
    <div className="card">
      <h2>Suppression and Quality Signals</h2>
      <Table rows={[
        { Category: "Missing metric", Count: missing.length, Resolution: "Enable provider signal mapping or reduce recommendation scope." },
        { Category: "Stale pricing", Count: findings.filter((f) => !f.pricing_snapshot_id).length, Resolution: "Refresh Product Catalog." },
        { Category: "Dismissed", Count: findings.filter((f) => f.state === "dismissed").length, Resolution: "Review false-positive reasons." },
      ]} />
    </div>
  );
}

function ProductCatalog({ rates }: { rates: ProductRate[] }) {
  return (
    <div className="card">
      <h2>Product Catalog Coverage</h2>
      <Table rows={rates.map((r) => ({ Provider: r.provider, Type: r.resource_type, SKU: r.sku, Region: r.region, Rate: `$${r.rate}/${r.unit}`, Group: r.compatibility_group, Snapshot: r.snapshot_id }))} />
    </div>
  );
}

function RecommendationLibrary(props: {
  definitions: RecommendationDefinition[];
  query: string;
  setQuery: (value: string) => void;
  selected: RecommendationDefinition | null;
  setSelected: (definition: RecommendationDefinition) => void;
  onEvaluate: (id: string) => void;
}) {
  return (
    <section className="two-col wide-left">
      <div className="card">
        <div className="split">
          <h2>Global Recommendation Library</h2>
          <input placeholder="Search all imported config rows..." value={props.query} onChange={(event) => props.setQuery(event.target.value)} />
        </div>
        <Table rows={props.definitions.slice(0, 100).map((d) => ({ ID: d.id, Name: <button className="link" onClick={() => props.setSelected(d)}>{d.name}</button>, Provider: d.provider_scope, Action: d.recommendation_type, Priority: d.priority, Metrics: d.primary_metrics.length }))} />
      </div>
      <div className="card">
        <h2>Definition Detail</h2>
        {props.selected ? (
          <div className="detail">
            <h3>{props.selected.name}</h3>
            <p>{props.selected.notes_and_guardrails || props.selected.basic_engine_support}</p>
            <p className="chips">{props.selected.primary_metrics.map((metric) => <span key={metric}>{metric}</span>)}</p>
            <pre>{JSON.stringify(props.selected.baseline_thresholds, null, 2)}</pre>
            <button onClick={() => props.onEvaluate(props.selected!.id)}>Evaluate now</button>
          </div>
        ) : (
          <p>Select a recommendation row to inspect its config.</p>
        )}
      </div>
    </section>
  );
}

function BasicReadiness({ data }: { data: LoadState }) {
  const p0 = data.definitions.filter((d) => d.priority === "P0").length;
  const connected = data.integrations.filter((i) => i.status !== "not_configured").length;
  return (
    <section className="grid">
      <Kpi title="Imported definitions" value={data.definitions.length} />
      <Kpi title="P0 candidates" value={p0} />
      <Kpi title="Provider tracks" value={data.integrations.length} />
      <Kpi title="Usable integrations" value={connected} />
      <div className="card span-4">
        <h2>Readiness Gates</h2>
        <Table rows={[
          { Gate: "Signal coverage", Status: connected ? "Pass" : "Needs setup", Evidence: `${connected} providers synced` },
          { Gate: "Backtest coverage", Status: data.hypotheses.some((h) => Number(h.last_backtest.coverage_pct || 0) >= 90) ? "Pass" : "Run backtest", Evidence: ">= 90% required" },
          { Gate: "Product Catalog", Status: data.productRates.length ? "Pass" : "Missing", Evidence: `${data.productRates.length} seeded rates` },
          { Gate: "Audit events", Status: data.dashboard?.recent_audit_events.length ? "Pass" : "No events", Evidence: `${data.dashboard?.recent_audit_events.length || 0} events` },
        ]} />
      </div>
    </section>
  );
}

function IntegrationSetup({ integrations }: { integrations: Integration[] }) {
  return (
    <div className="card">
      <h2>Manifest-Rendered Integration Setup</h2>
      <Table rows={integrations.map((i) => ({ Provider: i.name, Category: i.category, Auth: String(i.health.probe || ""), Credentials: i.credential_status, Mode: String(i.health.mode || "sample"), Signals: `${i.signal_coverage_pct}%` }))} />
    </div>
  );
}

function BatchSimulation({ definitions, onRun }: { definitions: RecommendationDefinition[]; onRun: (id: string) => void }) {
  return (
    <div className="card">
      <h2>Batch Simulation</h2>
      <p>Run imported recommendation configs against seeded or live signals before activation.</p>
      <Table rows={definitions.slice(0, 30).map((d) => ({ ID: d.id, Name: d.name, Window: d.lookback_window, Metrics: d.primary_metrics.length, Action: <button onClick={() => onRun(d.id)}>Simulate</button> }))} />
    </div>
  );
}

function CustomerAdvisories({ customers, findings, selectedCustomer, setSelectedCustomer }: { customers: Customer[]; findings: Finding[]; selectedCustomer: string; setSelectedCustomer: (id: string) => void }) {
  const scoped = findings.filter((finding) => finding.customer_id === selectedCustomer);
  return (
    <section className="stack">
      <div className="card split">
        <h2>Customer Recommendations</h2>
        <select value={selectedCustomer} onChange={(event) => setSelectedCustomer(event.target.value)}>
          {customers.map((customer) => <option key={customer.id} value={customer.id}>{customer.name}</option>)}
        </select>
      </div>
      <div className="card">
        <Table rows={scoped.map((f) => ({ Resource: f.resource_id, Provider: f.provider, State: f.state, Action: String(f.proposed_action.type || "Review"), Savings: `$${f.estimated_savings_monthly.toLocaleString()}`, Owner: f.owner_group }))} />
      </div>
    </section>
  );
}

function Kpi({ title, value }: { title: string; value: string | number | unknown }) {
  return (
    <div className="card kpi">
      <small>{title}</small>
      <strong>{String(value)}</strong>
    </div>
  );
}

function Table({ rows }: { rows: Array<Record<string, unknown>> }) {
  if (!rows.length) return <p className="empty">No records yet. Run ingestion/evaluation or import recommendations.</p>;
  const columns = Object.keys(rows[0]);
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>{columns.map((column) => <th key={column}>{column}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={index}>
              {columns.map((column) => <td key={column}>{row[column] as never}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
