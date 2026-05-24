// Screen 3 — Anomaly Detection
// Left: horizon-strip list of services + heat strip on each row.
// Right rail: detail of selected anomaly — what/why/who/now.
import {
  Sidebar, Topbar, FilterBar, KPI, Ico, Tag, ProviderBadge, fmtUSD, pct,
} from '../components/Shared.jsx';
import '../styles/tokens.css';

export default function AnomaliesScreen({ onNavigate }) {
  const services = [
    { svc: 'EKS',         p: 'AWS',   acct: 'prod-aws-1',     anomalies: [{ d: 10, sev: 3, amt: 18400 }, { d: 11, sev: 3, amt: 12200 }], baseline: 4800, spike: 6620, status: 'open' },
    { svc: 'BigQuery',    p: 'GCP',   acct: 'data-analytics', anomalies: [{ d: 9, sev: 2, amt: 11800 }, { d: 13, sev: 2, amt: 6200 }], baseline: 4600, spike: 5900, status: 'investigating' },
    { svc: 'S3',          p: 'AWS',   acct: 'prod-aws-1',     anomalies: [{ d: 6, sev: 1, amt: 4200 }], baseline: 3100, spike: 3640, status: 'open' },
    { svc: 'EC2',         p: 'AWS',   acct: 'prod-aws-1',     anomalies: [], baseline: 10400, spike: null, status: 'ok' },
    { svc: 'Azure SQL',   p: 'Azure', acct: 'enterprise-az',  anomalies: [{ d: 12, sev: 2, amt: 8800 }], baseline: 2900, spike: 4180, status: 'snoozed' },
    { svc: 'Cloud Run',   p: 'GCP',   acct: 'prod-gcp-svc',   anomalies: [], baseline: 1200, spike: null, status: 'ok' },
    { svc: 'GKE',         p: 'GCP',   acct: 'data-analytics', anomalies: [{ d: 8, sev: 1, amt: 3400 }, { d: 10, sev: 1, amt: 2800 }], baseline: 1600, spike: 2100, status: 'open' },
    { svc: 'Lambda',      p: 'AWS',   acct: 'prod-aws-1',     anomalies: [{ d: 13, sev: 1, amt: 2200 }], baseline: 2000, spike: 2440, status: 'resolved' },
    { svc: 'RDS',         p: 'AWS',   acct: 'prod-aws-1',     anomalies: [], baseline: 1100, spike: null, status: 'ok' },
    { svc: 'CloudFront',  p: 'AWS',   acct: 'prod-aws-1',     anomalies: [{ d: 11, sev: 2, amt: 5800 }], baseline: 700, spike: 1280, status: 'open' },
  ];

  return (
    <div className="lumen">
      <Sidebar active="anomalies" onNavigate={onNavigate} />
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        <Topbar crumbs={['Acme Inc.', 'Anomalies', 'EKS · prod-us-east-1']} asMonth="May 2026" />
        <FilterBar
          range="May 1 – 14, 2026"
          granularity="Daily"
          filters={[
            { label: 'Severity', value: '≥ medium' },
            { label: 'Status', value: 'open · investigating' },
            { label: 'Detector', value: 'STL + ML ensemble' },
          ]}
        />

        <div style={{ flex: 1, display: 'flex', minWidth: 0, overflow: 'hidden' }}>
          {/* MAIN */}
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, padding: '14px 14px 0', gap: 12, overflow: 'hidden' }}>
            {/* KPI strip */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10 }}>
              <KPI label="Open anomalies"   value="9"       sub="3 critical · 4 medium · 2 low" delta={50.0} kind="invert" accent="var(--negative)" spark={[3,4,5,6,7,8,9]} />
              <KPI label="Impact (7d)"      value="$74.2k"  sub="≈ 4.0% of weekly spend"        delta={26.4} kind="invert" accent="var(--d4)" spark={[20,25,32,40,52,62,74]} />
              <KPI label="Mean time to ack" value="4h 12m"  sub="target ≤ 2h"                   delta={-18.0} accent="var(--positive)" spark={[6,5.8,5.5,5,4.6,4.3,4.2]} />
              <KPI label="False positive"   value="6.4%"    sub="↓ vs 11.2% last quarter"       delta={-42.8} accent="var(--positive)" spark={[12,11,10,9,8,7,6.4]} />
            </div>

            {/* Anomalies horizon table */}
            <div className="card" style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 14px', borderBottom: '1px solid var(--hairline)' }}>
                <div className="section-title"><Ico name="alert" size={12} /> Anomaly heatstrip · last 14 days</div>
                <div style={{ flex: 1 }} />
                <div style={{ display: 'flex', gap: 4, fontSize: 11, color: 'var(--muted)' }}>
                  <span>Severity</span>
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: 3 }}><i style={{ width: 8, height: 8, background: 'oklch(0.85 0.04 25)', display: 'inline-block' }} /> low</span>
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: 3 }}><i style={{ width: 8, height: 8, background: 'oklch(0.72 0.13 26)', display: 'inline-block' }} /> med</span>
                  <span style={{ display: 'inline-flex', alignItems: 'center', gap: 3 }}><i style={{ width: 8, height: 8, background: 'oklch(0.55 0.2 26)', display: 'inline-block' }} /> high</span>
                </div>
                <button className="btn ghost" style={{ height: 22, fontSize: 11 }}>Routing rules</button>
              </div>
              <div style={{ flex: 1, overflow: 'auto', position: 'relative' }}>
                {/* date header */}
                <div style={{ position: 'sticky', top: 0, background: 'var(--panel)', borderBottom: '1px solid var(--hairline)', zIndex: 1, display: 'grid', gridTemplateColumns: '220px 1fr 110px 88px 90px 24px', alignItems: 'center', padding: '5px 14px', fontSize: 10, fontFamily: 'var(--font-num)', color: 'var(--muted)', letterSpacing: '0.06em', textTransform: 'uppercase' }}>
                  <span>Service</span>
                  <DateHeader />
                  <span style={{ textAlign: 'right' }}>Baseline</span>
                  <span style={{ textAlign: 'right' }}>Peak Δ</span>
                  <span style={{ textAlign: 'right' }}>Status</span>
                  <span></span>
                </div>
                {services.map((s, i) => (
                  <HorizonRow key={s.svc} {...s} selected={i === 0} />
                ))}
              </div>
            </div>
          </div>

          {/* RIGHT — detail rail */}
          <aside style={{
            width: 360, flex: '0 0 360px',
            background: 'var(--panel)',
            borderLeft: '1px solid var(--border)',
            padding: 14,
            display: 'flex', flexDirection: 'column', gap: 12,
            overflow: 'auto',
            fontSize: 12,
          }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <Tag tone="negative">⚠ critical</Tag>
                <span style={{ fontSize: 11, color: 'var(--muted)' }}>anomaly-21048 · opened 4h ago</span>
              </div>
              <h3 style={{ margin: '6px 0 2px', fontSize: 18, color: 'var(--ink)', fontWeight: 500, letterSpacing: '-0.01em', lineHeight: 1.25 }}>
                EKS <span className="mono" style={{ fontSize: 13, color: 'var(--muted)' }}>prod-us-east-1</span> spiked 38% Tue–Wed
              </h3>
              <div style={{ fontSize: 11.5, color: 'var(--muted)' }}>Detected May 11, 02:14 UTC · ongoing</div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
              <DetailStat label="Impact" value="$18.4k" tone="negative" />
              <DetailStat label="Forecast" value="$31k" sub="if unmitigated" tone="warning" />
              <DetailStat label="Z-score" value="3.4σ" />
              <DetailStat label="Detector" value="STL + ML" />
            </div>

            {/* Anomaly timeline */}
            <div className="card" style={{ padding: 10 }}>
              <div className="eyebrow" style={{ marginBottom: 6 }}>14d cost · baseline band</div>
              <AnomalySparkBig />
              <div style={{ fontSize: 10.5, color: 'var(--muted)', display: 'flex', justifyContent: 'space-between' }}>
                <span>May 1</span><span>May 7</span><span>May 14</span>
              </div>
            </div>

            <div>
              <div className="eyebrow" style={{ marginBottom: 4 }}>Suspected cause</div>
              <div style={{ padding: 10, background: 'var(--surface)', border: '1px solid var(--border)', borderLeft: '3px solid var(--accent)', borderRadius: 6, fontSize: 12, lineHeight: 1.5 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--accent)', marginBottom: 4 }}>
                  <Ico name="sparkles" size={12} />
                  <span style={{ fontWeight: 500, fontSize: 11 }}>Lumen analysis · 92% conf.</span>
                </div>
                <span style={{ color: 'var(--ink)' }}>
                  Idle <span className="mono">gp3</span> volumes (84 detached) persisted after the
                  {' '}<span className="mono">checkout-svc</span> rollback at <span className="mono">02:08</span>.
                  Node group <span className="mono">eks-prod-spot-3</span> auto-scaled to 24 nodes and stayed there.
                </span>
              </div>
            </div>

            <div>
              <div className="eyebrow" style={{ marginBottom: 4 }}>Related events</div>
              <div style={{ display: 'grid', gap: 4 }}>
                <Event ts="02:08" txt="Deploy rollback · checkout-svc v4.12 → v4.11" type="deploy" />
                <Event ts="02:14" txt="Anomaly detected · EKS cost +38%" type="alert" />
                <Event ts="02:21" txt="Auto-scale event · spot-3 → 24 nodes" type="infra" />
                <Event ts="08:40" txt="Slack notify · #finops-alerts" type="notify" />
                <Event ts="09:12" txt="Acknowledged by Maya Park" type="ack" />
              </div>
            </div>

            <div>
              <div className="eyebrow" style={{ marginBottom: 4 }}>Suggested actions</div>
              <Action title="Reclaim 84 idle gp3 volumes" amt="$4.2k/mo" cta="Apply" tone="positive" />
              <Action title="Scale down spot-3 to 14 nodes" amt="$2.8k/mo" cta="Plan" tone="info" />
              <Action title="Add policy · auto-detach >24h idle volumes" amt="prevent" cta="Add" tone="info" />
            </div>

            <div style={{ display: 'flex', gap: 6, paddingTop: 4 }}>
              <button className="btn primary" style={{ flex: 1, justifyContent: 'center' }}>Resolve</button>
              <button className="btn" style={{ flex: 1, justifyContent: 'center' }}>Assign…</button>
              <button className="btn ghost" style={{ padding: '0 8px' }}>Snooze</button>
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}

function DateHeader() {
  return (
    <div style={{ display: 'flex', gap: 1, padding: '0 8px', height: 18, alignItems: 'center' }}>
      {Array.from({ length: 14 }, (_, i) => (
        <div key={i} style={{ flex: 1, textAlign: 'center', fontSize: 9.5, color: i % 2 === 0 ? 'var(--ink)' : 'var(--muted)' }}>{i % 2 === 0 ? String(i + 1).padStart(2, '0') : ''}</div>
      ))}
    </div>
  );
}

function HorizonRow({ svc, p, acct, anomalies, baseline, spike, status, selected }) {
  const sevColor = (sev) => sev >= 3 ? 'oklch(0.55 0.2 26)' : sev >= 2 ? 'oklch(0.72 0.16 26)' : 'oklch(0.85 0.07 25)';
  const statusTag = {
    open:          { tone: 'negative', label: 'open' },
    investigating: { tone: 'warning',  label: 'investigating' },
    snoozed:       { tone: 'info',     label: 'snoozed' },
    resolved:      { tone: 'positive', label: 'resolved' },
    ok:            { tone: 'neutral',  label: '— ok —' },
  }[status];

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: '220px 1fr 110px 88px 90px 24px',
      alignItems: 'center', padding: '8px 14px',
      borderBottom: '1px solid var(--hairline)',
      background: selected ? 'var(--surface)' : 'transparent',
      borderLeft: selected ? '2px solid var(--ink)' : '2px solid transparent',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <ProviderBadge p={p} />
        <div>
          <div style={{ fontSize: 12, color: 'var(--ink)', fontWeight: selected ? 500 : 400 }}>{svc}</div>
          <div className="mono" style={{ fontSize: 10, color: 'var(--muted)' }}>{acct}</div>
        </div>
      </div>
      {/* heat strip */}
      <div style={{ display: 'flex', gap: 1, height: 26, padding: '0 8px' }}>
        {Array.from({ length: 14 }, (_, i) => {
          const a = anomalies.find(x => x.d === i + 1);
          const bg = a ? sevColor(a.sev) : 'var(--hairline)';
          const op = a ? 1 : 0.6;
          return (
            <div key={i} style={{ flex: 1, height: '100%', background: bg, opacity: op, borderRadius: 1, position: 'relative' }} title={a ? `Day ${a.d}` : ''}>
              {a && a.sev >= 2 && <div style={{ position: 'absolute', inset: 0, borderRadius: 1, boxShadow: 'inset 0 0 0 1px rgba(0,0,0,0.18)' }} />}
            </div>
          );
        })}
      </div>
      <div className="num" style={{ textAlign: 'right', fontSize: 11, color: 'var(--muted)' }}>${(baseline / 1000).toFixed(1)}k/d</div>
      <div className="num" style={{ textAlign: 'right', fontSize: 11.5, color: spike ? 'var(--negative)' : 'var(--muted)', fontWeight: spike ? 500 : 400 }}>
        {spike ? `+$${((spike - baseline) / 1000).toFixed(1)}k` : '—'}
      </div>
      <div style={{ textAlign: 'right' }}><Tag tone={statusTag.tone}>{statusTag.label}</Tag></div>
      <div><Ico name="chevR" size={11} /></div>
    </div>
  );
}

