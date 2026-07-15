// Screen — Settings · Cloud Credentials
// Unified AWS / Azure / GCP credential management wired to the Lumen backend:
//   GET    /api/credentials                → all configs grouped by provider
//   POST   /api/credentials/{provider}     → upsert config (JSON body)
//   POST   /api/credentials/{id}/test      → probe provider, updates test_status
//   DELETE /api/credentials/{id}           → remove config
// Each provider includes a step-by-step "Where do I find these values?" guide.
import { useState, useEffect, useCallback } from 'react';
import { Sidebar, Topbar, Tag } from '../components/Shared.jsx';
import '../styles/tokens.css';

const TENANT = 'tenant-demo';

// ── Provider definitions (fields, setup guides) ──────────────────────────────
const PROVIDERS = {
  aws: {
    label: 'Amazon Web Services',
    accent: '#e07b39',
    tagline: 'Cost & Usage Report (CUR 2.0) delivered to S3, read via cross-account IAM role.',
    summary: c => `s3://${c.s3_bucket}${c.s3_prefix ? '/' + c.s3_prefix : ''} · ${c.aws_role_arn || ''}`,
    fields: [
      { name: 'name',            label: 'Config Name',     placeholder: 'AWS CUR – Production', required: true,
        hint: 'A label to tell configurations apart.' },
      { name: 's3_bucket',       label: 'S3 Bucket',       placeholder: 'acme-cur-bucket', required: true,
        hint: 'Bucket that receives your Cost & Usage Report exports.' },
      { name: 's3_prefix',       label: 'S3 Prefix',       placeholder: 'cur/daily',
        hint: 'Report path prefix configured in Data Exports (optional).' },
      { name: 'aws_role_arn',    label: 'IAM Role ARN',    placeholder: 'arn:aws:iam::123456789012:role/FinOpsCurReadRole', required: true,
        hint: 'Cross-account role we assume to read the CUR files.' },
      { name: 'aws_external_id', label: 'External ID',     placeholder: 'finops-ext-4f9a',
        hint: 'Shared secret in the role trust policy (prevents confused-deputy).' },
      { name: 'aws_region',      label: 'AWS Region',      placeholder: 'us-east-1',
        hint: 'Region of the CUR bucket. Defaults to us-east-1.' },
    ],
    guide: [
      { t: 'Create the CUR export',
        s: 'AWS Console → Billing and Cost Management → Data Exports → Create → "Standard data export (CUR 2.0)". Choose Parquet, hourly granularity, include resource IDs. Point it at an S3 bucket (this is your S3 Bucket + S3 Prefix).' },
      { t: 'Create a read-only IAM role',
        s: 'IAM → Roles → Create role → "AWS account" → Another account. Enter the FinOps platform account ID and tick "Require external ID" — the value you enter there is the External ID field.' },
      { t: 'Attach a least-privilege policy',
        s: 'Allow only s3:GetObject and s3:ListBucket on the CUR bucket (arn:aws:s3:::<bucket> and arn:aws:s3:::<bucket>/*). No write or other permissions are needed.' },
      { t: 'Copy the Role ARN',
        s: 'Open the role → copy its ARN (arn:aws:iam::<account>:role/<name>) into the IAM Role ARN field. First CUR delivery can take up to 24h after export creation.' },
    ],
    cli: `# Verify the role and bucket from your side:
aws sts assume-role --role-arn arn:aws:iam::<acct>:role/FinOpsCurReadRole \\
  --role-session-name finops-test --external-id <external-id>
aws s3 ls s3://<bucket>/<prefix>/ --recursive | head`,
  },

  azure: {
    label: 'Microsoft Azure',
    accent: '#3b82c4',
    tagline: 'Service Principal with Cost Management Reader, polled via the Cost Management API.',
    summary: c => `Subscription ${c.subscription_id} · App ${c.client_id}`,
    fields: [
      { name: 'name',                label: 'Config Name',           placeholder: 'Azure Cost – Production', required: true,
        hint: 'A label to tell configurations apart.' },
      { name: 'azure_tenant_id',     label: 'Directory (Tenant) ID', placeholder: 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx', required: true, guid: true,
        hint: 'Your Microsoft Entra ID tenant GUID (36 chars).' },
      { name: 'subscription_id',     label: 'Subscription ID',       placeholder: 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx', required: true, guid: true,
        hint: 'The subscription whose costs we ingest (36 chars).' },
      { name: 'client_id',           label: 'Application (Client) ID', placeholder: 'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx', required: true, guid: true,
        hint: 'App ID of the registered application / Service Principal.' },
      { name: 'client_secret',       label: 'Client Secret',         placeholder: '••••••••••••', required: true, secret: true,
        hint: 'Secret VALUE (not the Secret ID). Shown only once in the portal — stored encrypted here.' },
      { name: 'management_group_id', label: 'Management Group ID',   placeholder: 'Optional — for tenant-wide billing',
        hint: 'Only needed to ingest costs across many subscriptions at once.' },
    ],
    guide: [
      { t: 'Find your Tenant ID',
        s: 'Azure Portal → Microsoft Entra ID → Overview → "Tenant ID". (CLI: az account show --query tenantId)' },
      { t: 'Register an application',
        s: 'Microsoft Entra ID → App registrations → New registration. Name it e.g. "finops-cost-reader", single tenant, no redirect URI. After creation, the Overview page shows "Application (client) ID" — that is your Client ID.' },
      { t: 'Create a client secret',
        s: 'In the app: Certificates & secrets → Client secrets → New client secret. Copy the VALUE column immediately — it is shown only once. This is your Client Secret. Set a reminder before its expiry date (max 24 months).' },
      { t: 'Find your Subscription ID',
        s: 'Portal → Subscriptions → select the subscription → copy "Subscription ID". (CLI: az account list -o table)' },
      { t: 'Grant Cost Management Reader',
        s: 'On that subscription: Access control (IAM) → Add → Add role assignment → role "Cost Management Reader" → Members → select your app by name. Without this the connection test will fail with 401/403.' },
    ],
    cli: `# One-shot setup with Azure CLI (prints appId=Client ID, password=Client Secret, tenant=Tenant ID):
az ad sp create-for-rbac --name finops-cost-reader \\
  --role "Cost Management Reader" \\
  --scopes /subscriptions/<subscription-id>`,
  },

  gcp: {
    label: 'Google Cloud',
    accent: '#2f9e8f',
    tagline: 'Billing export to BigQuery, read with a Service Account key.',
    summary: c => `Project ${c.gcp_project_id} · ${c.bigquery_dataset}.${c.bigquery_table}`,
    fields: [
      { name: 'name',                 label: 'Config Name',        placeholder: 'GCP Billing – Production', required: true,
        hint: 'A label to tell configurations apart.' },
      { name: 'gcp_project_id',       label: 'Project ID',         placeholder: 'acme-billing-admin', required: true,
        hint: 'Project that hosts the BigQuery billing export dataset.' },
      { name: 'bigquery_dataset',     label: 'BigQuery Dataset',   placeholder: 'billing_export', required: true,
        hint: 'Dataset selected when enabling billing export.' },
      { name: 'bigquery_table',       label: 'BigQuery Table',     placeholder: 'gcp_billing_export_v1_01A2B3_C4D5E6_F7G8H9', required: true,
        hint: 'Auto-created by the export; the name includes your billing account ID.' },
      { name: 'service_account_json', label: 'Service Account JSON Key', textarea: true, required: true,
        placeholder: '{ "type": "service_account", "project_id": "...", "private_key": "...", ... }',
        hint: 'Paste the full JSON key file contents. Stored encrypted, used server-side only.' },
    ],
    guide: [
      { t: 'Enable billing export to BigQuery',
        s: 'Console → Billing → Billing export → BigQuery export → enable "Standard usage cost" (and optionally "Detailed usage cost"). Pick a project + dataset (e.g. billing_export) — these are your Project ID and BigQuery Dataset. Data starts flowing from enablement; it is not backfilled.' },
      { t: 'Find the export table name',
        s: 'BigQuery → your dataset → the export creates a table named gcp_billing_export_v1_<BILLING_ACCT_ID with underscores>. Copy the exact name into BigQuery Table.' },
      { t: 'Create a service account',
        s: 'IAM & Admin → Service Accounts → Create. Name e.g. "finops-billing-reader".' },
      { t: 'Grant read-only BigQuery roles',
        s: 'Grant the service account: "BigQuery Data Viewer" (on the export dataset, or project) + "BigQuery Job User" (on the project, to run queries). Nothing else is required.' },
      { t: 'Create and download a JSON key',
        s: 'Service account → Keys → Add key → Create new key → JSON. Open the downloaded file and paste its full contents into the JSON Key field.' },
    ],
    cli: `# Equivalent gcloud setup:
gcloud iam service-accounts create finops-billing-reader --project <project-id>
gcloud projects add-iam-policy-binding <project-id> \\
  --member serviceAccount:finops-billing-reader@<project-id>.iam.gserviceaccount.com \\
  --role roles/bigquery.jobUser
bq add-iam-policy-binding --member=serviceAccount:finops-billing-reader@<project-id>.iam.gserviceaccount.com \\
  --role=roles/bigquery.dataViewer <project-id>:billing_export
gcloud iam service-accounts keys create key.json \\
  --iam-account finops-billing-reader@<project-id>.iam.gserviceaccount.com`,
  },
};

