// Tag Policy — governance, normalization, and prediction (Phase 14).
// Backed by /api/tags/policy, /api/tags/normalize/*, /api/tags/predictions/*.
//
// Three problems solved here, each its own section:
//   1. Policy       — declare required/recommended tag keys (+ allowed values).
//   2. Normalization — cluster inconsistent raw key/value spellings and merge
//                      them into one canonical form with a single click.
//   3. Prediction    — for resources still missing a required tag, suggest a
//                      value from sibling resources or the account default,
//                      and let a human approve/reject before it's applied.
import { useState, useEffect, useCallback } from 'react';
import { Sidebar, Topbar, KPI, Tag, fmtUSD } from '../components/Shared.jsx';
import '../styles/tokens.css';

async function getJSON(url, opts) {
  const r = await fetch(url, opts);
  if (!r.ok) {
    const b = await r.json().catch(() => ({}));
    throw new Error(typeof b.detail === 'string' ? b.detail : `${r.status} ${r.statusText}`);
  }
  return r.json();
}
const postJSON = (url, body) => getJSON(url, {
  method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body || {}),
});
const putJSON = (url, body) => getJSON(url, {
  method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
});

function Btn({ children, onClick, kind = 'ghost', disabled, small }) {
  const base = {
    border: '1px solid var(--hairline)', borderRadius: 8, cursor: disabled ? 'default' : 'pointer',
    fontSize: small ? 11 : 12, fontWeight: 600, padding: small ? '4px 10px' : '7px 14px',
    opacity: disabled ? 0.5 : 1, background: 'var(--surface)', color: 'var(--ink)',
  };
  if (kind === 'primary') { base.background = 'var(--ink)'; base.color = 'var(--surface)'; base.border = '1px solid var(--ink)'; }
  if (kind === 'danger') { base.color = 'var(--negative, #d64545)'; }
  if (kind === 'positive') { base.color = 'var(--positive, #1a9e6e)'; }
  return <button style={base} onClick={onClick} disabled={disabled}>{children}</button>;
}

const inputStyle = {
  fontSize: 11.5, padding: '5px 8px', border: '1px solid var(--hairline)', borderRadius: 6,
  background: 'var(--surface)', color: 'var(--ink)', fontFamily: 'inherit',
};

// ── Section 1: Policy editor ──────────────────────────────────────────────

function PolicyEditor({ policy, onSaved }) {
  const [keys, setKeys] = useState(policy.required_keys || []);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => { setKeys(policy.required_keys || []); }, [policy]);

  const update = (i, field, value) => setKeys(k => k.map((row, idx) => idx === i ? { ...row, [field]: value } : row));
  const remove = (i) => setKeys(k => k.filter((_, idx) => idx !== i));
  const add = () => setKeys(k => [...k, { key: '', level: 'required', description: '', allowed_values: [] }]);

  const save = async () => {
    setSaving(true); setError('');
    try {
      const payload = { required_keys: keys.filter(k => k.key.trim()).map(k => ({
        key: k.key.trim(), level: k.level, description: k.description || '',
        allowed_values: Array.isArray(k.allowed_values) ? k.allowed_values : String(k.allowed_values || '').split(',').map(s => s.trim()).filter(Boolean),
      })) };
      await putJSON('/api/tags/policy', payload);
      onSaved();
    } catch (e) { setError(e.message); }
    finally { setSaving(false); }
  };

  return (
    <div className="card" style={{ padding: '12px 14px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
        <div className="section-title">Tag policy</div>
        <span style={{ fontSize: 11, color: 'var(--muted)' }}>Required/recommended keys, checked against every resource</span>
        <div style={{ flex: 1 }} />
        <Btn small onClick={add}>+ Add key</Btn>
      </div>
      <table className="tbl">
        <thead>
          <tr><th>Key</th><th>Level</th><th>Description</th><th>Allowed values (comma-separated, blank = any)</th><th></th></tr>
        </thead>
        <tbody>
          {keys.map((k, i) => (
            <tr key={i}>
              <td><input style={{ ...inputStyle, width: 110 }} value={k.key} onChange={e => update(i, 'key', e.target.value)} placeholder="Team" /></td>
              <td>
                <select style={inputStyle} value={k.level} onChange={e => update(i, 'level', e.target.value)}>
                  <option value="required">Required</option>
                  <option value="recommended">Recommended</option>
                </select>
              </td>
              <td><input style={{ ...inputStyle, width: 220 }} value={k.description} onChange={e => update(i, 'description', e.target.value)} /></td>
              <td>
                <input style={{ ...inputStyle, width: 260 }}
                       value={Array.isArray(k.allowed_values) ? k.allowed_values.join(', ') : k.allowed_values}
                       onChange={e => update(i, 'allowed_values', e.target.value)}
                       placeholder="production, staging, development" />
              </td>
              <td><Btn small kind="danger" onClick={() => remove(i)}>Remove</Btn></td>
            </tr>
          ))}
          {keys.length === 0 && <tr><td colSpan={5} style={{ color: 'var(--muted)', fontSize: 12 }}>No keys defined — add one above.</td></tr>}
        </tbody>
      </table>
      {error && <div style={{ marginTop: 8, fontSize: 12, color: 'var(--negative, #d64545)' }}>{error}</div>}
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: 10 }}>
        <Btn kind="primary" onClick={save} disabled={saving}>{saving ? 'Saving…' : 'Save policy'}</Btn>
      </div>
    </div>
  );
}

