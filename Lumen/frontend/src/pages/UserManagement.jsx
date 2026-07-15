// Screen — Teams · Users & Access (RBAC)
// Admin screen backed by:
//   GET/POST  /api/users            PATCH/DELETE /api/users/{id}
//   GET       /api/users/roles      GET          /api/audit
import { useState, useEffect, useCallback } from 'react';
import { Sidebar, Topbar, Tag, Avatar } from '../components/Shared.jsx';
import '../styles/tokens.css';

const ROLE_TONES = {
  admin:           { bg: 'rgba(214,69,69,.12)',  c: 'var(--negative, #d64545)' },
  finops_engineer: { bg: 'rgba(59,130,196,.12)', c: '#3b82c4' },
  finance_manager: { bg: 'rgba(224,123,57,.12)', c: '#e07b39' },
  team_lead:       { bg: 'rgba(47,158,143,.12)', c: '#2f9e8f' },
  analyst:         { bg: 'rgba(120,100,220,.12)',c: '#7864dc' },
  viewer:          { bg: 'var(--hairline)',      c: 'var(--muted)' },
};

function RolePill({ role }) {
  const t = ROLE_TONES[role] || ROLE_TONES.viewer;
  return (
    <span style={{ fontSize: 10.5, fontWeight: 700, color: t.c, background: t.bg, padding: '2px 8px', borderRadius: 999, letterSpacing: .3 }}>
      {role.replace('_', ' ')}
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

const inputStyle = {
  width: '100%', boxSizing: 'border-box', fontSize: 12, padding: '7px 10px',
  border: '1px solid var(--hairline)', borderRadius: 8, background: 'var(--surface)', color: 'var(--ink)',
  fontFamily: 'inherit',
};

// ── Invite / create user ──────────────────────────────────────────────────────
function InviteForm({ roles, onClose, onSaved }) {
  const [form, setForm] = useState({ email: '', full_name: '', role: 'viewer', password: '' });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const save = async () => {
    if (!form.email.trim()) { setError('Email is required.'); return; }
    if (form.password.length < 8) { setError('Temporary password must be at least 8 characters.'); return; }
    setSaving(true); setError('');
    try {
      const r = await fetch('/api/users', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      });
      if (!r.ok) {
        const b = await r.json().catch(() => ({}));
        throw new Error(typeof b.detail === 'string' ? b.detail : `${r.status} ${r.statusText}`);
      }
      onSaved();
    } catch (e) { setError(e.message); }
    finally { setSaving(false); }
  };

  const selectedRole = roles.find(r => r.id === form.role);

  return (
    <div className="card" style={{ padding: '14px 16px' }}>
      <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 10 }}>Add user</div>
      <form autoComplete="off" onSubmit={e => e.preventDefault()}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          <div>
            <label style={{ display: 'block', fontSize: 11, fontWeight: 600, marginBottom: 4 }}>Email *</label>
            <input style={inputStyle} placeholder="alice@acme.com" value={form.email}
                   onChange={e => set('email', e.target.value)} autoComplete="off" name="finops_new_user_email" />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: 11, fontWeight: 600, marginBottom: 4 }}>Full name</label>
            <input style={inputStyle} placeholder="Alice Nguyen" value={form.full_name}
                   onChange={e => set('full_name', e.target.value)} autoComplete="off" />
          </div>
          <div>
            <label style={{ display: 'block', fontSize: 11, fontWeight: 600, marginBottom: 4 }}>Role *</label>
            <select style={inputStyle} value={form.role} onChange={e => set('role', e.target.value)}>
              {roles.map(r => <option key={r.id} value={r.id}>{r.id.replace('_', ' ')}</option>)}
            </select>
            {selectedRole && (
              <div style={{ fontSize: 10.5, color: 'var(--muted)', marginTop: 3, lineHeight: 1.4 }}>
                {selectedRole.description}
              </div>
            )}
          </div>
          <div>
            <label style={{ display: 'block', fontSize: 11, fontWeight: 600, marginBottom: 4 }}>Temporary password *</label>
            <input type="password" style={inputStyle} placeholder="min 8 characters" value={form.password}
                   onChange={e => set('password', e.target.value)} autoComplete="new-password" name="finops_new_user_pw" />
            <div style={{ fontSize: 10.5, color: 'var(--muted)', marginTop: 3 }}>
              Share securely; the user should change it on first login.
            </div>
          </div>
        </div>
        {error && (
          <div style={{ marginTop: 10, fontSize: 12, color: 'var(--negative, #d64545)', background: 'rgba(214,69,69,.08)', borderRadius: 8, padding: '8px 10px' }}>
            {error}
          </div>
        )}
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 12 }}>
          <Btn onClick={onClose}>Cancel</Btn>
          <Btn kind="primary" onClick={save} disabled={saving}>{saving ? 'Creating…' : 'Create user'}</Btn>
        </div>
      </form>
    </div>
  );
}

