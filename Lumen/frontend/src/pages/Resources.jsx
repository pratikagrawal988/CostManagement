// Resources — live resource inventory backed by /api/tags/resources + /api/tags/compliance/summary.
// Shows cost, tags, and tag-policy compliance per resource; filters for
// untagged/non-compliant; links out to Tag Policy for normalization/prediction.
import { useState, useEffect, useCallback } from 'react';
import { Sidebar, Topbar, KPI, Tag, fmtUSD } from '../components/Shared.jsx';
import '../styles/tokens.css';

async function getJSON(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
  return r.json();
}

const STATUS_TAG = {
  compliant:     { tone: 'positive', label: 'Compliant' },
  partial:       { tone: 'warning',  label: 'Partial' },
  non_compliant: { tone: 'negative', label: 'Non-compliant' },
};

function ChargebackChips({ chargeback }) {
  const entries = Object.entries(chargeback || {}).filter(([, v]) => v);
  if (!entries.length) return <span style={{ fontSize: 11, color: 'var(--muted)' }}>No tags</span>;
  return (
    <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
      {entries.map(([k, v]) => (
        <span key={k} style={{
          fontSize: 10.5, padding: '2px 7px', borderRadius: 999,
          background: 'var(--hairline)', color: 'var(--ink)',
        }}>{k}: <b>{v}</b></span>
      ))}
    </div>
  );
}

function MissingChips({ missingRequired, missingRecommended }) {
  return (
    <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap' }}>
      {(missingRequired || []).map(k => (
        <span key={k} style={{ fontSize: 10, padding: '2px 6px', borderRadius: 999, background: 'rgba(214,69,69,.1)', color: 'var(--negative, #d64545)' }}>
          missing {k}
        </span>
      ))}
      {(missingRecommended || []).map(k => (
        <span key={k} style={{ fontSize: 10, padding: '2px 6px', borderRadius: 999, background: 'rgba(224,180,57,.15)', color: '#b8860b' }}>
          {k} not normalized
        </span>
      ))}
    </div>
  );
}

