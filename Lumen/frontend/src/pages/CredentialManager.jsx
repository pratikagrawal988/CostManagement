/**
 * CredentialManager.jsx
 * Unified UI for managing AWS / Azure / GCP provider credentials.
 * Covers: add config, edit config, test connection, enable/disable, delete.
 */

import { useState, useEffect, useCallback } from 'react';

const API = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8088';
const TENANT = 'tenant-demo';

// ── Icons ─────────────────────────────────────────────────────────────────────
const Icon = {
  aws:     <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-5 h-5"><path d="M6.5 14.5s-2 .5-2 2.5 2 2.5 2 2.5h11s2-.5 2-2.5-2-2.5-2-2.5"/><path d="M12 4v10M8 6l4-3 4 3"/></svg>,
  azure:   <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-5 h-5"><path d="M6 8l6-4 6 4v8l-6 4-6-4z"/><path d="M12 4v16M6 8l6 4 6-4"/></svg>,
  gcp:     <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="w-5 h-5"><circle cx="12" cy="12" r="8"/><path d="M12 4a8 8 0 0 1 8 8H12z"/></svg>,
  check:   <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-4 h-4"><path d="M5 13l4 4L19 7"/></svg>,
  error:   <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-4 h-4"><circle cx="12" cy="12" r="10"/><path d="M15 9l-6 6M9 9l6 6"/></svg>,
  warn:    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-4 h-4"><path d="M12 9v4M12 17h.01M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/></svg>,
  add:     <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-4 h-4"><path d="M12 5v14M5 12h14"/></svg>,
  trash:   <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-4 h-4"><path d="M3 6h18M19 6l-1 14H6L5 6M10 11v6M14 11v6M9 6V4h6v2"/></svg>,
  refresh: <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-4 h-4"><path d="M23 4v6h-6"/><path d="M1 20v-6h6"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>,
  eye:     <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-4 h-4"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>,
  eyeOff:  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="w-4 h-4"><path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/><line x1="1" y1="1" x2="23" y2="23"/></svg>,
};