const GUID_RE = /^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$/;

// ── Small atoms ───────────────────────────────────────────────────────────────
function StatusPill({ status }) {
  const map = {
    ok:      { c: 'var(--positive, #1a9e6e)', bg: 'rgba(26,158,110,.1)',  label: 'Connected' },
    error:   { c: 'var(--negative, #d64545)', bg: 'rgba(214,69,69,.1)',   label: 'Failed' },
    pending: { c: 'var(--muted)',             bg: 'var(--hairline)',      label: 'Not tested' },
  };
  const s = map[status] || map.pending;
  return (
    <span style={{ fontSize: 11, fontWeight: 600, color: s.c, background: s.bg, padding: '2px 8px', borderRadius: 999 }}>
      {s.label}
    </span>
  );
}

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

// ── Setup guide (collapsible) ─────────────────────────────────────────────────
function SetupGuide({ provider }) {
  const [open, setOpen] = useState(false);
  const p = PROVIDERS[provider];
  return (
    <div style={{ borderTop: '1px dashed var(--hairline)', marginTop: 10, paddingTop: 8 }}>
      <button
        onClick={() => setOpen(o => !o)}
        style={{ background: 'none', border: 'none', cursor: 'pointer', color: p.accent, fontSize: 12, fontWeight: 600, padding: 0 }}
      >
        {open ? '▾' : '▸'} Where do I find these values? — {p.label} setup guide
      </button>
      {open && (
        <div style={{ marginTop: 8 }}>
          <ol style={{ margin: 0, paddingLeft: 18, display: 'flex', flexDirection: 'column', gap: 8 }}>
            {p.guide.map((g, i) => (
              <li key={i} style={{ fontSize: 12, lineHeight: 1.5 }}>
                <span style={{ fontWeight: 600 }}>{g.t}.</span>{' '}
                <span style={{ color: 'var(--muted)' }}>{g.s}</span>
              </li>
            ))}
          </ol>
          <pre style={{
            marginTop: 10, background: 'var(--ink)', color: 'var(--surface)', borderRadius: 8,
            padding: '10px 12px', fontSize: 11, lineHeight: 1.55, overflowX: 'auto', whiteSpace: 'pre',
          }}>{p.cli}</pre>
          <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 6 }}>
            Least privilege: only read access to billing data is required. Secrets are encrypted at rest and never returned by the API or written to logs.
          </div>
        </div>
      )}
    </div>
  );
}

