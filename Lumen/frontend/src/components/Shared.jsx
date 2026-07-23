import React from 'react';
import { APP_NAME, APP_INITIAL } from '../config.js';

// ─────────────────────────────────────────────────────────────────
// Lumen — shared chrome + primitives used by every screen.
// Sidebar / Topbar / FilterBar / KPI / Spark / StackedArea / atoms
// ─────────────────────────────────────────────────────────────────

export const fmtUSD = (n, opts = {}) => {
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

export const pct = (n, d = 1) => (n > 0 ? '+' : '') + n.toFixed(d) + '%';

// Icons — single-stroke, 14×14 viewBox, currentColor
const Icon = ({ d, size = 14, stroke = 1.5, fill }) => (
  <svg width={size} height={size} viewBox="0 0 14 14" fill="none"
    stroke="currentColor" strokeWidth={stroke} strokeLinecap="round" strokeLinejoin="round">
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
  sparkles: "M7 2 L8 5.5 L11.5 7 L8 8.5 L7 12 L6 8.5 L2.5 7 L6 5.5 Z M11 1.5 L11.5 3 L13 3.5 L11.5 4 L11 5.5 L10.5 4 L9 3.5 L10.5 3 Z",
  check:    "M3 7.5 L6 10 L11 4",
  x:        "M3.5 3.5 L10.5 10.5 M10.5 3.5 L3.5 10.5",
  download: "M7 2 V9 M4 6 L7 9 L10 6 M2.5 12 H11.5",
  link:     "M6 8 L8 6 M5.5 9.5 L4 11 A2 2 0 0 1 1 8 L3 6.5 M8.5 4.5 L10 3 A2 2 0 0 1 13 6 L11 7.5",
  pin:      "M7 1.5 V8 M4.5 8 H9.5 L9 11 H5 Z M7 11 V13",
  share:    "M3 7 L11 3 M3 7 L11 11",
  cube:     "M7 1 L12 4 V10 L7 13 L2 10 V4 Z M7 1 V13 M2 4 L7 7 L12 4",
};

export const Ico = ({ name, size = 14, stroke = 1.5, fill }) => (
  <Icon d={I[name] || ''} size={size} stroke={stroke} fill={fill} />
);

// ─────────────────────────────────────────────────────────────────
// SIDEBAR
// ─────────────────────────────────────────────────────────────────
export function Sidebar({ active = 'overview', onNavigate }) {
  const nav = [
    { id: 'overview',        label: 'Overview',           icon: 'home' },
    { id: 'explorer',        label: 'Cost Explorer',      icon: 'explore' },
    { id: 'anomalies',       label: 'Anomalies',          icon: 'alert',  badge: 3 },
    { id: 'budgets',         label: 'Budgets & Forecast', icon: 'budget' },
    { id: 'recommendations', label: 'Recommendations',    icon: 'bulb',   badge: 28 },
    { id: 'ai',              label: 'AI Cost',            icon: 'sparkles', badge: 'NEW' },
    { id: 'databricks',      label: 'Databricks',         icon: 'cube',   badge: 'NEW' },
    { id: 'resources',       label: 'Resources',          icon: 'tree' },
  ];
  const lower = [
    { id: 'tags',     label: 'Tag policy', icon: 'tag' },
    { id: 'teams',    label: 'Teams',      icon: 'team' },
    { id: 'reports',  label: 'Reports',    icon: 'cal' },
    { id: 'settings', label: 'Settings',   icon: 'cog' },
  ];

  const navigate = onNavigate || (() => {});

  return (
    <aside style={{
      width: 188, flex: '0 0 188px',
      background: 'var(--panel)',
      borderRight: '1px solid var(--border)',
      display: 'flex', flexDirection: 'column',
      padding: '14px 10px',
      gap: 6,
      fontSize: 12.5,
      overflow: 'hidden',
    }}>
      {/* Logo */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 6px 12px' }}>
        <div style={{
          width: 22, height: 22, borderRadius: 6,
          background: 'var(--ink)', color: 'var(--bg)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontFamily: 'var(--font-display)', fontStyle: 'italic', fontSize: 15, lineHeight: 1,
          flexShrink: 0,
        }}>{APP_INITIAL}</div>
        <div style={{ fontWeight: 600, color: 'var(--ink)', letterSpacing: '-0.01em', fontSize: 13 }}>{APP_NAME}</div>
      </div>

      {/* Org switcher */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 6,
        padding: '6px 8px',
        background: 'var(--surface)',
        border: '1px solid var(--border)',
        borderRadius: 8,
        marginBottom: 8,
        cursor: 'pointer',
      }}>
        <div style={{
          width: 16, height: 16, borderRadius: 4,
          background: 'oklch(0.7 0.13 280)', color: 'white',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 10, fontWeight: 600, flexShrink: 0,
        }}>A</div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 11.5, fontWeight: 500, color: 'var(--ink)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>Acme Inc.</div>
          <div style={{ fontSize: 10, color: 'var(--muted)' }}>org · 4 accounts</div>
        </div>
        <Ico name="chev" size={12} />
      </div>

      <div className="eyebrow" style={{ padding: '6px 8px 2px' }}>Workspace</div>
      {nav.map(n => (
        <NavItem key={n.id} {...n} active={active === n.id} onClick={() => navigate(n.id)} />
      ))}

      <div className="eyebrow" style={{ padding: '14px 8px 2px' }}>Governance</div>
      {lower.map(n => <NavItem key={n.id} {...n} onClick={() => navigate(n.id)} />)}

      <div style={{ flex: 1 }} />

      {/* Data freshness */}
      <div style={{ padding: '10px 8px', borderTop: '1px solid var(--hairline)', display: 'flex', flexDirection: 'column', gap: 4 }}>
        <div style={{ fontSize: 10, color: 'var(--muted)', display: 'flex', justifyContent: 'space-between' }}>
          <span>Data freshness</span>
          <span className="mono">live</span>
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

function NavItem({ label, icon, active, badge, onClick }) {
  return (
    <div onClick={onClick} style={{
      display: 'flex', alignItems: 'center', gap: 8,
      padding: '5px 8px', borderRadius: 6,
      color: active ? 'var(--ink)' : 'var(--text)',
      background: active ? 'var(--surface)' : 'transparent',
      border: active ? '1px solid var(--border)' : '1px solid transparent',
      fontWeight: active ? 500 : 400,
      cursor: 'pointer',
    }}>
      <span style={{ color: active ? 'var(--ink)' : 'var(--muted)', display: 'flex', flexShrink: 0 }}>
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
// TOPBAR
// ─────────────────────────────────────────────────────────────────
export function Topbar({ crumbs = ['Overview'], asMonth, onExport, onShare }) {
  const now = new Date();
  const monthStr = asMonth || now.toLocaleString('en-US', { month: 'short', year: 'numeric' });

  return (
    <div style={{
      height: 44, flex: '0 0 44px',
      borderBottom: '1px solid var(--border)',
      display: 'flex', alignItems: 'center', gap: 12,
      padding: '0 14px',
      background: 'var(--bg)',
      flexShrink: 0,
    }}>
      {/* Breadcrumbs */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, color: 'var(--muted)', fontSize: 12 }}>
        {crumbs.map((c, i) => (
          <React.Fragment key={i}>
            {i > 0 && <Ico name="chevR" size={10} />}
            <span style={{
              color: i === crumbs.length - 1 ? 'var(--ink)' : 'var(--muted)',
              fontWeight: i === crumbs.length - 1 ? 500 : 400,
            }}>{c}</span>
          </React.Fragment>
        ))}
      </div>

      <div style={{
        padding: '2px 6px',
        background: 'var(--panel)', border: '1px solid var(--border)', borderRadius: 4,
        fontSize: 10.5, color: 'var(--muted)', fontFamily: 'var(--font-num)',
      }}>
        FY26 · {monthStr}
      </div>

      <div style={{ flex: 1 }} />

      {/* Ask AI bar */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8,
        height: 28, padding: '0 10px',
        width: 340,
        background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 8,
        color: 'var(--muted)', fontSize: 12,
      }}>
        <span style={{ color: 'var(--accent)', display: 'flex' }}><Ico name="sparkles" size={13} /></span>
        <span style={{ color: 'var(--ink)' }}>Ask {APP_NAME}</span>
        <span style={{ color: 'var(--subtle)', overflow: 'hidden', whiteSpace: 'nowrap', textOverflow: 'ellipsis', flex: 1 }}>· "why did EKS spike last Tue?"</span>
        <span className="kbd">⌘</span><span className="kbd">K</span>
      </div>

      <button className="btn ghost" title="Notifications"><Ico name="bell" size={13} /></button>
      <button className="btn ghost" onClick={onShare}><Ico name="share" size={13} /> Share</button>
      <button className="btn" onClick={onExport}><Ico name="download" size={12} /> Export</button>

      <div style={{
        width: 26, height: 26, borderRadius: 999,
        background: 'oklch(0.85 0.06 80)', color: 'oklch(0.3 0.05 60)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 11, fontWeight: 600, flexShrink: 0,
      }}>PA</div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
// FILTER BAR
// ─────────────────────────────────────────────────────────────────
export function FilterBar({
  range = 'Last 30 days',
  granularity = 'Daily',
  onGranularityChange,
  providers = ['AWS', 'GCP', 'Azure'],
  activeProviders = ['AWS', 'GCP', 'Azure'],
  onProviderToggle,
  filters = [],
  compare = 'vs last month',
  onRangeClick,
}) {
  return (
    <div style={{
      flex: '0 0 auto',
      borderBottom: '1px solid var(--border)',
      background: 'var(--panel)',
      padding: '8px 14px',
      display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap',
      fontSize: 12,
      flexShrink: 0,
    }}>
      {/* Date range */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
        <span style={{ color: 'var(--muted)', display: 'flex' }}><Ico name="cal" size={12} /></span>
        <div
          onClick={onRangeClick}
          style={{
            display: 'flex', alignItems: 'center', height: 24, padding: '0 8px',
            background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 6, gap: 6, cursor: 'pointer',
          }}>
          <span style={{ color: 'var(--ink)', fontWeight: 500 }}>{range}</span>
          <Ico name="chev" size={10} />
        </div>
        {/* Granularity tabs */}
        <div style={{ display: 'flex', height: 24, background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 6, overflow: 'hidden' }}>
          {['Hourly', 'Daily', 'Weekly', 'Monthly'].map(g => (
            <div
              key={g}
              onClick={() => onGranularityChange?.(g)}
              style={{
                padding: '0 8px', display: 'flex', alignItems: 'center',
                background: g === granularity ? 'var(--ink)' : 'transparent',
                color: g === granularity ? 'var(--bg)' : 'var(--muted)',
                fontSize: 11, fontWeight: g === granularity ? 500 : 400,
                borderRight: '1px solid var(--border)',
                cursor: 'pointer',
              }}>{g}</div>
          ))}
        </div>
      </div>

      <div className="vline" style={{ height: 16 }} />

      {/* Provider toggles */}
      <div style={{ display: 'flex', gap: 4 }}>
        {providers.map(p => {
          const on = activeProviders.includes(p);
          const cls = p.toLowerCase();
          return (
            <div
              key={p}
              onClick={() => onProviderToggle?.(p)}
              style={{
                display: 'inline-flex', alignItems: 'center', gap: 5,
                height: 24, padding: '0 8px 0 6px',
                border: '1px solid var(--border)',
                borderRadius: 999,
                background: on ? 'var(--surface)' : 'var(--panel)',
                opacity: on ? 1 : 0.55,
                fontSize: 11.5, cursor: 'pointer',
              }}>
              <span className={`pbadge ${cls}`} style={{ width: 14, height: 14, fontSize: 8 }}>{p[0]}</span>
              {p}
            </div>
          );
        })}
      </div>

      <div className="vline" style={{ height: 16 }} />

      {filters.map((f, i) => (
        <div key={i} style={{
          display: 'inline-flex', alignItems: 'center', height: 24, padding: '0 8px',
          background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 6, gap: 6,
        }}>
          <span style={{ color: 'var(--muted)' }}>{f.label}</span>
          <span style={{ color: 'var(--ink)', fontWeight: 500 }}>{f.value}</span>
          <Ico name="chev" size={10} />
        </div>
      ))}

      <button className="chip ghost"><Ico name="plus" size={10} /> Add filter</button>

      <div style={{ flex: 1 }} />

      <div style={{
        display: 'inline-flex', alignItems: 'center', height: 24, padding: '0 8px',
        background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 6, gap: 6,
      }}>
        <span style={{ color: 'var(--muted)' }}>compare</span>
        <span style={{ color: 'var(--ink)', fontWeight: 500 }}>{compare}</span>
        <Ico name="chev" size={10} />
      </div>
      <span className="chip" style={{ color: 'var(--muted)', height: 24, fontSize: 11 }}>USD</span>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
// KPI CARD
// ─────────────────────────────────────────────────────────────────
export function KPI({ label, value, delta, deltaLabel = 'vs last mo', sub, spark, kind = 'neutral', accent = 'var(--accent)', big = false }) {
  const trendCls = delta == null ? 'flat' : delta > 0 ? (kind === 'invert' ? 'dn' : 'up') : (kind === 'invert' ? 'up' : 'dn');
  const trendSign = delta == null ? '·' : (delta > 0 ? '▲' : '▼');
  return (
    <div className="card" style={{ padding: 14, display: 'flex', flexDirection: 'column', gap: 6, flex: 1, minWidth: 0, position: 'relative' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <span className="legend-dot" style={{ background: accent }} />
        <span className="eyebrow">{label}</span>
      </div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
        <div className="num" style={{ fontSize: big ? 28 : 22, color: 'var(--ink)', fontWeight: 500, letterSpacing: '-0.025em', lineHeight: 1 }}>
          {value}
        </div>
        {delta != null && (
          <span className={`trend ${trendCls}`}>{trendSign} {Math.abs(delta).toFixed(1)}%</span>
        )}
      </div>
      {sub && <div style={{ fontSize: 11, color: 'var(--muted)' }}>{sub}</div>}
      {deltaLabel && <div style={{ fontSize: 10.5, color: 'var(--subtle)' }}>{deltaLabel}</div>}
      {spark && <Spark data={spark} color={accent} height={28} />}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
// SPARK — minimal sparkline
// ─────────────────────────────────────────────────────────────────
export function Spark({ data, color = 'var(--accent)', height = 28, showDot = true }) {
  if (!data || data.length < 2) return null;
  const w = 100, h = height;
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
      {showDot && <circle cx={last[0]} cy={last[1]} r="2" fill={color} />}
    </svg>
  );
}

// ─────────────────────────────────────────────────────────────────
// STACKED AREA chart
// ─────────────────────────────────────────────────────────────────
export function StackedArea({ series, width = 700, height = 220, colors, mode = 'area', xLabels, yTicks = 4, highlightIdx, yFormatter }) {
  if (!series || !series.length) return null;
  const N = series[0].data.length;
  if (N < 2) return null;

  const stacked = [];
  for (let i = 0; i < N; i++) {
    let acc = 0;
    const col = [];
    series.forEach(s => { col.push([acc, acc + s.data[i]]); acc += s.data[i]; });
    stacked.push(col);
  }
  const totals = Array.from({ length: N }, (_, i) => series.reduce((a, s) => a + s.data[i], 0));
  const max = Math.max(...totals) * 1.05 || 1;
  const padL = 42, padR = 12, padT = 10, padB = 22;
  const W = width - padL - padR, H = height - padT - padB;
  const x = i => padL + (i / (N - 1)) * W;
  const y = v => padT + H - (v / max) * H;

  const layerPaths = series.map((s, si) => {
    const top = stacked.map((c, i) => `${i === 0 ? 'M' : 'L'}${x(i).toFixed(1)},${y(c[si][1]).toFixed(1)}`).join(' ');
    const bot = [...stacked].reverse().map((c, i) => {
      const origIdx = N - 1 - i;
      return `L${x(origIdx).toFixed(1)},${y(c[si][0]).toFixed(1)}`;
    }).join(' ');
    return `${top} ${bot} Z`;
  });

  const fmtY = yFormatter || (v => v >= 1000 ? `${(v / 1000).toFixed(0)}k` : String(Math.round(v)));
  const ticks = Array.from({ length: yTicks + 1 }, (_, i) => (max * i) / yTicks);

  return (
    <svg viewBox={`0 0 ${width} ${height}`} width="100%" height={height} style={{ overflow: 'visible' }}>
      {ticks.map((t, i) => (
        <g key={i}>
          <line x1={padL} x2={width - padR} y1={y(t)} y2={y(t)} stroke="var(--hairline)" strokeWidth="1" vectorEffect="non-scaling-stroke" />
          <text x={padL - 6} y={y(t) + 3} textAnchor="end" fontFamily="var(--font-num)" fontSize="9" fill="var(--muted)">{fmtY(t)}</text>
        </g>
      ))}
      {mode !== 'line' && series.map((s, si) => (
        <path key={si} d={layerPaths[si]} fill={s.color} opacity={mode === 'bar' ? 0 : 0.82} />
      ))}
      {mode === 'bar' && series.map((s, si) => (
        stacked.map((c, i) => {
          const bw = (W / N) * 0.65;
          return <rect key={`${si}-${i}`} x={x(i) - bw / 2} y={y(c[si][1])} width={bw} height={Math.max(0, y(c[si][0]) - y(c[si][1]))} fill={s.color} opacity="0.9" />;
        })
      ))}
      {mode === 'line' && series.map((s, si) => {
        const line = s.data.map((v, i) => `${i === 0 ? 'M' : 'L'}${x(i)},${y(v)}`).join(' ');
        return <path key={si} d={line} fill="none" stroke={s.color} strokeWidth="1.6" vectorEffect="non-scaling-stroke" />;
      })}
      {xLabels && xLabels.map((l, i) => l ? (
        <text key={i} x={x(i)} y={height - 4} textAnchor="middle" fontFamily="var(--font-num)" fontSize="9.5" fill="var(--muted)">{l}</text>
      ) : null)}
      {highlightIdx != null && (
        <line x1={x(highlightIdx)} x2={x(highlightIdx)} y1={padT} y2={padT + H} stroke="var(--ink)" strokeWidth="1" strokeDasharray="3 3" vectorEffect="non-scaling-stroke" />
      )}
    </svg>
  );
}

// ─────────────────────────────────────────────────────────────────
// MISC ATOMS
// ─────────────────────────────────────────────────────────────────
export function Tag({ children, tone = 'neutral' }) {
  const map = {
    neutral:  { bg: 'var(--hairline)',       fg: 'var(--muted)' },
    positive: { bg: 'var(--positive-soft)',  fg: 'var(--positive)' },
    negative: { bg: 'var(--negative-soft)',  fg: 'var(--negative)' },
    warning:  { bg: 'var(--warning-soft)',   fg: 'var(--warning)' },
    info:     { bg: 'var(--info-soft)',      fg: 'var(--info)' },
  };
  const c = map[tone] || map.neutral;
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 4,
      padding: '1px 6px', borderRadius: 4,
      background: c.bg, color: c.fg,
      fontFamily: 'var(--font-num)', fontSize: 10.5, fontWeight: 500, whiteSpace: 'nowrap',
    }}>{children}</span>
  );
}

export function ProviderBadge({ p }) {
  const cls = (p || '').toLowerCase();
  return <span className={`pbadge ${cls}`}>{(p || '?')[0]}</span>;
}

export function Avatar({ name, size = 18, color }) {
  const initials = (name || '?').split(' ').map(s => s[0]).slice(0, 2).join('');
  return <div style={{ width: size, height: size, borderRadius: 999, background: color || 'oklch(0.85 0.05 80)', color: 'oklch(0.3 0.05 60)', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', fontSize: size * 0.45, fontWeight: 600, flex: '0 0 auto' }}>{initials}</div>;
}

export function ProgressBar({ value, max, color = 'var(--accent)', height = 8, marker, label }) {
  const w = Math.min(1, (value || 0) / (max || 1));
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

// Utility: generate deterministic mock series (fallback when API loading)
export function genCostSeries(base, days, drift = 0.02, noise = 0.08, weeklyDip = 0.18, seed = 1) {
  let s = seed;
  const rnd = () => { s = (s * 9301 + 49297) % 233280; return s / 233280; };
  const out = [];
  let v = base;
  for (let i = 0; i < days; i++) {
    v *= 1 + (drift / days);
    const dow = i % 7;
    const w = (dow === 5 || dow === 6) ? 1 - weeklyDip : 1;
    out.push(Math.round(v * w * (1 + (rnd() - 0.5) * noise)));
  }
  return out;
}