// ── Status Badge ──────────────────────────────────────────────────────────────
function StatusBadge({ status }) {
  const map = {
    ok:      { bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200', icon: Icon.check,   label: 'Connected'  },
    error:   { bg: 'bg-red-50',     text: 'text-red-700',     border: 'border-red-200',     icon: Icon.error,   label: 'Error'      },
    warning: { bg: 'bg-amber-50',   text: 'text-amber-700',   border: 'border-amber-200',   icon: Icon.warn,    label: 'Warning'    },
    pending: { bg: 'bg-slate-50',   text: 'text-slate-500',   border: 'border-slate-200',   icon: null,         label: 'Not tested' },
  };
  const s = map[status] || map.pending;
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium border ${s.bg} ${s.text} ${s.border}`}>
      {s.icon && <span className="shrink-0">{s.icon}</span>}
      {s.label}
    </span>
  );
}

// ── Provider Card ─────────────────────────────────────────────────────────────
function ProviderCard({ provider, configs, onAdd, onTest, onDelete, testing }) {
  const meta = {
    aws:   { label: 'Amazon Web Services', color: 'text-orange-600', bg: 'bg-orange-50', border: 'border-orange-200', icon: Icon.aws,   hint: 'Connect via cross-account IAM role for Cost & Usage Reports.' },
    azure: { label: 'Microsoft Azure',     color: 'text-blue-600',   bg: 'bg-blue-50',   border: 'border-blue-200',   icon: Icon.azure, hint: 'Use a Service Principal with Cost Management Reader role.'     },
    gcp:   { label: 'Google Cloud',        color: 'text-teal-600',   bg: 'bg-teal-50',   border: 'border-teal-200',   icon: Icon.gcp,   hint: 'Export billing to BigQuery and provide a Service Account JSON.'  },
  }[provider];

  return (
    <div className={`rounded-xl border ${meta.border} overflow-hidden`}>
      {/* Header */}
      <div className={`flex items-center justify-between px-5 py-4 ${meta.bg}`}>
        <div className="flex items-center gap-3">
          <span className={`${meta.color}`}>{meta.icon}</span>
          <div>
            <div className="font-semibold text-slate-800">{meta.label}</div>
            <div className="text-xs text-slate-500 mt-0.5">{meta.hint}</div>
          </div>
        </div>
        <button
          onClick={() => onAdd(provider)}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-sm font-medium text-slate-700 hover:bg-slate-50 shadow-sm"
        >
          {Icon.add} Add config
        </button>
      </div>

      {/* Config rows */}
      {configs.length === 0 ? (
        <div className="px-5 py-5 text-sm text-slate-400 text-center">
          No {meta.label} configurations yet
        </div>
      ) : (
        <div className="divide-y divide-slate-100">
          {configs.map(cfg => (
            <ConfigRow
              key={cfg.id}
              cfg={cfg}
              onTest={() => onTest(cfg.id)}
              onDelete={() => onDelete(cfg.id)}
              testing={testing === cfg.id}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function ConfigRow({ cfg, onTest, onDelete, testing }) {
  const [expanded, setExpanded] = useState(false);
  return (
    <div className="px-5 py-3">
      <div className="flex items-center gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-medium text-sm text-slate-800 truncate">{cfg.name}</span>
            <StatusBadge status={cfg.test_status} />
            {!cfg.enabled && (
              <span className="text-xs bg-slate-100 text-slate-500 px-2 py-0.5 rounded-full">Disabled</span>
            )}
          </div>
          <div className="text-xs text-slate-400 mt-0.5">
            {cfg.provider === 'aws'   && `s3://${cfg.s3_bucket}${cfg.s3_prefix ? '/' + cfg.s3_prefix : ''} · ${cfg.aws_role_arn}`}
            {cfg.provider === 'azure' && `Subscription: ${cfg.subscription_id} · Client: ${cfg.client_id}`}
            {cfg.provider === 'gcp'   && `Project: ${cfg.gcp_project_id} · Dataset: ${cfg.bigquery_dataset}.${cfg.bigquery_table}`}
          </div>
          {cfg.test_message && cfg.test_status === 'error' && (
            <div className="text-xs text-red-600 mt-1 font-mono bg-red-50 px-2 py-1 rounded">{cfg.test_message}</div>
          )}
          {cfg.last_sync_at && (
            <div className="text-xs text-slate-400 mt-0.5">
              Last sync: {new Date(cfg.last_sync_at).toLocaleString()}
            </div>
          )}
        </div>
        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={onTest}
            disabled={testing}
            className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs font-medium bg-white border border-slate-200 text-slate-600 hover:bg-slate-50 disabled:opacity-50"
          >
            {testing ? (
              <span className="w-3 h-3 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
            ) : Icon.refresh}
            Test
          </button>
          <button
            onClick={onDelete}
            className="p-1.5 rounded-lg text-slate-400 hover:text-red-500 hover:bg-red-50"
          >
            {Icon.trash}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Add Config Modal ──────────────────────────────────────────────────────────
function AddModal({ provider, onClose, onSaved }) {
  const [form, setForm] = useState({
    name: provider === 'aws' ? 'AWS CUR' : provider === 'azure' ? 'Azure Cost' : 'GCP Billing',
    // AWS
    s3_bucket: '', s3_prefix: '', aws_role_arn: '', aws_external_id: '', aws_region: 'us-east-1',
    // Azure
    azure_tenant_id: '', client_id: '', client_secret: '', subscription_id: '', management_group_id: '',
    // GCP
    gcp_project_id: '', bigquery_dataset: '', bigquery_table: 'gcp_billing_export_v1', service_account_json: '',
  });
  const [saving, setSaving] = useState(false);
  const [error,  setError]  = useState('');
  const [showSecret, setShowSecret] = useState(false);

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const save = async () => {
    setSaving(true); setError('');
    try {
      const endpoint = `/api/credentials/${provider}`;
      const body = { tenant_id: TENANT, ...form };
      const r = await fetch(`${API}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!r.ok) throw new Error((await r.json()).detail || r.statusText);
      onSaved();
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  const Field = ({ label, name, type = 'text', placeholder = '', hint = '', textarea = false }) => (
    <div>
      <label className="block text-xs font-medium text-slate-600 mb-1">{label}</label>
      {textarea ? (
        <textarea
          rows={4}
          className="w-full text-sm border border-slate-200 rounded-lg px-3 py-2 font-mono focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
          placeholder={placeholder}
          value={form[name]}
          onChange={e => set(name, e.target.value)}
        />
      ) : (
        <div className="relative">
          <input
            type={type === 'password' && !showSecret ? 'password' : 'text'}
            className="w-full text-sm border border-slate-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder={placeholder}
            value={form[name]}
            onChange={e => set(name, e.target.value)}
          />
          {type === 'password' && (
            <button
              type="button"
              onClick={() => setShowSecret(v => !v)}
              className="absolute right-2.5 top-2.5 text-slate-400 hover:text-slate-600"
            >
              {showSecret ? Icon.eyeOff : Icon.eye}
            </button>
          )}
        </div>
      )}
      {hint && <p className="text-xs text-slate-400 mt-1">{hint}</p>}
    </div>
  );

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] flex flex-col">
        <div className="px-6 py-4 border-b border-slate-100 flex items-center justify-between">
          <h2 className="font-semibold text-slate-800">
            Add {provider === 'aws' ? 'AWS' : provider === 'azure' ? 'Azure' : 'GCP'} Configuration
          </h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 text-xl leading-none">×</button>
        </div>

        <div className="overflow-y-auto flex-1 px-6 py-5 space-y-4">
          <Field label="Config Name" name="name" placeholder="AWS CUR – Production" />

          {provider === 'aws' && (<>
            <Field label="S3 Bucket" name="s3_bucket" placeholder="my-cur-bucket" />
            <Field label="S3 Prefix" name="s3_prefix" placeholder="cur/reports (optional)" />
            <Field label="IAM Role ARN" name="aws_role_arn" placeholder="arn:aws:iam::123456789:role/FinOpsReadRole"
              hint="Cross-account role that grants s3:GetObject on the CUR bucket." />
            <Field label="External ID" name="aws_external_id" placeholder="finops-external-id (optional)" />
            <Field label="AWS Region" name="aws_region" placeholder="us-east-1" />
          </>)}

          {provider === 'azure' && (<>
            <Field label="Azure Tenant ID (AAD)" name="azure_tenant_id" placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" />
            <Field label="Client ID (App ID)" name="client_id" placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" />
            <Field label="Client Secret" name="client_secret" type="password" placeholder="••••••••"
              hint="Service Principal secret. Stored encrypted — never logged." />
            <Field label="Subscription ID" name="subscription_id" placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx" />
            <Field label="Management Group ID" name="management_group_id" placeholder="Optional — for tenant-wide billing" />
          </>)}

          {provider === 'gcp' && (<>
            <Field label="GCP Project ID" name="gcp_project_id" placeholder="my-gcp-project" />
            <Field label="BigQuery Dataset" name="bigquery_dataset" placeholder="billing_export" />
            <Field label="BigQuery Table" name="bigquery_table" placeholder="gcp_billing_export_v1" />
            <Field label="Service Account JSON" name="service_account_json" textarea
              placeholder='Paste your service account JSON here { "type": "service_account", ... }'
              hint="Stored encrypted. The SA needs BigQuery Data Viewer + BigQuery Job User roles." />
          </>)}

          {error && (
            <div className="bg-red-50 border border-red-200 rounded-lg px-3 py-2 text-sm text-red-700">{error}</div>
          )}
        </div>

        <div className="px-6 py-4 border-t border-slate-100 flex justify-end gap-3">
          <button onClick={onClose} className="px-4 py-2 rounded-lg text-sm font-medium text-slate-600 hover:bg-slate-50 border border-slate-200">
            Cancel
          </button>
          <button
            onClick={save}
            disabled={saving}
            className="px-5 py-2 rounded-lg text-sm font-medium bg-slate-900 text-white hover:bg-slate-700 disabled:opacity-50"
          >
            {saving ? 'Saving…' : 'Save Configuration'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Main Component ────────────────────────────────────────────────────────────
export default function CredentialManager() {
  const [data,    setData]    = useState(null);
  const [loading, setLoading] = useState(true);
  const [modal,   setModal]   = useState(null);   // provider string
  const [testing, setTesting] = useState(null);   // config_id being tested
  const [error,   setError]   = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetch(`${API}/api/credentials?tenant_id=${TENANT}`);
      setData(await r.json());
    } catch (e) {
      setError('Could not load configurations.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleTest = async (configId) => {
    setTesting(configId);
    try {
      await fetch(`${API}/api/credentials/${configId}/test?tenant_id=${TENANT}`, { method: 'POST' });
      await load();
    } finally {
      setTesting(null);
    }
  };

  const handleDelete = async (configId) => {
    if (!confirm('Remove this configuration? This cannot be undone.')) return;
    await fetch(`${API}/api/credentials/${configId}?tenant_id=${TENANT}`, { method: 'DELETE' });
    await load();
  };

  const providers = ['aws', 'azure', 'gcp'];

  // Count connected / total
  const allConfigs = data ? [...(data.providers.aws || []), ...(data.providers.azure || []), ...(data.providers.gcp || [])] : [];
  const connected  = allConfigs.filter(c => c.test_status === 'ok').length;

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="max-w-4xl mx-auto px-6 py-8">

        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-slate-900">Cloud Provider Credentials</h1>
          <p className="text-slate-500 mt-1">
            Connect your cloud providers to start ingesting cost data. All credentials are encrypted at rest.
          </p>
          {allConfigs.length > 0 && (
            <div className="mt-3 inline-flex items-center gap-2 text-sm">
              <span className="w-2 h-2 rounded-full bg-emerald-400" />
              <span className="text-slate-600">{connected} of {allConfigs.length} configured providers connected</span>
            </div>
          )}
        </div>

        {/* Info banner */}
        <div className="bg-blue-50 border border-blue-200 rounded-xl px-5 py-4 mb-6 text-sm text-blue-800">
          <strong>Data flow:</strong> AWS CUR → S3 → 5-min poll → FOCUS normalisation → dashboards.
          Azure &amp; GCP billing exports are synced hourly via their respective APIs.
          No data leaves your environment — credentials are used server-side only.
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl px-5 py-3 mb-6 text-sm text-red-700">{error}</div>
        )}

        {loading ? (
          <div className="flex items-center gap-3 text-slate-400 py-12 justify-center">
            <div className="w-5 h-5 border-2 border-slate-300 border-t-blue-500 rounded-full animate-spin" />
            Loading configurations…
          </div>
        ) : (
          <div className="space-y-5">
            {providers.map(p => (
              <ProviderCard
                key={p}
                provider={p}
                configs={(data?.providers?.[p] || []).map(c => ({ ...c, provider: p }))}
                onAdd={setModal}
                onTest={handleTest}
                onDelete={handleDelete}
                testing={testing}
              />
            ))}
          </div>
        )}

        {/* Setup guide */}
        <div className="mt-8 rounded-xl border border-slate-200 bg-white">
          <div className="px-5 py-4 border-b border-slate-100">
            <h3 className="font-semibold text-slate-700 text-sm">Quick Setup Guide</h3>
          </div>
          <div className="px-5 py-4 grid grid-cols-1 md:grid-cols-3 gap-5 text-sm">
            <div>
              <div className="font-medium text-orange-600 mb-1.5">AWS</div>
              <ol className="text-slate-500 space-y-1 list-decimal list-inside text-xs">
                <li>Enable Cost & Usage Reports in Billing console</li>
                <li>Choose Parquet format, hourly granularity</li>
                <li>Create cross-account IAM role with s3:GetObject</li>
                <li>Paste the Role ARN and S3 bucket above</li>
              </ol>
            </div>
            <div>
              <div className="font-medium text-blue-600 mb-1.5">Azure</div>
              <ol className="text-slate-500 space-y-1 list-decimal list-inside text-xs">
                <li>Register an App in Azure Active Directory</li>
                <li>Assign Cost Management Reader to the subscription</li>
                <li>Create a client secret under Certificates & Secrets</li>
                <li>Paste Tenant ID, Client ID, Secret, and Subscription above</li>
              </ol>
            </div>
            <div>
              <div className="font-medium text-teal-600 mb-1.5">GCP</div>
              <ol className="text-slate-500 space-y-1 list-decimal list-inside text-xs">
                <li>Enable Cloud Billing Export to BigQuery</li>
                <li>Create a Service Account in IAM</li>
                <li>Grant BigQuery Data Viewer + Job User roles</li>
                <li>Download JSON key and paste it above</li>
              </ol>
            </div>
          </div>
        </div>
      </div>

      {modal && (
        <AddModal
          provider={modal}
          onClose={() => setModal(null)}
          onSaved={() => { setModal(null); load(); }}
        />
      )}
    </div>
  );
}