// ── Add-config form ───────────────────────────────────────────────────────────
function AddConfigForm({ provider, onClose, onSaved }) {
  const p = PROVIDERS[provider];
  const init = {};
  p.fields.forEach(f => { init[f.name] = ''; });
  const [form, setForm] = useState(init);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [reveal, setReveal] = useState(false);

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const validate = () => {
    for (const f of p.fields) {
      const v = (form[f.name] || '').trim();
      if (f.required && !v) return `${f.label} is required.`;
      if (f.guid && v && !GUID_RE.test(v)) return `${f.label} must be a 36-character GUID (8-4-4-4-12).`;
      if (f.name === 'service_account_json' && v) {
        try { JSON.parse(v); } catch { return 'Service Account JSON Key is not valid JSON — paste the entire key file contents.'; }
      }
    }
    return '';
  };

  const save = async () => {
    const v = validate();
    if (v) { setError(v); return; }
    setSaving(true); setError('');
    try {
      const body = { tenant_id: TENANT, enabled: true };
      p.fields.forEach(f => { body[f.name] = (form[f.name] || '').trim(); });
      const r = await fetch(`/api/credentials/${provider}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!r.ok) {
        const resp = await r.json().catch(() => ({}));
        throw new Error(typeof resp.detail === 'string' ? resp.detail : `${r.status} ${r.statusText}`);
      }
      onSaved();
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  const inputStyle = {
    width: '100%', boxSizing: 'border-box', fontSize: 12, padding: '7px 10px',
    border: '1px solid var(--hairline)', borderRadius: 8, background: 'var(--surface)', color: 'var(--ink)',
    fontFamily: 'inherit',
  };

  return (
    <div style={{ borderTop: '1px solid var(--hairline)', marginTop: 10, paddingTop: 12 }}>
      {/* autoComplete off: prevent the browser autofilling saved logins into credential fields */}
      <form autoComplete="off" onSubmit={e => e.preventDefault()}>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        {p.fields.map(f => (
          <div key={f.name} style={{ gridColumn: f.textarea ? '1 / -1' : 'auto' }}>
            <label style={{ display: 'block', fontSize: 11, fontWeight: 600, marginBottom: 4 }}>
              {f.label}{f.required && <span style={{ color: 'var(--negative, #d64545)' }}> *</span>}
            </label>
            {f.textarea ? (
              <textarea
                rows={5} style={{ ...inputStyle, fontFamily: 'var(--font-num, monospace)', resize: 'vertical' }}
                placeholder={f.placeholder} value={form[f.name]} onChange={e => set(f.name, e.target.value)}
                autoComplete="off"
              />
            ) : (
              <div style={{ position: 'relative' }}>
                <input
                  type={f.secret && !reveal ? 'password' : 'text'}
                  style={inputStyle} placeholder={f.placeholder}
                  value={form[f.name]} onChange={e => set(f.name, e.target.value)}
                  autoComplete={f.secret ? 'new-password' : 'off'}
                  name={`finops_${provider}_${f.name}`}
                />
                {f.secret && (
                  <button
                    type="button"
                    onClick={() => setReveal(r => !r)}
                    style={{ position: 'absolute', right: 8, top: 6, background: 'none', border: 'none', cursor: 'pointer', fontSize: 11, color: 'var(--muted)' }}
                  >
                    {reveal ? 'hide' : 'show'}
                  </button>
                )}
              </div>
            )}
            {f.hint && <div style={{ fontSize: 10.5, color: 'var(--muted)', marginTop: 3, lineHeight: 1.4 }}>{f.hint}</div>}
          </div>
        ))}
      </div>

      {error && (
        <div style={{ marginTop: 10, fontSize: 12, color: 'var(--negative, #d64545)', background: 'rgba(214,69,69,.08)', borderRadius: 8, padding: '8px 10px' }}>
          {error}
        </div>
      )}

      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 12 }}>
        <Btn onClick={onClose}>Cancel</Btn>
        <Btn kind="primary" onClick={save} disabled={saving}>{saving ? 'Saving…' : 'Save & connect'}</Btn>
      </div>
      </form>

      <SetupGuide provider={provider} />
    </div>
  );
}

// ── Provider card ─────────────────────────────────────────────────────────────
function ProviderSection({ provider, configs, loading, onRefresh }) {
  const p = PROVIDERS[provider];
  const [adding, setAdding] = useState(false);
  const [testing, setTesting] = useState(null);
  const [notice, setNotice] = useState('');

  const test = async (id) => {
    setTesting(id); setNotice('');
    try {
      const r = await fetch(`/api/credentials/${encodeURIComponent(id)}/test`, { method: 'POST' });
      const body = await r.json().catch(() => ({}));
      if (!r.ok) setNotice(typeof body.detail === 'string' ? body.detail : 'Connection test failed.');
    } finally {
      setTesting(null);
      onRefresh();
    }
  };

  const remove = async (id) => {
    if (!window.confirm('Remove this configuration? This cannot be undone.')) return;
    await fetch(`/api/credentials/${encodeURIComponent(id)}`, { method: 'DELETE' });
    onRefresh();
  };

  return (
    <div className="card" style={{ padding: '14px 16px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
        <span style={{ width: 10, height: 10, borderRadius: 3, background: p.accent, display: 'inline-block' }} />
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 700, fontSize: 13 }}>{p.label}</div>
          <div style={{ fontSize: 11, color: 'var(--muted)' }}>{p.tagline}</div>
        </div>
        <Btn onClick={() => setAdding(a => !a)} kind={adding ? 'ghost' : 'primary'}>
          {adding ? 'Close' : '+ Add configuration'}
        </Btn>
      </div>

      {notice && (
        <div style={{ marginTop: 8, fontSize: 11, color: 'var(--negative, #d64545)' }}>{notice}</div>
      )}

      {/* Existing configs */}
      <div style={{ marginTop: 10 }}>
        {loading ? (
          <div style={{ fontSize: 12, color: 'var(--muted)', padding: '8px 0' }}>Loading…</div>
        ) : configs.length === 0 && !adding ? (
          <div style={{ fontSize: 12, color: 'var(--muted)', padding: '8px 0' }}>
            No configurations yet — add one to start ingesting {p.label} costs.
          </div>
        ) : configs.map(cfg => (
          <div key={cfg.id} style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '8px 0', borderTop: '1px solid var(--hairline)' }}>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <span style={{ fontSize: 12, fontWeight: 600 }}>{cfg.name}</span>
                <StatusPill status={cfg.test_status} />
                {!cfg.enabled && <Tag tone="neutral">disabled</Tag>}
              </div>
              <div style={{ fontSize: 11.5, color: 'var(--muted)', marginTop: 2, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {p.summary(cfg)}
              </div>
              {cfg.test_status === 'error' && cfg.test_message && (
                <div style={{ fontSize: 11, color: 'var(--negative, #d64545)', marginTop: 3, fontFamily: 'var(--font-num, monospace)' }}>
                  {cfg.test_message}
                </div>
              )}
              {cfg.last_sync_at && (
                <div style={{ fontSize: 10.5, color: 'var(--muted)', marginTop: 2 }}>
                  Last sync {new Date(cfg.last_sync_at).toLocaleString()}
                </div>
              )}
            </div>
            <Btn small onClick={() => test(cfg.id)} disabled={testing === cfg.id}>
              {testing === cfg.id ? 'Testing…' : 'Test connection'}
            </Btn>
            <Btn small kind="danger" onClick={() => remove(cfg.id)}>Remove</Btn>
          </div>
        ))}
      </div>

      {adding && (
        <AddConfigForm
          provider={provider}
          onClose={() => setAdding(false)}
          onSaved={() => { setAdding(false); onRefresh(); }}
        />
      )}
      {!adding && <SetupGuide provider={provider} />}
    </div>
  );
}

// ── Main screen ───────────────────────────────────────────────────────────────
export default function CredentialManager({ onNavigate }) {
  const [data, setData] = useState({ aws: [], azure: [], gcp: [] });
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');

  const load = useCallback(async () => {
    setLoading(true); setLoadError('');
    try {
      const r = await fetch(`/api/credentials?tenant_id=${TENANT}`);
      if (!r.ok) throw new Error(`${r.status} ${r.statusText}`);
      const d = await r.json();
      setData({
        aws:   d.providers?.aws   || [],
        azure: d.providers?.azure || [],
        gcp:   d.providers?.gcp   || [],
      });
    } catch (e) {
      setLoadError(`Could not load configurations (${e.message}). Is the backend running?`);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const total = data.aws.length + data.azure.length + data.gcp.length;
  const connected = [...data.aws, ...data.azure, ...data.gcp].filter(c => c.test_status === 'ok').length;

  return (
    <div className="lumen" style={{ height: '100vh' }}>
      <Sidebar active="settings" onNavigate={onNavigate} />
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        <Topbar crumbs={['Acme Inc.', 'Settings', 'Cloud Credentials']} />
        <div style={{ flex: 1, overflowY: 'auto', padding: '16px 18px' }}>
          <div style={{ maxWidth: 860, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 12 }}>

            <div>
              <div className="section-title" style={{ fontSize: 15 }}>Cloud provider credentials</div>
              <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 2 }}>
                Connect AWS, Azure, and GCP billing data. Credentials are encrypted at rest, used server-side only,
                and require read-only billing access.
                {total > 0 && <> · <b>{connected}/{total}</b> configurations connected</>}
              </div>
            </div>

            {loadError && (
              <div className="card" style={{ padding: '10px 14px', fontSize: 12, color: 'var(--negative, #d64545)' }}>
                {loadError}
              </div>
            )}

            {/* Data-flow explainer */}
            <div className="card" style={{ padding: '10px 14px', fontSize: 11.5, color: 'var(--muted)', lineHeight: 1.5 }}>
              <b style={{ color: 'var(--ink)' }}>How ingestion works:</b>{' '}
              AWS CUR files land in your S3 bucket and are polled on schedule · Azure costs are pulled from the
              Cost Management API · GCP costs are queried from your BigQuery billing export. Everything is
              normalized to FOCUS and appears in dashboards within one sync cycle.
            </div>

            {['aws', 'azure', 'gcp'].map(k => (
              <ProviderSection
                key={k}
                provider={k}
                configs={data[k]}
                loading={loading}
                onRefresh={load}
              />
            ))}

          </div>
        </div>
      </div>
    </div>
  );
}