export default function Resources({ onNavigate }) {
  const [summary, setSummary] = useState(null);
  const [resources, setResources] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [providerFilter, setProviderFilter] = useState('');
  const [q, setQ] = useState('');
  const [days, setDays] = useState(30);

  const load = useCallback(async () => {
    setLoading(true); setError('');
    try {
      const params = new URLSearchParams({ days: String(days) });
      if (statusFilter) params.set('status', statusFilter);
      if (providerFilter) params.set('provider', providerFilter);
      if (q) params.set('q', q);
      const [sum, res] = await Promise.all([
        getJSON(`/api/tags/compliance/summary?days=${days}`),
        getJSON(`/api/tags/resources?${params.toString()}`),
      ]);
      setSummary(sum);
      setResources(res.resources || []);
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }, [days, statusFilter, providerFilter, q]);

  useEffect(() => { load(); }, [load]);

  return (
    <div className="lumen" style={{ height: '100vh' }}>
      <Sidebar active="resources" onNavigate={onNavigate} />
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        <Topbar crumbs={['Workspace', 'Resources']} />
        <div style={{ flex: 1, overflowY: 'auto', padding: '16px 18px' }}>
          <div style={{ maxWidth: 1180, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 12 }}>

            {summary && (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10 }}>
                <KPI label="Resources tracked" value={String(summary.total_resources)} sub={`last ${days}d`} accent="var(--accent)" />
                <KPI label="Tag compliance" value={`${summary.compliance_pct}%`} sub={`${summary.compliant} of ${summary.total_resources} compliant`} accent="var(--positive, #1a9e6e)" />
                <KPI label="Cost at risk" value={fmtUSD(summary.cost_at_risk)} sub="spend on non-compliant resources" accent="var(--negative, #d64545)" />
                <KPI label="Total spend" value={fmtUSD(summary.total_cost)} sub={`${summary.non_compliant} non-compliant · ${summary.partial} partial`} accent="var(--d3)" />
              </div>
            )}

            {summary?.by_missing_key?.length > 0 && (
              <div className="card" style={{ padding: '10px 14px' }}>
                <div className="section-title" style={{ marginBottom: 6 }}>Most common gaps</div>
                <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                  {summary.by_missing_key.map(m => (
                    <span key={m.key} style={{ fontSize: 11.5, padding: '4px 10px', borderRadius: 999, background: 'var(--hairline)' }}>
                      <b>{m.key}</b> · {m.resource_count} resources · {fmtUSD(m.cost)}
                    </span>
                  ))}
                </div>
                <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 8 }}>
                  Fix normalization or generate predictions from the <a onClick={() => onNavigate?.('tags')} style={{ cursor: 'pointer', color: 'var(--accent)' }}>Tag Policy</a> page.
                </div>
              </div>
            )}

            <div className="card" style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 14px', borderBottom: '1px solid var(--hairline)', flexWrap: 'wrap' }}>
                <div className="section-title">Resource inventory</div>
                <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}
                        style={{ fontSize: 11.5, padding: '4px 8px', border: '1px solid var(--hairline)', borderRadius: 6, background: 'var(--surface)' }}>
                  <option value="">All statuses</option>
                  <option value="compliant">Compliant</option>
                  <option value="partial">Partial</option>
                  <option value="non_compliant">Non-compliant</option>
                </select>
                <select value={providerFilter} onChange={e => setProviderFilter(e.target.value)}
                        style={{ fontSize: 11.5, padding: '4px 8px', border: '1px solid var(--hairline)', borderRadius: 6, background: 'var(--surface)' }}>
                  <option value="">All providers</option>
                  <option value="AWS">AWS</option>
                  <option value="Azure">Azure</option>
                  <option value="GCP">GCP</option>
                </select>
                <input placeholder="Search resource…" value={q} onChange={e => setQ(e.target.value)}
                       style={{ fontSize: 11.5, padding: '4px 8px', border: '1px solid var(--hairline)', borderRadius: 6, background: 'var(--surface)', minWidth: 160 }} />
                <select value={days} onChange={e => setDays(Number(e.target.value))}
                        style={{ fontSize: 11.5, padding: '4px 8px', border: '1px solid var(--hairline)', borderRadius: 6, background: 'var(--surface)' }}>
                  <option value={7}>7 days</option>
                  <option value={30}>30 days</option>
                  <option value={90}>90 days</option>
                </select>
                <div style={{ flex: 1 }} />
                <span style={{ fontSize: 11, color: 'var(--muted)' }}>{resources.length} shown</span>
              </div>

              {error && <div style={{ padding: '10px 14px', fontSize: 12, color: 'var(--negative, #d64545)' }}>{error}</div>}
              {loading ? (
                <div style={{ padding: '16px 14px', fontSize: 12, color: 'var(--muted)' }}>Loading resources…</div>
              ) : resources.length === 0 ? (
                <div style={{ padding: '16px 14px', fontSize: 12, color: 'var(--muted)' }}>No resources match these filters.</div>
              ) : (
                <div style={{ overflow: 'auto' }}>
                  <table className="tbl">
                    <thead>
                      <tr>
                        <th>Resource</th>
                        <th>Provider / Service</th>
                        <th className="num">Cost</th>
                        <th>Status</th>
                        <th>Chargeback tags</th>
                        <th>Gaps</th>
                      </tr>
                    </thead>
                    <tbody>
                      {resources.map(r => {
                        const st = STATUS_TAG[r.status] || STATUS_TAG.non_compliant;
                        return (
                          <tr key={r.resource_id}>
                            <td style={{ color: 'var(--ink)', fontWeight: 500 }}>
                              {r.resource_name}
                              <div style={{ fontSize: 10, color: 'var(--muted)', fontFamily: 'var(--font-num, monospace)' }}>{r.resource_id}</div>
                            </td>
                            <td>
                              <div style={{ fontSize: 11.5 }}>{r.provider}</div>
                              <div style={{ fontSize: 10.5, color: 'var(--muted)' }}>{r.service}{r.region ? ` · ${r.region}` : ''}</div>
                            </td>
                            <td className="num">{fmtUSD(r.total_cost)}</td>
                            <td><Tag tone={st.tone}>{st.label}</Tag></td>
                            <td><ChargebackChips chargeback={r.chargeback} /></td>
                            <td><MissingChips missingRequired={r.missing_required} missingRecommended={r.missing_recommended} /></td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
