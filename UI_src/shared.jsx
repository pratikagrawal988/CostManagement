/* global React */
/* eslint-disable no-unused-vars */

// ─────────────────────────────────────────────────────────────────
// Lumen — shared chrome + primitives used by every screen.
// Sidebar / Topbar / FilterBar / KPI / Spark / charts / tables.
// ─────────────────────────────────────────────────────────────────

const fmtUSD = (n, opts = {}) => {
  const { compact = false, sign = false } = opts;
  const v = Math.abs(n);
  let out;
  if (compact) {
    if (v >= 1e9) out = (n / 1e9).toFixed(2) + 'B';
    else if (v >= 1e6) out = (n / 1e6).toFixed(2) + 'M';
    else if (v >= 1e3) out = (n / 1e3).toFixed(1) + 'k';
    else out = n.toFixed(0);
  } else {
    out = n.toLocaleString('en-US', { maximumFractionDigits: 0 });
  }
  if (sign && n > 0) out = '+' + out;
  return '$' + out;
};
const pct = (n, d = 1) => (n > 0 ? '+' : '') + n.toFixed(d) + '%';

// Icons — single-stroke, 14px viewBox, currentColor
const Icon = ({ d, size = 14, stroke = 1.5, fill }) => (
  <svg width={size} height={size} viewBox="0 0 14 14" fill="none" stroke="currentColor" strokeWidth={stroke} strokeLinecap="round" strokeLinejoin="round">
    {fill ? <path d={d} fill="currentColor" stroke="none" /> : <path d={d} />}
  </svg>
);
const I = {
  spark:    "M1 8 L3 6 L5 9 L7 4 L9 7 L11 3 L13 6",
  search:   "M6 1.5 A4.5 4.5 0 1 0 6 10.5 A4.5 4.5 0 1 0 6 1.5 M9.5 9.5 L12.5 12.5",
  filter:   "M1.5 2.5 H12.5 L8.5 7 V12 L5.5 11 V7 Z",
  bell:     "M3.5 9 V6.5 A3.5 3.5 0 0 1 10.5 6.5 V9 L11.5 10 H2.5 Z M5.5 11 Q7 12.5 8.5 11",
  chev:     "M4.5 5.5 L7 8 L9.5 5.5",
  chevR:    "M5.5 4.5 L8 7 L5.5 9.5",
  plus:     "M7 2.5 V11.5 M2.5 7 H11.5",
  dot:      "M7 7 L7 7",
  arrowU:   "M7 11 V3 M4 6 L7 3 L10 6",
  arrowD:   "M7 3 V11 M4 8 L7 11 L10 8",
  arrowR:   "M2.5 7 H11.5 M8.5 4 L11.5 7 L8.5 10",
  spark2:   "M1 9 L4 6 L7 8 L10 3 L13 5",
  home:     "M2 7 L7 2 L12 7 V12 H2 Z",
  explore:  "M2 12 L5 6 L8 10 L11 4 L13 7",
  alert:    "M7 1.5 L13 12 H1 Z M7 6 V8.5 M7 10 V10.5",
  budget:   "M2.5 4 H11.5 V11 H2.5 Z M2.5 6.5 H11.5 M4.5 9 H6.5",
  bulb:     "M7 1.5 A3.5 3.5 0 0 1 9.5 7.5 V9 H4.5 V7.5 A3.5 3.5 0 0 1 7 1.5 M5.5 10.5 H8.5 M6 12 H8",
  tree:     "M2 2 H6 V6 H2 Z M8 2 H12 V6 H8 Z M2 8 H6 V12 H2 Z M8 8 H12 V12 H8 Z",
  tag:      "M1.5 1.5 H7 L12.5 7 L7 12.5 L1.5 7 Z M4 4 H4.5",
  team:     "M5 5 A2 2 0 1 0 5 1 A2 2 0 1 0 5 5 M1 11 Q1 8 5 8 Q9 8 9 11 M10 5 A1.5 1.5 0 1 0 10 2 M13 9 Q13 7 10 7",
  cal:      "M2.5 3 H11.5 V11.5 H2.5 Z M2.5 5.5 H11.5 M4.5 1.5 V3.5 M9.5 1.5 V3.5",
  cog:      "M7 4.5 A2.5 2.5 0 1 0 7 9.5 A2.5 2.5 0 1 0 7 4.5 M7 1 V2.5 M7 11.5 V13 M1 7 H2.5 M11.5 7 H13",
  cmd:      "M3 3 H11 V11 H3 Z M5 1 V13 M9 1 V13 M1 5 H13 M1 9 H13",
  sparkles: "M7 2 L8 5.5 L11.5 7 L8 8.5 L7 12 L6 8.5 L2.5 7 L6 5.5 Z M11 1.5 L11.5 3 L13 3.5 L11.5 4 L11 5.5 L10.5 4 L9 3.5 L10.5 3 Z",
  check:    "M3 7.5 L6 10 L11 4",
  x:        "M3.5 3.5 L10.5 10.5 M10.5 3.5 L3.5 10.5",
  flame:    "M7 12.5 Q3 11 3 7.5 Q3 4.5 5.5 2.5 Q5 5 7 6 Q9 4 8.5 1.5 Q11 4 11 7.5 Q11 11 7 12.5",
  globe:    "M7 1 A6 6 0 1 0 7 13 A6 6 0 1 0 7 1 M1 7 H13 M7 1 Q3.5 7 7 13 M7 1 Q10.5 7 7 13",
  download: "M7 2 V9 M4 6 L7 9 L10 6 M2.5 12 H11.5",
  link:     "M6 8 L8 6 M5.5 9.5 L4 11 A2 2 0 0 1 1 8 L3 6.5 M8.5 4.5 L10 3 A2 2 0 0 1 13 6 L11 7.5",
  pin:      "M7 1.5 V8 M4.5 8 H9.5 L9 11 H5 Z M7 11 V13",
  share:    "M3 7 L11 3 M3 7 L11 11 M3 7 A1.5 1.5 0 1 0 3 7 M11 3 A1.5 1.5 0 1 0 11 3 M11 11 A1.5 1.5 0 1 0 11 11",
};
const Ico = ({ name, size, stroke, fill }) => <Icon d={I[name]} size={size} stroke={stroke} fill={fill} />;