// ── User row ──────────────────────────────────────────────────────────────────
function UserRow({ user, roles, onChanged }) {
  const [editing, setEditing] = useState(false);
  const [role, setRole] = useState(user.role);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const patch = async (body) => {
    setBusy(true); setError('');
    try {
      const r = await fetch(`/api/users/${encodeURIComponent(user.id)}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      if (!r.ok) {
        const b = await r.json().catch(() => ({}));
        throw new Error(typeof b.detail === 'string' ? b.detail : `${r.status}`);
      }
      setEditing(false);
      onChanged();
    } catch (e) { setError(e.message); }
    finally { setBusy(false); }
  };

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '9px 0', borderTop: '1px solid var(--hairline)', opacity: user.is_active ? 1 : .55 }}>
      <Avatar name={user.full_name || user.email} size={26} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 12.5, fontWeight: 600 }}>{user.full_name || user.email}</span>
          <RolePill role={user.role} />
          {!user.is_active && <Tag tone="neutral">deactivated</Tag>}
        </div>
        <div style={{ fontSize: 11, color: 'var(--muted)', marginTop: 1 }}>
          {user.email}
          {user.last_login_at ? ` · last login ${new Date(user.last_login_at).toLocaleDateString()}` : ' · never logged in'}
        </div>
        {error && <div style={{ fontSize: 11, color: 'var(--negative, #d64545)', marginTop: 2 }}>{error}</div>}
      </div>

      {editing ? (
        <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
          <select style={{ ...inputStyle, width: 170 }} value={role} onChange={e => setRole(e.target.value)}>
            {roles.map(r => <option key={r.id} value={r.id}>{r.id.replace('_', ' ')}</option>)}
          </select>
          <Btn small kind="primary" disabled={busy} onClick={() => patch({ role })}>Save</Btn>
          <Btn small onClick={() => { setEditing(false); setRole(user.role); }}>Cancel</Btn>
        </div>
      ) : (
        <div style={{ display: 'flex', gap: 6 }}>
          <Btn small onClick={() => setEditing(true)}>Change role</Btn>
          {user.is_active
            ? <Btn small kind="danger" disabled={busy} onClick={() => patch({ is_active: false })}>Deactivate</Btn>
            : <Btn small disabled={busy} onClick={() => patch({ is_active: true })}>Reactivate</Btn>}
        </div>
      )}
    </div>
  );
}

// ── Audit trail ───────────────────────────────────────────────────────────────
function AuditTrail() {
  const [events, setEvents] = useState([]);
  const [open, setOpen] = useState(true);

  const load = useCallback(async () => {
    try {
      const r = await fetch('/api/audit?limit=25');
      if (r.ok) setEvents((await r.json()).events || []);
    } catch { /* ignore */ }
  }, []);
  useEffect(() => { load(); }, [load]);

  return (
    <div className="card" style={{ padding: '14px 16px' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <div style={{ fontWeight: 700, fontSize: 13, flex: 1 }}>Audit trail</div>
        <Btn small onClick={load}>Refresh</Btn>
        <Btn small onClick={() => setOpen(o => !o)}>{open ? 'Hide' : 'Show'}</Btn>
      </div>
      {open && (
        <div style={{ marginTop: 8 }}>
          {events.length === 0 ? (
            <div style={{ fontSize: 12, color: 'var(--muted)', padding: '6px 0' }}>
              No audit events yet. User and credential changes will appear here.
            </div>
          ) : events.map(e => (
            <div key={e.id} style={{ display: 'flex', gap: 10, padding: '6px 0', borderTop: '1px solid var(--hairline)', fontSize: 11.5 }}>
              <span style={{ color: 'var(--muted)', whiteSpace: 'nowrap', fontFamily: 'var(--font-num, monospace)' }}>
                {new Date(e.created_at).toLocaleString()}
              </span>
              <span style={{ fontWeight: 600, whiteSpace: 'nowrap' }}>{e.action}</span>
              <span style={{ color: 'var(--muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {e.actor} · {e.resource_type}
                {e.payload?.email ? ` · ${e.payload.email}` : ''}
                {e.payload?.status && e.payload.status !== 'success' ? ` · ${e.payload.status}` : ''}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

// ── Main screen ───────────────────────────────────────────────────────────────
export default function UserManagement({ onNavigate }) {
  const [users, setUsers] = useState([]);
  const [roles, setRoles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [inviting, setInviting] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true); setError('');
    try {
      const [ur, rr] = await Promise.all([fetch('/api/users'), fetch('/api/users/roles')]);
      if (ur.status === 403) throw new Error('You need the admin role to manage users.');
      if (!ur.ok) throw new Error(`${ur.status} ${ur.statusText}`);
      setUsers((await ur.json()).users || []);
      if (rr.ok) setRoles((await rr.json()).roles || []);
    } catch (e) { setError(e.message); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const active = users.filter(u => u.is_active).length;

  return (
    <div className="lumen" style={{ height: '100vh' }}>
      <Sidebar active="teams" onNavigate={onNavigate} />
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        <Topbar crumbs={['Acme Inc.', 'Teams', 'Users & Access']} />
        <div style={{ flex: 1, overflowY: 'auto', padding: '16px 18px' }}>
          <div style={{ maxWidth: 860, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: 12 }}>

            <div style={{ display: 'flex', alignItems: 'flex-end', gap: 10 }}>
              <div style={{ flex: 1 }}>
                <div className="section-title" style={{ fontSize: 15 }}>Users & access</div>
                <div style={{ fontSize: 12, color: 'var(--muted)', marginTop: 2 }}>
                  Role-based access control. {users.length > 0 && <>{active} active user{active === 1 ? '' : 's'} · roles are enforced by the API on every request.</>}
                </div>
              </div>
              <Btn kind="primary" onClick={() => setInviting(v => !v)}>{inviting ? 'Close' : '+ Add user'}</Btn>
            </div>

            {error && (
              <div className="card" style={{ padding: '10px 14px', fontSize: 12, color: 'var(--negative, #d64545)' }}>{error}</div>
            )}

            {inviting && (
              <InviteForm roles={roles} onClose={() => setInviting(false)}
                          onSaved={() => { setInviting(false); load(); }} />
            )}

            {/* Role legend */}
            <div className="card" style={{ padding: '10px 14px' }}>
              <div style={{ fontSize: 11, fontWeight: 700, marginBottom: 6, letterSpacing: .3, color: 'var(--muted)' }}>ROLE PERMISSIONS</div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px 18px' }}>
                {roles.map(r => (
                  <div key={r.id} style={{ display: 'flex', gap: 8, alignItems: 'baseline', fontSize: 11.5 }}>
                    <RolePill role={r.id} />
                    <span style={{ color: 'var(--muted)', lineHeight: 1.4 }}>{r.description.split('—')[1] || r.description}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* User list */}
            <div className="card" style={{ padding: '6px 16px 10px' }}>
              {loading ? (
                <div style={{ fontSize: 12, color: 'var(--muted)', padding: '10px 0' }}>Loading users…</div>
              ) : users.length === 0 && !error ? (
                <div style={{ fontSize: 12, color: 'var(--muted)', padding: '10px 0' }}>
                  No users yet — add the first one above.
                </div>
              ) : users.map(u => (
                <UserRow key={u.id} user={u} roles={roles} onChanged={load} />
              ))}
            </div>

            <AuditTrail />

          </div>
        </div>
      </div>
    </div>
  );
}