// ── Section 2: Key normalization ──────────────────────────────────────────

function KeyNormalization({ onApplied }) {
  const [suggestions, setSuggestions] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(null);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true); setError('');
    try { setSuggestions((await getJSON('/api/tags/normalize/keys?days=90')).suggestions); }
    catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const merge = async (s) => {
    setBusy(s.canonical_key_suggestion);
    try {
      const aliases = s.variants.map(v => v.key).filter(k => k !== s.canonical_key_suggestion);
      const res = await postJSON('/api/tags/normalize/keys/apply', {
        canonical_key: s.canonical_key_suggestion, aliases, bulk_apply: true,
      });
      await load();
      onApplied?.(res);
    } catch (e) { setError(e.message); }
    finally { setBusy(null); }
  };

  return (
    <div className="card" style={{ padding: '12px 14px' }}>
      <div className="section-title" style={{ marginBottom: 4 }}>Tag key normalization</div>
      <div style={{ fontSize: 11.5, color: 'var(--muted)', marginBottom: 8 }}>
        Different resources spell the same tag key differently (e.g. <code>team</code> vs <code>Team</code> vs <code>squad</code>).
        Merge variants into one canonical key so chargeback and compliance reporting see them as the same field.
      </div>
      {error && <div style={{ fontSize: 12, color: 'var(--negative, #d64545)', marginBottom: 8 }}>{error}</div>}
      {loading ? (
        <div style={{ fontSize: 12, color: 'var(--muted)' }}>Scanning tag keys…</div>
      ) : !suggestions?.length ? (
        <div style={{ fontSize: 12, color: 'var(--muted)' }}>No inconsistent key spellings found in the last 90 days.</div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {suggestions.map(s => (
            <div key={s.canonical_key_suggestion} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 10px', border: '1px solid var(--hairline)', borderRadius: 8 }}>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 12, fontWeight: 600 }}>→ {s.canonical_key_suggestion}</div>
                <div style={{ display: 'flex', gap: 6, marginTop: 4, flexWrap: 'wrap' }}>
                  {s.variants.map(v => (
                    <span key={v.key} style={{ fontSize: 10.5, padding: '2px 7px', borderRadius: 999, background: 'var(--hairline)' }}>
                      {v.key} <span style={{ color: 'var(--muted)' }}>×{v.occurrences}</span>
                    </span>
                  ))}
                </div>
              </div>
              <Btn kind="primary" small disabled={busy === s.canonical_key_suggestion} onClick={() => merge(s)}>
                {busy === s.canonical_key_suggestion ? 'Merging…' : 'Merge'}
              </Btn>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Section 3: Value normalization ────────────────────────────────────────

function ValueNormalization({ policyKeys, onApplied }) {
  const [key, setKey] = useState(policyKeys[0]?.key || 'Environment');
  const [suggestions, setSuggestions] = useState(null);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(null);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    if (!key) return;
    setLoading(true); setError('');
    try { setSuggestions((await getJSON(`/api/tags/normalize/values?key=${encodeURIComponent(key)}&days=90`)).suggestions); }
    catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }, [key]);
  useEffect(() => { load(); }, [load]);

  const merge = async (s) => {
    setBusy(s.canonical_value_suggestion);
    try {
      const aliases = s.variants.map(v => v.value).filter(v => v !== s.canonical_value_suggestion);
      const res = await postJSON('/api/tags/normalize/values/apply', {
        tag_key: key, canonical_value: s.canonical_value_suggestion, aliases, bulk_apply: true,
      });
      await load();
      onApplied?.(res);
    } catch (e) { setError(e.message); }
    finally { setBusy(null); }
  };

  return (
    <div className="card" style={{ padding: '12px 14px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
        <div className="section-title">Tag value normalization</div>
        <select style={inputStyle} value={key} onChange={e => setKey(e.target.value)}>
          {(policyKeys.length ? policyKeys.map(k => k.key) : ['Environment', 'Team', 'CostCenter']).map(k => (
            <option key={k} value={k}>{k}</option>
          ))}
        </select>
      </div>
      <div style={{ fontSize: 11.5, color: 'var(--muted)', marginBottom: 8 }}>
        Values like <code>prod</code>, <code>Production</code>, <code>PROD</code> should count as one value for policy and reporting.
      </div>
      {error && <div style={{ fontSize: 12, color: 'var(--negative, #d64545)', marginBottom: 8 }}>{error}</div>}
      {loading ? (
        <div style={{ fontSize: 12, color: 'var(--muted)' }}>Scanning values for {key}…</div>
      ) : !suggestions?.length ? (
        <div style={{ fontSize: 12, color: 'var(--muted)' }}>No inconsistent values found for {key} in the last 90 days.</div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {suggestions.map(s => (
            <div key={s.canonical_value_suggestion} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 10px', border: '1px solid var(--hairline)', borderRadius: 8 }}>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 12, fontWeight: 600 }}>→ {s.canonical_value_suggestion}</div>
                <div style={{ display: 'flex', gap: 6, marginTop: 4, flexWrap: 'wrap' }}>
                  {s.variants.map(v => (
                    <span key={v.value} style={{ fontSize: 10.5, padding: '2px 7px', borderRadius: 999, background: 'var(--hairline)' }}>
                      {v.value} <span style={{ color: 'var(--muted)' }}>×{v.occurrences}</span>
                    </span>
                  ))}
                </div>
              </div>
              <Btn kind="primary" small disabled={busy === s.canonical_value_suggestion} onClick={() => merge(s)}>
                {busy === s.canonical_value_suggestion ? 'Merging…' : 'Merge'}
              </Btn>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Section 4: Prediction ─────────────────────────────────────────────────

function Predictions({ policyKeys }) {
  const [predictions, setPredictions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [busyId, setBusyId] = useState(null);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true); setError('');
    try { setPredictions((await getJSON('/api/tags/predictions?status=pending')).predictions); }
    catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const generate = async () => {
    setGenerating(true); setError('');
    try {
      await postJSON('/api/tags/predictions/generate', { tag_keys: policyKeys.map(k => k.key), days: 90 });
      await load();
    } catch (e) { setError(e.message); }
    finally { setGenerating(false); }
  };

  const resolve = async (id, action) => {
    setBusyId(id);
    try { await postJSON(`/api/tags/predictions/${id}/${action}`); await load(); }
    catch (e) { setError(e.message); }
    finally { setBusyId(null); }
  };

  return (
    <div className="card" style={{ padding: '12px 14px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
        <div className="section-title">Missing-tag prediction</div>
        <div style={{ flex: 1 }} />
        <Btn kind="primary" small onClick={generate} disabled={generating}>{generating ? 'Generating…' : 'Generate suggestions'}</Btn>
      </div>
      <div style={{ fontSize: 11.5, color: 'var(--muted)', marginBottom: 8 }}>
        For resources missing a required tag, suggests a value from sibling resources in the same provider/service/region
        (or the account default when no sibling signal exists). Review and approve before it's applied.
      </div>
      {error && <div style={{ fontSize: 12, color: 'var(--negative, #d64545)', marginBottom: 8 }}>{error}</div>}
      {loading ? (
        <div style={{ fontSize: 12, color: 'var(--muted)' }}>Loading predictions…</div>
      ) : predictions.length === 0 ? (
        <div style={{ fontSize: 12, color: 'var(--muted)' }}>No pending predictions — click "Generate suggestions" to scan untagged resources.</div>
      ) : (
        <table className="tbl">
          <thead>
            <tr><th>Resource</th><th>Tag</th><th>Suggested value</th><th>Confidence</th><th>Method</th><th></th></tr>
          </thead>
          <tbody>
            {predictions.map(p => (
              <tr key={p.id}>
                <td>
                  {p.resource_name}
                  <div style={{ fontSize: 10, color: 'var(--muted)' }}>{p.provider} · {p.service}</div>
                </td>
                <td><b>{p.tag_key}</b></td>
                <td>{p.predicted_value}</td>
                <td>
                  <span style={{
                    fontSize: 10.5, padding: '2px 7px', borderRadius: 999,
                    background: p.confidence >= 0.8 ? 'rgba(26,158,110,.12)' : p.confidence >= 0.5 ? 'rgba(224,180,57,.15)' : 'rgba(214,69,69,.1)',
                    color: p.confidence >= 0.8 ? 'var(--positive, #1a9e6e)' : p.confidence >= 0.5 ? '#b8860b' : 'var(--negative, #d64545)',
                  }}>{Math.round(p.confidence * 100)}%</span>
                </td>
                <td style={{ fontSize: 10.5, color: 'var(--muted)' }}>{p.method.replace('_', ' ')}</td>
                <td>
                  <div style={{ display: 'flex', gap: 6 }}>
                    <Btn small kind="positive" disabled={busyId === p.id} onClick={() => resolve(p.id, 'approve')}>Approve</Btn>
                    <Btn small kind="danger" disabled={busyId === p.id} onClick={() => resolve(p.id, 'reject')}>Reject</Btn>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}

// ── Page ───────────────────────────────────────────────────────────────────

export default function TagPolicy({ onNavigate }) {
  const [policy, setPolicy] = useState(null);
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState('');

  const loadPolicy = useCallback(async () => {
    try {
      const [p, s] = await Promise.all([
        getJSON('/api/tags/policy'),
        getJSON('/api/tags/compliance/summary?days=30'),
      ]);
      setPolicy(p); setSummary(s);
    } catch (e) { setError(e.message); }
  }, []);
  useEffect(() => { loadPolicy(); }, [loadPolicy]);

  return (
    <div className="lumen" style={{ height: '100vh' }}>
      <Sidebar active="tags" onNavigate={onNavigate} />
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        <Topbar crumbs={['Workspace', 'Tag Policy']} />
        <div style={{ flex: 1, overflowY: 'auto', padding: '16px 18px' }}>
          <div style={{ maxWidth: 1100, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 12 }}>

            {summary && (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10 }}>
                <KPI label="Compliance" value={`${summary.compliance_pct}%`} sub={`${summary.compliant}/${summary.total_resources} resources`} accent="var(--positive, #1a9e6e)" />
                <KPI label="Non-compliant" value={String(summary.non_compliant)} sub="missing a required tag" accent="var(--negative, #d64545)" />
                <KPI label="Partial" value={String(summary.partial)} sub="missing a recommended tag" accent="var(--warning, #b8860b)" />
                <KPI label="Cost at risk" value={fmtUSD(summary.cost_at_risk)} sub="untagged/non-compliant spend" accent="var(--d3)" />
              </div>
            )}

            {error && <div className="card" style={{ padding: '10px 14px', fontSize: 12, color: 'var(--negative, #d64545)' }}>{error}</div>}

            {policy && <PolicyEditor policy={policy} onSaved={loadPolicy} />}
            <KeyNormalization onApplied={loadPolicy} />
            {policy && <ValueNormalization policyKeys={policy.required_keys || []} onApplied={loadPolicy} />}
            {policy && <Predictions policyKeys={policy.required_keys || []} />}

            <div style={{ fontSize: 11, color: 'var(--muted)', textAlign: 'center', padding: '4px 0 12px' }}>
              See the full resource-level breakdown on the <a onClick={() => onNavigate?.('resources')} style={{ cursor: 'pointer', color: 'var(--accent)' }}>Resources</a> page.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