// ─────────────────────────────────────────────────────────────────
// SIDEBAR
// ─────────────────────────────────────────────────────────────────
function Sidebar({ active = 'overview' }) {
  const nav = [
    { id: 'overview', label: 'Overview', icon: 'home' },
    { id: 'explorer', label: 'Cost Explorer', icon: 'explore' },
    { id: 'anomalies', label: 'Anomalies', icon: 'alert', badge: 3 },
    { id: 'budgets', label: 'Budgets & Forecast', icon: 'budget' },
    { id: 'recommendations', label: 'Recommendations', icon: 'bulb', badge: 28 },
    { id: 'ai', label: 'AI cost', icon: 'sparkles', badge: 'NEW' },
    { id: 'drilldown', label: 'Resources', icon: 'tree' },
  ];
  const lower = [
    { id: 'tags', label: 'Tag policy', icon: 'tag' },
    { id: 'teams', label: 'Teams', icon: 'team' },
    { id: 'reports', label: 'Reports', icon: 'cal' },
    { id: 'settings', label: 'Settings', icon: 'cog' },
  ];
  return (
    <aside style={{
      width: 188, flex: '0 0 188px',
      background: 'var(--panel)',
      borderRight: '1px solid var(--border)',
      display: 'flex', flexDirection: 'column',
      padding: '14px 10px',
      gap: 6,
      fontSize: 12.5,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 6px 12px' }}>
        <div style={{
          width: 22, height: 22, borderRadius: 6,
          background: 'var(--ink)', color: 'var(--bg)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontFamily: 'var(--font-display)', fontStyle: 'italic', fontSize: 16, lineHeight: 1,
        }}>L</div>
        <div style={{ fontWeight: 600, color: 'var(--ink)', letterSpacing: '-0.01em' }}>lumen</div>
        <div style={{ marginLeft: 'auto', fontSize: 10, color: 'var(--muted)', fontFamily: 'var(--font-num)' }}>v3.2</div>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '6px 8px', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8, marginBottom: 8 }}>
        <div style={{ width: 16, height: 16, borderRadius: 4, background: 'oklch(0.7 0.13 280)', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 10, fontWeight: 600 }}>A</div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 11.5, fontWeight: 500, color: 'var(--ink)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>Acme Inc.</div>
          <div style={{ fontSize: 10, color: 'var(--muted)' }}>org · 4 accounts</div>
        </div>
        <Ico name="chev" size={12} />
      </div>

      <div className="eyebrow" style={{ padding: '6px 8px 2px' }}>Workspace</div>
      {nav.map(n => (
        <NavItem key={n.id} {...n} active={active === n.id} />
      ))}

      <div className="eyebrow" style={{ padding: '14px 8px 2px' }}>Governance</div>
      {lower.map(n => <NavItem key={n.id} {...n} />)}

      <div style={{ flex: 1 }} />

      <div style={{ padding: '10px 8px', borderTop: '1px solid var(--hairline)', display: 'flex', flexDirection: 'column', gap: 4 }}>
        <div style={{ fontSize: 10, color: 'var(--muted)', display: 'flex', justifyContent: 'space-between' }}>
          <span>Data freshness</span>
          <span className="mono">2m ago</span>
        </div>
        <div style={{ height: 4, background: 'var(--hairline)', borderRadius: 999, overflow: 'hidden' }}>
          <div style={{ width: '76%', height: '100%', background: 'var(--positive)' }} />
        </div>
        <div style={{ fontSize: 10, color: 'var(--muted)', display: 'flex', justifyContent: 'space-between' }}>
          <span>AWS · GCP · Azure</span>
          <span className="mono" style={{ color: 'var(--positive)' }}>● synced</span>
        </div>
      </div>
    </aside>
  );
}