function DetailStat({ label, value, sub, tone }) {
  return (
    <div className="card-flush" style={{ padding: '8px 10px', background: 'var(--surface)' }}>
      <div className="eyebrow" style={{ fontSize: 9.5 }}>{label}</div>
      <div className="num" style={{ fontSize: 16, color: `var(--${tone || 'ink'})`, fontWeight: 500, marginTop: 2 }}>{value}</div>
      {sub && <div style={{ fontSize: 10, color: 'var(--muted)' }}>{sub}</div>}
    </div>
  );
}

function AnomalySparkBig() {
  const W = 320, H = 88, padL = 0, padR = 0, padT = 4, padB = 16;
  const w = W - padL - padR, h = H - padT - padB;
  const data = [4.6, 4.8, 4.5, 4.7, 4.6, 4.9, 4.7, 5.0, 5.2, 6.4, 6.6, 5.4, 5.0, 4.9];
  const upperBand = data.map(() => 5.6);
  const lowerBand = data.map(() => 3.8);
  const max = 7.2, min = 3.0;
  const x = (i) => padL + (i / (data.length - 1)) * w;
  const y = (v) => padT + h - ((v - min) / (max - min)) * h;
  const line = data.map((v, i) => `${i === 0 ? 'M' : 'L'}${x(i)},${y(v)}`).join(' ');
  const bandPath = upperBand.map((v, i) => `${i === 0 ? 'M' : 'L'}${x(i)},${y(v)}`).join(' ')
    + lowerBand.slice().reverse().map((v, i) => `L${x(lowerBand.length - 1 - i)},${y(v)}`).join(' ') + ' Z';
  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H}>
      <path d={bandPath} fill="var(--accent)" opacity="0.10" />
      <rect x={x(9) - 8} y={padT} width={x(11) - x(9) + 16} height={h} fill="var(--negative)" opacity="0.08" rx="4" />
      <path d={line} fill="none" stroke="var(--ink)" strokeWidth="1.6" vectorEffect="non-scaling-stroke" />
      {[9, 10].map(i => <circle key={i} cx={x(i)} cy={y(data[i])} r="3" fill="var(--negative)" />)}
      <text x={x(9.5)} y={padT + 9} textAnchor="middle" fontSize="9.5" fill="var(--negative)" fontFamily="var(--font-num)" fontWeight="500">+38% · $18.4k</text>
    </svg>
  );
}

function Event({ ts, txt, type }) {
  const colors = { deploy: 'var(--info)', alert: 'var(--negative)', infra: 'var(--warning)', notify: 'var(--muted)', ack: 'var(--positive)' };
  return (
    <div style={{ display: 'flex', gap: 8, alignItems: 'baseline', fontSize: 11.5, padding: '3px 0', borderBottom: '1px dashed var(--hairline)' }}>
      <span className="mono" style={{ fontSize: 10, color: 'var(--muted)', width: 42 }}>{ts}</span>
      <span style={{ width: 6, height: 6, borderRadius: 999, background: colors[type], marginTop: 6 }} />
      <span style={{ flex: 1, color: 'var(--text)' }}>{txt}</span>
    </div>
  );
}

function Action({ title, amt, cta, tone }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 10px', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 6, marginBottom: 4 }}>
      <div style={{ flex: 1, fontSize: 12, color: 'var(--ink)' }}>{title}</div>
      <Tag tone={tone}>{amt}</Tag>
      <button className="btn" style={{ height: 22, padding: '0 8px', fontSize: 11 }}>{cta}</button>
    </div>
  );
}
