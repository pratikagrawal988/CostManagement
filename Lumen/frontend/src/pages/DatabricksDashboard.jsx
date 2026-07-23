// Databricks dashboard — DBU consumption, job/pipeline cost, cluster
// utilization/idle waste, and reconciliation against the underlying CSP
// infra cost. Backed by /api/databricks/* (see routes_databricks.py).
import { useState, useEffect, useCallback } from 'react';
import { Sidebar, Topbar, KPI, Tag, StackedArea, fmtUSD } from '../components/Shared.jsx';
import '../styles/tokens.css';

async function getJSON(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json();
}

const CLUSTER_TYPE_COLORS = {
  all_purpose: 'var(--accent)', job: 'var(--d2)', sql_warehouse: 'var(--d3)', dlt: 'var(--positive, #1a9e6e)',
};

export default function DatabricksDashboard({ onNavigate }) {
  const [days, setDays] = useState(30);
  const [overview, setOverview] = useState(null);
  const [dbuCost, setDbuCost] = useState(null);
  const [jobs, setJobs] = useState(null);
  const [clusters, setClusters] = useState(null);
  const [reconGroupBy, setReconGroupBy] = useState('workspace');
  const [recon, setRecon] = useState(null);
  const [wastefulOnly, setWastefulOnly] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true); setError('');
    try {
      const [ov, dbu, jb, cl, rc] = await Promise.all([
        getJSON(`/api/databricks/overview?days=${days}`),
        getJSON(`/api/databricks/dbu-cost?days=${days}`),
        getJSON(`/api/databricks/jobs?days=${days}`),
        getJSON(`/api/databricks/clusters?days=${days}${wastefulOnly ? '&wasteful_only=true' : ''}`),
        getJSON(`/api/databricks/reconciliation?days=${days}&group_by=${reconGroupBy}`),
      ]);
      setOverview(ov); setDbuCost(dbu); setJobs(jb); setClusters(cl); setRecon(rc);
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }, [days, wastefulOnly, reconGroupBy]);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="lumen" style={{ height: '100vh' }}>
      <Sidebar active="databricks" onNavigate={onNavigate} />
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        <Topbar crumbs={['Workspace', 'Databricks']} />
        <div style={{ flex: 1, overflowY: 'auto', padding: '16px 18px' }}>
          <div style={{ maxWidth: 1180, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 12 }}>

            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <div className="section-title" style={{ fontSize: 14 }}>Databricks cost & utilization</div>
              <div style={{ fontSize: 11.5, color: 'var(--muted)' }}>
                DBU platform fee marries with underlying cloud infra cost to show the true total.
              </div>
              <div style={{ flex: 1 }} />
              <select value={days} onChange={e => setDays(Number(e.target.value))}
                      style={{ fontSize: 11.5, padding: '4px 8px', border: '1px solid var(--hairline)', borderRadius: 6, background: 'var(--surface)' }}>
                <option value={7}>7 days</option>
                <option value={30}>30 days</option>
                <option value={60}>60 days</option>
              </select>
            </div>

            {error && <div className="card" style={{ padding: '10px 14px', fontSize: 12, color: 'var(--negative, #d64545)' }}>{error}</div>}

            {overview && (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10 }}>
                <KPI label="True total cost" value={fmtUSD(overview.true_total_cost)}
                     sub={`DBU ${fmtUSD(overview.dbu_cost)} + infra ${fmtUSD(overview.infra_cost)}`} accent="var(--ink)" />
                <KPI label="Platform markup" value={`${overview.platform_markup_pct}%`}
                     sub="DBU fee on top of CSP infra cost" accent="var(--d3)" />
                <KPI label="Idle cost" value={fmtUSD(overview.idle_cost)}
                     sub={`${overview.utilization_pct}% avg utilization`} accent="var(--negative, #d64545)" />
                <KPI label="Job success rate" value={`${overview.job_success_rate_pct}%`}
                     sub={`${overview.job_runs} runs · ${overview.job_failures} failed`} accent="var(--positive, #1a9e6e)" />
              </div>
            )}

            {overview && (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10 }}>
                <KPI label="Clusters" value={String(overview.cluster_count)} sub={`across ${overview.workspace_count} workspaces`} accent="var(--accent)" />
                <KPI label="Active vs idle hours" value={`${Math.round(overview.active_hours)} / ${Math.round(overview.idle_hours)}`} sub="active / idle node-hours" accent="var(--muted)" />
                <KPI label="DBU consumption" value={overview.dbu_quantity.toLocaleString()} sub="total DBUs this period" accent="var(--d2)" />
              </div>
            )}

            {dbuCost && (
              <div className="card" style={{ padding: '12px 14px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                  <div className="section-title">DBU cost trend</div>
                  <div style={{ flex: 1 }} />
                  <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                    {dbuCost.by_cluster_type.map(c => (
                      <Tag key={c.cluster_type} tone="neutral">{c.cluster_type}: {fmtUSD(c.cost)}</Tag>
                    ))}
                  </div>
                </div>
                <StackedArea
                  mode="line"
                  series={[{ label: 'DBU cost', color: 'var(--accent)', data: dbuCost.timeseries.map(t => t.cost) }]}
                  xLabels={dbuCost.timeseries.map((t, i) => (i % Math.ceil(dbuCost.timeseries.length / 8) === 0 ? t.date.slice(5) : ''))}
                  yFormatter={v => '$' + Math.round(v).toLocaleString()}
                />
              </div>
            )}

            {recon && (
              <div className="card" style={{ padding: '12px 14px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                  <div className="section-title">Cost reconciliation — DBU platform fee vs. CSP infra</div>
                  <div style={{ flex: 1 }} />
                  <select value={reconGroupBy} onChange={e => setReconGroupBy(e.target.value)}
                          style={{ fontSize: 11.5, padding: '4px 8px', border: '1px solid var(--hairline)', borderRadius: 6, background: 'var(--surface)' }}>
                    <option value="workspace">By workspace</option>
                    <option value="provider">By cloud provider</option>
                    <option value="cluster">By cluster</option>
                  </select>
                </div>
                <div style={{ fontSize: 11.5, color: 'var(--muted)', marginBottom: 8 }}>
                  Overall markup: <b style={{ color: 'var(--ink)' }}>{recon.overall_markup_pct}%</b> — the Databricks
                  platform fee lands on top of {fmtUSD(recon.total_infra_cost)} of underlying cloud compute,
                  for a true total of {fmtUSD(recon.total_true_cost)}.
                </div>
                {recon.rows.length > 0 && (
                  <StackedArea
                    mode="bar"
                    series={[
                      { label: 'Infra (CSP)', color: 'var(--muted)', data: recon.rows.slice(0, 10).map(r => r.infra_cost) },
                      { label: 'DBU (Databricks)', color: 'var(--accent)', data: recon.rows.slice(0, 10).map(r => r.dbu_cost) },
                    ]}
                    xLabels={recon.rows.slice(0, 10).map(r => r.group.length > 14 ? r.group.slice(0, 12) + '…' : r.group)}
                    yFormatter={v => '$' + Math.round(v).toLocaleString()}
                  />
                )}
                <table className="tbl" style={{ marginTop: 8 }}>
                  <thead><tr><th>{reconGroupBy}</th><th className="num">Infra cost</th><th className="num">DBU cost</th><th className="num">True total</th><th className="num">Markup</th></tr></thead>
                  <tbody>
                    {recon.rows.map(r => (
                      <tr key={r.group}>
                        <td style={{ color: 'var(--ink)', fontWeight: 500 }}>{r.group}</td>
                        <td className="num">{fmtUSD(r.infra_cost)}</td>
                        <td className="num">{fmtUSD(r.dbu_cost)}</td>
                        <td className="num">{fmtUSD(r.true_total_cost)}</td>
                        <td className="num">{r.platform_markup_pct}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {jobs && (
              <div className="card" style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 14px', borderBottom: '1px solid var(--hairline)' }}>
                  <div className="section-title">Job & pipeline cost</div>
                  <span style={{ fontSize: 11, color: 'var(--muted)' }}>{jobs.total_runs} runs · {jobs.total_failures} failed</span>
                </div>
                <table className="tbl">
                  <thead>
                    <tr><th>Job</th><th className="num">Runs</th><th className="num">Success rate</th><th className="num">Avg duration</th><th className="num">Total cost</th></tr>
                  </thead>
                  <tbody>
                    {jobs.jobs.map(j => (
                      <tr key={j.job_name}>
                        <td style={{ color: 'var(--ink)', fontWeight: 500 }}>{j.job_name}</td>
                        <td className="num">{j.run_count}</td>
                        <td className="num">
                          <span style={{ color: j.success_rate_pct >= 95 ? 'var(--positive, #1a9e6e)' : j.success_rate_pct >= 85 ? '#b8860b' : 'var(--negative, #d64545)' }}>
                            {j.success_rate_pct}%
                          </span>
                        </td>
                        <td className="num">{Math.round(j.avg_duration_seconds / 60)}m</td>
                        <td className="num">{fmtUSD(j.total_cost)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {clusters && (
              <div className="card" style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 14px', borderBottom: '1px solid var(--hairline)' }}>
                  <div className="section-title">Cluster utilization & idle cost</div>
                  <label style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 11.5, cursor: 'pointer' }}>
                    <input type="checkbox" checked={wastefulOnly} onChange={e => setWastefulOnly(e.target.checked)} />
                    Wasteful only
                  </label>
                  <div style={{ flex: 1 }} />
                  <span style={{ fontSize: 11, color: 'var(--muted)' }}>{clusters.count} clusters</span>
                </div>
                <div style={{ overflow: 'auto', maxHeight: 420 }}>
                  <table className="tbl">
                    <thead>
                      <tr>
                        <th>Cluster</th><th>Type</th><th className="num">CPU util</th>
                        <th className="num">Idle hrs</th><th className="num">Idle cost</th>
                        <th className="num">DBU cost</th><th className="num">Infra cost</th><th className="num">True total</th><th></th>
                      </tr>
                    </thead>
                    <tbody>
                      {clusters.clusters.map(c => (
                        <tr key={c.cluster_id}>
                          <td style={{ color: 'var(--ink)', fontWeight: 500 }}>
                            {c.cluster_name}
                            <div style={{ fontSize: 10, color: 'var(--muted)' }}>{c.workspace_name} · {c.cloud_provider} · {c.node_type_id}</div>
                          </td>
                          <td>
                            <span style={{ fontSize: 10.5, padding: '2px 7px', borderRadius: 999, background: 'var(--hairline)', color: CLUSTER_TYPE_COLORS[c.cluster_type] || 'var(--ink)' }}>
                              {c.cluster_type}
                            </span>
                          </td>
                          <td className="num">{c.avg_cpu_utilization_pct}%</td>
                          <td className="num">{c.idle_hours}</td>
                          <td className="num">{fmtUSD(c.idle_cost)}</td>
                          <td className="num">{fmtUSD(c.dbu_cost)}</td>
                          <td className="num">{fmtUSD(c.infra_cost)}</td>
                          <td className="num">{fmtUSD(c.true_total_cost)}</td>
                          <td>{c.wasteful && <Tag tone="negative">wasteful</Tag>}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {loading && <div style={{ fontSize: 12, color: 'var(--muted)', textAlign: 'center', padding: 20 }}>Loading Databricks data…</div>}
          </div>
        </div>
      </div>
    </div>
  );
}