function NavItem({ label, icon, active, badge }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 8,
      padding: '5px 8px', borderRadius: 6,
      color: active ? 'var(--ink)' : 'var(--text)',
      background: active ? 'var(--surface)' : 'transparent',
      border: active ? '1px solid var(--border)' : '1px solid transparent',
      fontWeight: active ? 500 : 400,
      cursor: 'pointer',
      position: 'relative',
    }}>
      <span style={{ color: active ? 'var(--ink)' : 'var(--muted)', display: 'flex' }}>
        <Ico name={icon} size={13} />
      </span>
      <span style={{ flex: 1 }}>{label}</span>
      {badge != null && (
        <span style={{
          fontFamily: 'var(--font-num)', fontSize: 10,
          background: active ? 'var(--ink)' : 'var(--hairline)',
          color: active ? 'var(--bg)' : 'var(--muted)',
          padding: '1px 5px', borderRadius: 999, minWidth: 16, textAlign: 'center',
        }}>{badge}</span>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
// TOPBAR — global breadcrumb, search, AI ask, account
// ─────────────────────────────────────────────────────────────────
function Topbar({ crumbs = ['Overview'], showAsk = true, asMonth = 'May 2026' }) {
  return (
    <div style={{
      height: 44, flex: '0 0 44px',
      borderBottom: '1px solid var(--border)',
      display: 'flex', alignItems: 'center', gap: 12,
      padding: '0 14px',
      background: 'var(--bg)',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--muted)', fontSize: 12 }}>
        {crumbs.map((c, i) => (
          <React.Fragment key={i}>
            {i > 0 && <Ico name="chevR" size={10} />}
            <span style={{ color: i === crumbs.length - 1 ? 'var(--ink)' : 'var(--muted)', fontWeight: i === crumbs.length - 1 ? 500 : 400 }}>{c}</span>
          </React.Fragment>
        ))}
      </div>

      <div style={{ marginLeft: 8, padding: '2px 6px', background: 'var(--panel)', border: '1px solid var(--border)', borderRadius: 4, fontSize: 10.5, color: 'var(--muted)', fontFamily: 'var(--font-num)' }}>
        FY26 · {asMonth}
      </div>

      <div style={{ flex: 1 }} />

      {showAsk && (
        <div style={{
          display: 'flex', alignItems: 'center', gap: 8,
          height: 28, padding: '0 10px',
          width: 360,
          background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8,
          color: 'var(--muted)', fontSize: 12,
        }}>
          <span style={{ color: 'var(--accent)' }}><Ico name="sparkles" size={13} /></span>
          <span style={{ color: 'var(--ink)' }}>Ask Lumen</span>
          <span style={{ color: 'var(--subtle)' }}>· "why did EKS spike last Tue?"</span>
          <span style={{ flex: 1 }} />
          <span className="kbd">⌘</span><span className="kbd">K</span>
        </div>
      )}

      <button className="btn ghost" title="Notifications"><Ico name="bell" size={13} /></button>
      <button className="btn ghost"><Ico name="share" size={13} /> Share</button>
      <button className="btn"><Ico name="download" size={12} /> Export</button>

      <div style={{ width: 26, height: 26, borderRadius: 999, background: 'oklch(0.85 0.06 80)', color: 'oklch(0.3 0.05 60)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 11, fontWeight: 600 }}>JK</div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
// FILTER BAR — the persistent slicer above content
// ─────────────────────────────────────────────────────────────────
function FilterBar({
  range = 'May 1 – 14',
  granularity = 'Daily',
  providers = ['AWS', 'GCP', 'Azure'],
  active = ['AWS', 'GCP', 'Azure'],
  filters = [
    { label: 'Service', value: 'all 47' },
    { label: 'Environment', value: 'production' },
    { label: 'Project', value: 'all 12' },
    { label: 'Tag · team', value: 'all' },
  ],
  compare = 'vs last month',
}) {
  return (
    <div style={{
      flex: '0 0 auto',
      borderBottom: '1px solid var(--border)',
      background: 'var(--panel)',
      padding: '8px 14px',
      display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap',
      fontSize: 12,
    }}>
      {/* Date range */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
        <span style={{ color: 'var(--muted)', display: 'flex' }}><Ico name="cal" size={12} /></span>
        <div style={{ display: 'flex', alignItems: 'center', height: 24, padding: '0 8px', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 6, gap: 6 }}>
          <span style={{ color: 'var(--ink)', fontWeight: 500 }}>{range}</span>
          <Ico name="chev" size={10} />
        </div>
        <div style={{ display: 'flex', height: 24, background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 6, overflow: 'hidden' }}>
          {['Hourly', 'Daily', 'Weekly', 'Monthly'].map(g => (
            <div key={g} style={{
              padding: '0 8px', display: 'flex', alignItems: 'center',
              background: g === granularity ? 'var(--ink)' : 'transparent',
              color: g === granularity ? 'var(--bg)' : 'var(--muted)',
              fontSize: 11, fontWeight: g === granularity ? 500 : 400,
              borderRight: '1px solid var(--border)',
            }}>{g}</div>
          ))}
        </div>
      </div>

      <div className="vline" style={{ height: 16 }} />

      {/* Providers */}
      <div style={{ display: 'flex', gap: 4 }}>
        {providers.map(p => {
          const on = active.includes(p);
          const cls = p.toLowerCase();
          return (
            <div key={p} style={{
              display: 'inline-flex', alignItems: 'center', gap: 5,
              height: 24, padding: '0 8px 0 6px',
              border: '1px solid var(--border)',
              borderRadius: 999,
              background: on ? 'var(--surface)' : 'var(--panel)',
              opacity: on ? 1 : 0.55,
              fontSize: 11.5,
            }}>
              <span className={`pbadge ${cls}`} style={{ width: 14, height: 14, fontSize: 8 }}>{p[0]}</span>
              {p}
            </div>
          );
        })}
      </div>

      <div className="vline" style={{ height: 16 }} />

      {filters.map((f, i) => (
        <div key={i} style={{ display: 'inline-flex', alignItems: 'center', height: 24, padding: '0 8px', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 6, gap: 6 }}>
          <span style={{ color: 'var(--muted)' }}>{f.label}</span>
          <span style={{ color: 'var(--ink)', fontWeight: 500 }}>{f.value}</span>
          <Ico name="chev" size={10} />
        </div>
      ))}

      <button className="chip ghost"><Ico name="plus" size={10} /> Add filter</button>

      <div style={{ flex: 1 }} />

      <div style={{ display: 'inline-flex', alignItems: 'center', height: 24, padding: '0 8px', background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 6, gap: 6 }}>
        <span style={{ color: 'var(--muted)' }}>compare</span>
        <span style={{ color: 'var(--ink)', fontWeight: 500 }}>{compare}</span>
        <Ico name="chev" size={10} />
      </div>
      <span className="chip" style={{ color: 'var(--muted)', height: 24, fontSize: 11 }}>USD</span>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
// KPI CARD — big number, delta, sparkline, "vs" comparison
// ─────────────────────────────────────────────────────────────────
function KPI({ label, value, delta, deltaLabel = 'vs last mo', sub, spark, kind = 'neutral', accent = 'var(--accent)', big = false }) {
  const trendCls = delta == null ? 'flat' : delta > 0 ? (kind === 'invert' ? 'dn' : 'up') : (kind === 'invert' ? 'up' : 'dn');
  const trendSign = delta == null ? '·' : (delta > 0 ? '▲' : '▼');
  return (
    <div className="card" style={{ padding: 14, display: 'flex', flexDirection: 'column', gap: 6, flex: 1, minWidth: 0, position: 'relative' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <span className="legend-dot" style={{ background: accent }} />
        <span className="eyebrow">{label}</span>
      </div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
        <div className="num" style={{ fontSize: big ? 30 : 24, color: 'var(--ink)', fontWeight: 500, letterSpacing: '-0.025em', lineHeight: 1 }}>
          {value}
        </div>
        {delta != null && (
          <span className={`trend ${trendCls}`}>{trendSign} {Math.abs(delta).toFixed(1)}%</span>
        )}
      </div>
      <div style={{ fontSize: 11, color: 'var(--muted)', display: 'flex', justifyContent: 'space-between', gap: 6 }}>
        <span>{sub}</span>
        <span>{deltaLabel}</span>
      </div>
      {spark && <Spark data={spark} color={accent} height={28} />}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
// SPARK — minimal sparkline w/ area + dot
// ─────────────────────────────────────────────────────────────────
function Spark({ data, color = 'var(--accent)', height = 28, showDot = true, baseline }) {
  if (!data || data.length < 2) return null;
  const w = 100;
  const h = height;
  const max = Math.max(...data);
  const min = Math.min(...data);
  const span = max - min || 1;
  const points = data.map((v, i) => [i * (w / (data.length - 1)), h - ((v - min) / span) * (h - 4) - 2]);
  const path = points.map((p, i) => (i === 0 ? `M${p[0]},${p[1]}` : `L${p[0]},${p[1]}`)).join(' ');
  const area = `${path} L${w},${h} L0,${h} Z`;
  const last = points[points.length - 1];
  return (
    <svg viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none" width="100%" height={h} style={{ overflow: 'visible' }}>
      <path d={area} fill={color} opacity="0.10" />
      <path d={path} fill="none" stroke={color} strokeWidth="1.4" vectorEffect="non-scaling-stroke" />
      {baseline != null && <line x1="0" y1={h - ((baseline - min) / span) * (h - 4) - 2} x2={w} y2={h - ((baseline - min) / span) * (h - 4) - 2} stroke="var(--muted)" strokeDasharray="2 2" strokeWidth="0.5" vectorEffect="non-scaling-stroke" />}
      {showDot && <circle cx={last[0]} cy={last[1]} r="2" fill={color} />}
    </svg>
  );
}

// ─────────────────────────────────────────────────────────────────
// AREA / STACKED AREA chart
// ─────────────────────────────────────────────────────────────────
function StackedArea({ series, width = 700, height = 220, colors, mode = 'area', xLabels, yTicks = 4, highlightIdx }) {
  // series: [{ name, color, data: [n,…] }] same length
  if (!series || !series.length) return null;
  const N = series[0].data.length;
  const stacked = [];
  for (let i = 0; i < N; i++) {
    let acc = 0;
    const col = [];
    series.forEach((s) => { col.push([acc, acc + s.data[i]]); acc += s.data[i]; });
    stacked.push(col);
  }
  const totals = Array.from({ length: N }, (_, i) => series.reduce((a, s) => a + s.data[i], 0));
  const max = Math.max(...totals) * 1.05;
  const padL = 38, padR = 12, padT = 10, padB = 22;
  const W = width - padL - padR, H = height - padT - padB;
  const x = (i) => padL + (i / (N - 1)) * W;
  const y = (v) => padT + H - (v / max) * H;

  const layerPaths = series.map((s, si) => {
    const top = stacked.map((c, i) => `${i === 0 ? 'M' : 'L'}${x(i)},${y(c[si][1])}`).join(' ');
    const bot = stacked.map((c, i) => `L${x(N - 1 - i)},${y(stacked[N - 1 - i][si][0])}`).join(' ').replace(/^L/, '');
    return `${top} L${x(N - 1)},${y(stacked[N - 1][si][0])} ${bot} Z`;
  });
  const lines = mode === 'line' ? series.map((s) =>
    s.data.map((v, i) => `${i === 0 ? 'M' : 'L'}${x(i)},${y(v)}`).join(' ')
  ) : [];

  const ticks = Array.from({ length: yTicks + 1 }, (_, i) => (max * i) / yTicks);

  return (
    <svg viewBox={`0 0 ${width} ${height}`} width="100%" height={height} style={{ overflow: 'visible' }}>
      {ticks.map((t, i) => (
        <g key={i}>
          <line x1={padL} x2={width - padR} y1={y(t)} y2={y(t)} stroke="var(--hairline)" strokeWidth="1" vectorEffect="non-scaling-stroke" />
          <text x={padL - 6} y={y(t) + 3} textAnchor="end" fontFamily="var(--font-num)" fontSize="9" fill="var(--muted)">{Math.round(t / 1000)}k</text>
        </g>
      ))}
      {mode !== 'line' && series.map((s, si) => (
        <path key={si} d={layerPaths[si]} fill={s.color} opacity={mode === 'bar' ? 0 : 0.85} />
      ))}
      {mode === 'bar' && series.map((s, si) => (
        stacked.map((c, i) => {
          const w = (W / N) * 0.7;
          return <rect key={si + '-' + i} x={x(i) - w / 2} y={y(c[si][1])} width={w} height={Math.max(0, y(c[si][0]) - y(c[si][1]))} fill={s.color} opacity="0.95" />;
        })
      ))}
      {mode === 'line' && series.map((s, si) => (
        <path key={si} d={lines[si]} fill="none" stroke={s.color} strokeWidth="1.6" vectorEffect="non-scaling-stroke" />
      ))}
      {/* axis labels */}
      {xLabels && xLabels.map((l, i) => (
        <text key={i} x={x(i)} y={height - 6} textAnchor="middle" fontFamily="var(--font-num)" fontSize="9.5" fill="var(--muted)">{l}</text>
      ))}
      {highlightIdx != null && (
        <line x1={x(highlightIdx)} x2={x(highlightIdx)} y1={padT} y2={padT + H} stroke="var(--ink)" strokeWidth="1" strokeDasharray="3 3" vectorEffect="non-scaling-stroke" />
      )}
    </svg>
  );
}

// ─────────────────────────────────────────────────────────────────
// Helper: generate plausible daily cost data
// ─────────────────────────────────────────────────────────────────
function genCostSeries(base, days, drift = 0.02, noise = 0.08, weeklyDip = 0.18, seed = 1) {
  let s = seed;
  const rnd = () => { s = (s * 9301 + 49297) % 233280; return s / 233280; };
  const out = [];
  let v = base;
  for (let i = 0; i < days; i++) {
    v *= 1 + (drift / days);
    const dow = i % 7;
    const w = (dow === 5 || dow === 6) ? 1 - weeklyDip : 1;
    const n = 1 + (rnd() - 0.5) * noise;
    out.push(Math.round(v * w * n));
  }
  return out;
}

// ─────────────────────────────────────────────────────────────────
// Misc atoms
// ─────────────────────────────────────────────────────────────────
function Tag({ children, tone = 'neutral' }) {
  const map = {
    neutral: { bg: 'var(--hairline)', fg: 'var(--muted)' },
    positive: { bg: 'var(--positive-soft)', fg: 'var(--positive)' },
    negative: { bg: 'var(--negative-soft)', fg: 'var(--negative)' },
    warning: { bg: 'var(--warning-soft)', fg: 'var(--warning)' },
    info: { bg: 'var(--info-soft)', fg: 'var(--info)' },
  };
  const c = map[tone] || map.neutral;
  return <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, padding: '1px 6px', borderRadius: 4, background: c.bg, color: c.fg, fontFamily: 'var(--font-num)', fontSize: 10.5, fontWeight: 500, whiteSpace: 'nowrap' }}>{children}</span>;
}

function Avatar({ name, size = 18, color }) {
  const initials = name.split(' ').map(s => s[0]).slice(0, 2).join('');
  return <div style={{ width: size, height: size, borderRadius: 999, background: color || 'oklch(0.85 0.05 80)', color: 'oklch(0.3 0.05 60)', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', fontSize: size * 0.45, fontWeight: 600 }}>{initials}</div>;
}

function ProviderBadge({ p }) {
  return <span className={`pbadge ${p.toLowerCase()}`}>{p[0]}</span>;
}

// Tiny dashed/dotted bar — for budget rails
function ProgressBar({ value, max, color = 'var(--accent)', height = 8, marker, label }) {
  const w = Math.min(1, value / max);
  return (
    <div style={{ position: 'relative', height, background: 'var(--hairline)', borderRadius: 999 }}>
      <div style={{ position: 'absolute', inset: 0, width: `${w * 100}%`, background: color, borderRadius: 'inherit' }} />
      {marker != null && (
        <div style={{ position: 'absolute', top: -2, bottom: -2, left: `${(marker / max) * 100}%`, width: 2, background: 'var(--ink)' }} />
      )}
      {label && <div style={{ position: 'absolute', right: 4, top: -14, fontFamily: 'var(--font-num)', fontSize: 10, color: 'var(--muted)' }}>{label}</div>}
    </div>
  );
}

Object.assign(window, {
  fmtUSD, pct, Icon, Ico, I,
  Sidebar, Topbar, FilterBar,
  KPI, Spark, StackedArea,
  genCostSeries, Tag, Avatar, ProviderBadge, ProgressBar,
});
