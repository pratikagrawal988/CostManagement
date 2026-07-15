// BudgetManager — live budget CRUD backed by /api/budgets (Phase 13).
// Rendered inside BudgetsScreen via the Live/Demo toggle.
import { useState, useEffect, useCallback } from 'react';

const fmtUSD = v => '$' + Number(v || 0).toLocaleString(undefined, { maximumFractionDigits: 0 });

const STATUS_TONE = {
  ok:      { c: 'var(--positive, #1a9e6e)', bg: 'rgba(26,158,110,.1)',  label: 'On track' },
  warning: { c: '#b8860b',                  bg: 'rgba(224,180,57,.15)', label: 'Warning' },
  over:    { c: 'var(--negative, #d64545)', bg: 'rgba(214,69,69,.1)',   label: 'Over budget' },
};

const inputStyle = {
  width: '100%', boxSizing: 'border-box', fontSize: 12, padding: '7px 10px',
  border: '1px solid var(--hairline)', borderRadius: 8, background: 'var(--surface)', color: 'var(--ink)',
  fontFamily: 'inherit',
};

function Btn({ children, onClick, kind = 'ghost', disabled, small }) {
  const base = {
    border: '1px solid var(--hairline)', borderRadius: 8, cursor: disabled ? 'default' : 'pointer',
    fontSize: small ? 11 : 12, fontWeight: 600, padding: small ? '4px 10px' : '7px 14px',
    opacity: disabled ? 0.5 : 1, background: 'var(--surface)', color: 'var(--ink)',
  };
  if (kind === 'primary') { base.background = 'var(--ink)'; base.color = 'var(--surface)'; base.border = '1px solid var(--ink)'; }
  if (kind === 'danger')  { base.color = 'var(--negative, #d64545)'; }
  return <button style={base} onClick={onClick} disabled={disabled}>{children}</button>;
}

function UtilBar({ pct, status }) {
  const t = STATUS_TONE[status] || STATUS_TONE.ok;
  return (
    <div style={{ position: 'relative', height: 6, borderRadius: 3, background: 'var(--hairline)', overflow: 'hidden' }}>
      <div style={{ position: 'absolute', inset: 0, width: `${Math.min(pct, 100)}%`, background: t.c, borderRadius: 3 }} />
    </div>
  );
}

function CreateForm({ onClose, onSaved }) {
  const [form, setForm] = useState({
    name: '', amount: '', period: 'monthly', provider_name: '', service_category: '',
    warn_at: '80', owner_email: '',
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const save = async () => {
    const amount = parseFloat(form.amount);
    if (!form.name.trim()) { setError('Name is required.'); return; }
    if (!amount || amount <= 0) { setError('Amount must be a positive number.'); return; }
    const warn = parseFloat(form.warn_at) || 80;
    setSaving(true); setError('');
    try {
      const r = await fetch('/api/budgets', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: form.name.trim(),
          amount,
          period: form.period,
          provider_name: form.provider_name,
          service_category: form.service_category.trim(),
          alert_thresholds: [warn, 100],
          owner_email: form.owner_email.trim(),
          enabled: true,
        }),
      });
      if (!r.ok) {
        const b = await r.json().catch(() => ({}));
        throw new Error(typeof b.detail === 'string' ? b.detail : `${r.status} ${r.statusText}`);
      }
      onSaved();
    } catch (e) { setError(e.message); }
    finally { setSaving(false); }
  };

  return (
    <div className="card" style={{ padding: '12px 14px' }}>
      <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>New budget</div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10 }}>
        <div>
          <label style={{ display: 'block', fontSize: 11, fontWeight: 600, marginBottom: 4 }}>Name *</label>
          <input style={inputStyle} placeholder="Compute – Production" value={form.name} onChange={e => set('name', e.target.value)} />
        </div>
        <div>
          <label style={{ display: 'block', fontSize: 11, fontWeight: 600, marginBottom: 4 }}>Amount (USD) *</label>
          <input style={inputStyle} placeholder="50000" value={form.amount} onChange={e => set('amount', e.target.value)} />
        </div>
        <div>
          <label style={{ display: 'block', fontSize: 11, fontWeight: 600, marginBottom: 4 }}>Period</label>
          <select style={inputStyle} value={form.period} onChange={e => set('period', e.target.value)}>
            <option value="monthly">Monthly</option>
            <option value="quarterly">Quarterly</option>
            <option value="annual">Annual</option>
          </select>
        </div>
        <div>
          <label style={{ display: 'block', fontSize: 11, fontWeight: 600, marginBottom: 4 }}>Provider scope</label>
          <select style={inputStyle} value={form.provider_name} onChange={e => set('provider_name', e.target.value)}>
            <option value="">All providers</option>
            <option value="AWS">AWS</option>
            <option value="Azure">Azure</option>
            <option value="GCP">GCP</option>
          </select>
        </div>
        <div>
          <label style={{ display: 'block', fontSize: 11, fontWeight: 600, marginBottom: 4 }}>Service category scope</label>
          <input style={inputStyle} placeholder="Compute (empty = all)" value={form.service_category} onChange={e => set('service_category', e.target.value)} />
        </div>
        <div>
          <label style={{ display: 'block', fontSize: 11, fontWeight: 600, marginBottom: 4 }}>Warn at (%)</label>
          <input style={inputStyle} placeholder="80" value={form.warn_at} onChange={e => set('warn_at', e.target.value)} />
        </div>
      </div>
      {error && (
        <div style={{ marginTop: 10, fontSize: 12, color: 'var(--negative, #d64545)', background: 'rgba(214,69,69,.08)', borderRadius: 8, padding: '8px 10px' }}>{error}</div>
      )}
      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 10 }}>
        <Btn onClick={onClose}>Cancel</Btn>
        <Btn kind="primary" onClick={save} disabled={saving}>{saving ? 'Creating…' : 'Create budget'}</Btn>
      </div>
    </div>
  );
}

function BudgetRow({ b, onChanged }) {
  const [busy, setBusy] = useState(false);
  const t = STATUS_TONE[b.status] || STATUS_TONE.ok;

  const call = async (method, body) => {
    setBusy(true);
    try {
      await fetch(`/api/budgets/${encodeURIComponent(b.id)}`, {
        method,
        headers: body ? { 'Content-Type': 'application/json' } : undefined,
        body: body ? JSON.stringify(body) : undefined,
      });
      onChanged();
    } finally { setBusy(false); }
  };

  const scope = [b.scope.provider_name, b.scope.service_category, b.scope.sub_account_id].filter(Boolean).join(' · ') || 'All spend';

  return (
    <div style={{ padding: '10px 0', borderTop: '1px solid var(--hairline)', opacity: b.enabled ? 1 : .55 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 12.5, fontWeight: 700 }}>{b.name}</span>
            <span style={{ fontSize: 10.5, fontWeight: 700, color: t.c, background: t.bg, padding: '2px 8px', borderRadius: 999 }}>{t.label}</span>
            <span style={{ fontSize: 10.5, color: 'var(--muted)' }}>{b.period}</span>
          </div>
          <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 1 }}>{scope}</div>
        </div>
        <div style={{ textAlign: 'right', whiteSpace: 'nowrap' }}>
          <div style={{ fontSize: 12.5, fontWeight: 700, fontFamily: 'var(--font-num, monospace)' }}>
            {fmtUSD(b.actual)} <span style={{ color: 'var(--muted)', fontWeight: 400 }}>/ {fmtUSD(b.amount)}</span>
          </div>
          <div style={{ fontSize: 10.5, color: 'var(--muted)' }}>
            {b.utilization_pct}% used · forecast {fmtUSD(b.forecast_eop)} ({b.forecast_pct}%)
          </div>
        </div>
        <div style={{ display: 'flex', gap: 6 }}>
          <Btn small disabled={busy} onClick={() => call('PATCH', { enabled: !b.enabled })}>{b.enabled ? 'Pause' : 'Resume'}</Btn>
          <Btn small kind="danger" disabled={busy} onClick={() => { if (window.confirm(`Delete budget "${b.name}"?`)) call('DELETE'); }}>Delete</Btn>
        </div>
      </div>
      <div style={{ marginTop: 6 }}>
        <UtilBar pct={b.utilization_pct} status={b.status} />
      </div>
    </div>
  );
}

export default function BudgetManager() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true); setError('');
    try {
      const r = await fetch('/api/budgets');
      if (r.status === 403) throw new Error('Your role does not include budgets:read.');
      if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
      setData(await r.json());
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const budgets = data?.budgets || [];
  const alerts = data?.alerts || [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12, maxWidth: 860 }}>
      <div style={{ display: 'flex', alignItems: 'flex-end', gap: 10 }}>
        <div style={{ flex: 1 }}>
          <div className="section-title" style={{ fontSize: 14 }}>Budget definitions</div>
          <div style={{ fontSize: 11.5, color: 'var(--muted)', marginTop: 2 }}>
            Actuals computed live from FOCUS cost data{data?.anchor ? ` · period anchored to ${data.anchor}` : ''}.
            Alerts fire at each threshold (warning / 100%).
          </div>
        </div>
        <Btn kind="primary" onClick={() => setCreating(v => !v)}>{creating ? 'Close' : '+ New budget'}</Btn>
      </div>

      {alerts.length > 0 && (
        <div className="card" style={{ padding: '10px 14px', borderLeft: '3px solid var(--negative, #d64545)' }}>
          <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: .3, color: 'var(--negative, #d64545)', marginBottom: 4 }}>
            {alerts.length} BUDGET ALERT{alerts.length > 1 ? 'S' : ''}
          </div>
          {alerts.map(a => (
            <div key={a.id} style={{ fontSize: 11.5, color: 'var(--muted)' }}>
              <b style={{ color: 'var(--ink)' }}>{a.name}</b> is at {a.utilization_pct}% of {fmtUSD(a.amount)} ({a.status === 'over' ? 'over budget' : 'above warning threshold'})
            </div>
          ))}
        </div>
      )}

      {error && <div className="card" style={{ padding: '10px 14px', fontSize: 12, color: 'var(--negative, #d64545)' }}>{error}</div>}

      {creating && <CreateForm onClose={() => setCreating(false)} onSaved={() => { setCreating(false); load(); }} />}

      <div className="card" style={{ padding: '4px 14px 8px' }}>
        {loading ? (
          <div style={{ fontSize: 12, color: 'var(--muted)', padding: '10px 0' }}>Loading budgets…</div>
        ) : budgets.length === 0 && !error ? (
          <div style={{ fontSize: 12, color: 'var(--muted)', padding: '10px 0' }}>
            No budgets defined yet — create the first one. Scope it to a provider or service category, or leave open for total spend.
          </div>
        ) : budgets.map(b => <BudgetRow key={b.id} b={b} onChanged={load} />)}
      </div>
    </div>
  );
}
