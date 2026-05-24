// Screen 1 — Executive Overview
// Persona: CFO. Big hero metrics, spend curve, forecast, burn, then
// a "cost flow" sankey + AI commentary + top-movers leaderboard.
import { useState } from 'react';
import {
  Sidebar, Topbar, FilterBar, KPI, Spark, StackedArea, Ico, Tag,
  ProviderBadge, Avatar, fmtUSD, pct, genCostSeries,
} from '../components/Shared.jsx';
import '../styles/tokens.css';

const ALL_PROVIDERS = ['AWS', 'GCP', 'Azure'];

export default function ExecutiveOverview({ onNavigate }) {
  const [granularity, setGranularity]       = useState('Daily');
  const [activeProviders, setActiveProviders] = useState(['AWS', 'GCP', 'Azure']);
  const [chartMode, setChartMode]           = useState('area');
  const [viewMode, setViewMode]             = useState('Overview');

  function toggleProvider(p) {
    setActiveProviders(prev =>
      prev.includes(p)
        ? prev.length > 1 ? prev.filter(x => x !== p) : prev  // keep at least 1
        : [...prev, p]
    );
  }

  const days = 14;
  const aws = genCostSeries(48000, days, 0.04, 0.10, 0.22, 2);
  const gcp = genCostSeries(28000, days, 0.05, 0.09, 0.18, 7);
  const az  = genCostSeries(16000, days, 0.03, 0.11, 0.15, 5);
  const labels = Array.from({ length: days }, (_, i) => String(i + 1).padStart(2, '0'));

  const mtd = aws.reduce((a, b) => a + b, 0) + gcp.reduce((a, b) => a + b, 0) + az.reduce((a, b) => a + b, 0);
  const forecast = Math.round(mtd * (31 / days) * 0.985);

  return (
    <div className="lumen">
      <Sidebar active="overview" onNavigate={onNavigate} />
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        <Topbar crumbs={['Acme Inc.', 'Overview']} asMonth="May 2026" />
        <FilterBar
          range="May 1 – 14, 2026"
          granularity={granularity}
          onGranularityChange={setGranularity}
          activeProviders={activeProviders}
          onProviderToggle={toggleProvider}
          filters={[
            { label: 'Service', value: 'all 47' },
            { label: 'Environment', value: 'production' },
            { label: 'Tag · team', value: 'all' },
          ]}
        />

        <div style={{ flex: 1, overflow: 'hidden', padding: '14px 14px 0', display: 'flex', flexDirection: 'column', gap: 12 }}>
          {/* Hero header */}
          <div style={{ display: 'flex', alignItems: 'flex-end', gap: 18, marginBottom: -2 }}>
            <div>
              <div className="eyebrow">Month-to-date · 14 of 31 days</div>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 12, marginTop: 2 }}>
                <h1 className="display" style={{ margin: 0, fontSize: 38, color: 'var(--ink)', lineHeight: 1 }}>
                  May, twenty&#8209;six
                </h1>
                <span style={{ fontSize: 12, color: 'var(--muted)' }}>updated 2m ago · auto-refresh on</span>
              </div>
            </div>
            <div style={{ flex: 1 }} />
            <ViewToggle active={viewMode} onChange={setViewMode} />
          </div>

          {/* KPI strip */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 10 }}>
            <KPI label="MTD spend"        value={fmtUSD(mtd, { compact: true })} sub="$94.2k yesterday" delta={6.4} kind="invert" spark={aws.map((v,i)=>v+gcp[i]+az[i])} big />
            <KPI label="Forecast EOM"     value={fmtUSD(forecast, { compact: true })} sub="conf. 92% · ±$48k" delta={4.1} kind="invert" accent="var(--d3)" spark={[1.7,1.74,1.79,1.83,1.88,1.92,1.96]} />
            <KPI label="vs Apr 2026"      value="+5.2%" sub="$112k more than last mo" delta={5.2} kind="invert" accent="var(--d5)" spark={[1,1.02,1.04,1.07,1.05,1.08,1.05]} />
            <KPI label="Savings captured" value="$184k" sub="68% of $271k pipeline" delta={12.0} accent="var(--positive)" spark={[0.4,0.5,0.7,0.9,1.1,1.5,1.84]} />
            <KPI label="Budget burn"      value="48.7%" sub="$1.21M of $2.49M FY26-Q2" delta={-1.3} kind="invert" accent="var(--d4)" spark={[0.1,0.18,0.27,0.34,0.4,0.45,0.487]} />
          </div>

          {/* Main row: chart + forecast + burn */}
          <div style={{ display: 'grid', gridTemplateColumns: '1.55fr 1fr', gap: 10 }}>
            {/* Stacked spend chart */}
            <div className="card" style={{ padding: '12px 14px 4px', display: 'flex', flexDirection: 'column', minHeight: 260 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 6 }}>
                <div className="section-title">Daily spend, by provider</div>
                <div style={{ flex: 1 }} />
                <Legend items={[
                  { color: 'var(--aws)',   label: 'AWS',   value: fmtUSD(aws.reduce((a,b)=>a+b,0), {compact:true}), active: activeProviders.includes('AWS')   },
                  { color: 'var(--gcp)',   label: 'GCP',   value: fmtUSD(gcp.reduce((a,b)=>a+b,0), {compact:true}), active: activeProviders.includes('GCP')   },
                  { color: 'var(--azure)', label: 'Azure', value: fmtUSD(az.reduce((a,b)=>a+b,0),  {compact:true}), active: activeProviders.includes('Azure') },
                ]} onToggle={toggleProvider} />
                {/* Chart mode switcher */}
                <div style={{ display: 'flex', background: 'var(--panel)', border: '1px solid var(--border)', borderRadius: 6, padding: 2 }}>
                  {['area','bar','line'].map(m => (
                    <div key={m} onClick={() => setChartMode(m)} style={{
                      padding: '2px 8px', fontSize: 11, borderRadius: 4, cursor: 'pointer',
                      background: chartMode === m ? 'var(--surface)' : 'transparent',
                      color:      chartMode === m ? 'var(--ink)' : 'var(--muted)',
                      fontWeight: chartMode === m ? 500 : 400,
                      textTransform: 'capitalize',
                    }}>{m}</div>
                  ))}
                </div>
              </div>
              <StackedArea
                width={760}
                height={208}
                mode={chartMode}
                xLabels={labels.map((l,i)=> i%2===0 ? `May ${l}` : '')}
                highlightIdx={10}
                series={[
                  { name: 'AWS',   color: 'var(--aws)',   data: aws },
                  { name: 'GCP',   color: 'var(--gcp)',   data: gcp },
                  { name: 'Azure', color: 'var(--azure)', data: az },
                ].filter(s => activeProviders.includes(s.name))}
              />
              <div style={{ display: 'flex', gap: 10, padding: '4px 0 6px', fontSize: 11, color: 'var(--muted)', borderTop: '1px solid var(--hairline)', marginTop: 4 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span style={{ width: 10, height: 2, background: 'var(--ink)', display: 'inline-block' }} />
                  <span>Tue · May 11</span>
                  <span className="mono" style={{ color: 'var(--ink)' }}>$98,420</span>
                  <Tag tone="negative">▲ 14% vs prior Tue</Tag>
                </div>
                <div style={{ flex: 1 }} />
                <span>peak hour 14:00 UTC · weekend dip −22%</span>
              </div>
            </div>

            {/* Forecast + Burn */}
            <div style={{ display: 'grid', gridTemplateRows: '1fr 1fr', gap: 10 }}>
              <ForecastCard forecast={forecast} />
              <BurnCard />
            </div>
          </div>

          {/* Sankey + AI insights */}
          <div style={{ display: 'grid', gridTemplateColumns: '1.55fr 1fr', gap: 10 }}>
            <div className="card" style={{ padding: '12px 14px', display: 'flex', flexDirection: 'column', minHeight: 218 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 6 }}>
                <div className="section-title">Where the money goes <span style={{ color: 'var(--muted)', fontWeight: 400 }}>· providers → services → teams</span></div>
                <div style={{ flex: 1 }} />
                <span className="chip ghost" style={{ fontSize: 10.5 }}>Sankey</span>
                <span className="chip ghost" style={{ fontSize: 10.5 }}>Treemap</span>
                <span className="chip ghost" style={{ fontSize: 10.5 }}>Sunburst</span>
              </div>
              <Sankey />
            </div>

            <div className="card" style={{ padding: '12px 14px', display: 'flex', flexDirection: 'column', minHeight: 218 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                <span style={{ color: 'var(--accent)', display: 'flex' }}><Ico name="sparkles" size={13} /></span>
                <div className="section-title">Lumen insights</div>
                <Tag tone="info">3 new</Tag>
                <div style={{ flex: 1 }} />
                <span style={{ fontSize: 10.5, color: 'var(--muted)' }}>powered by claude</span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6, overflow: 'hidden' }}>
                <Insight
                  tone="negative"
                  body={<>EKS <span className="mono">prod-us-east-1</span> spiked <b>+38%</b> Tue–Wed. Root cause: <i>idle gp3 volumes</i> after the <span className="mono">checkout-svc</span> rollback.</>}
                  meta="$18.4k impact" cta="Investigate"
                />
                <Insight
                  tone="positive"
                  body={<>Reserved-Instance coverage on <span className="mono">m6i.xlarge</span> is now <b>91%</b>. You're trending to capture <b>$42k</b> more savings this quarter.</>}
                  meta="+$42k Q2" cta="Plan"
                />
                <Insight
                  tone="warning"
                  body={<>Budget <i>"Data Platform"</i> on track to overshoot by <b>4.8%</b> if BigQuery slot use stays flat through May.</>}
                  meta="$28k risk" cta="Adjust"
                />
                <Insight
                  tone="info"
                  body={<>27 idle <span className="mono">Azure SQL</span> instances detected in <span className="mono">staging</span>. One-click reclaim: <b>$11.2k/mo</b>.</>}
                  meta="$11.2k/mo" cta="Reclaim"
                />
              </div>
            </div>
          </div>

          {/* Bottom rail: 3 panels */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10, paddingBottom: 14 }}>
            <Movers />
            <Services />
            <Teams />
          </div>
        </div>
      </div>
    </div>
  );
}

function ViewToggle({ active, onChange }) {
  const opts = ['Overview', 'P&L view', 'Unit economics'];
  return (
    <div style={{ display: 'flex', background: 'var(--panel)', border: '1px solid var(--border)', borderRadius: 8, padding: 2 }}>
      {opts.map((o) => (
        <div key={o} onClick={() => onChange(o)} style={{
          padding: '4px 10px', fontSize: 12, borderRadius: 6, cursor: 'pointer',
          background: active === o ? 'var(--surface)' : 'transparent',
          color:      active === o ? 'var(--ink)' : 'var(--muted)',
          fontWeight: active === o ? 500 : 400,
          boxShadow:  active === o ? 'var(--shadow-1)' : 'none',
        }}>{o}</div>
      ))}
    </div>
  );
}

function Legend({ items, onToggle }) {
  return (
    <div style={{ display: 'flex', gap: 10, fontSize: 11 }}>
      {items.map((it) => (
        <div key={it.label} onClick={() => onToggle?.(it.label)} style={{
          display: 'flex', alignItems: 'center', gap: 5,
          cursor: onToggle ? 'pointer' : 'default',
          opacity: it.active === false ? 0.35 : 1,
          transition: 'opacity 0.15s',
        }}>
          <span className="legend-dot" style={{ background: it.color }} />
          <span style={{ color: 'var(--muted)' }}>{it.label}</span>
          <span className="mono" style={{ color: 'var(--ink)', fontWeight: 500 }}>{it.value}</span>
        </div>
      ))}
    </div>
  );
}

function ForecastCard({ forecast }) {
  const W = 360, H = 90, padL = 6, padR = 6, padT = 4, padB = 14;
  const w = W - padL - padR, h = H - padT - padB;
  const realized = [0.1, 0.16, 0.22, 0.28, 0.33, 0.39, 0.44, 0.48];
  const fcastMid = [0.48, 0.55, 0.62, 0.7, 0.78, 0.86, 0.94, 1.00];
  const fcastHi  = [0.48, 0.57, 0.66, 0.76, 0.86, 0.96, 1.05, 1.08];
  const fcastLo  = [0.48, 0.53, 0.58, 0.64, 0.7, 0.76, 0.84, 0.92];
  const x = (i, n) => padL + (i / (n - 1)) * w * 0.5;
  const xF = (i, n) => padL + w * 0.5 + (i / (n - 1)) * w * 0.5;
  const y = (v) => padT + h - v * h;
  const realPath = realized.map((v, i) => `${i === 0 ? 'M' : 'L'}${x(i, realized.length)},${y(v)}`).join(' ');
  const midPath = fcastMid.map((v, i) => `${i === 0 ? 'M' : 'L'}${xF(i, fcastMid.length)},${y(v)}`).join(' ');
  const cone = fcastHi.map((v, i) => `${i === 0 ? 'M' : 'L'}${xF(i, fcastHi.length)},${y(v)}`).join(' ')
             + ' ' + fcastLo.slice().reverse().map((v, i) => `L${xF(fcastLo.length - 1 - i, fcastLo.length)},${y(v)}`).join(' ') + ' Z';
  return (
    <div className="card" style={{ padding: '12px 14px', display: 'flex', flexDirection: 'column', gap: 4 }}>
      <div style={{ display: 'flex', alignItems: 'center' }}>
        <div className="section-title">Forecast · end of May</div>
        <div style={{ flex: 1 }} />
        <Tag tone="info">92% conf.</Tag>
      </div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 10 }}>
        <div className="num" style={{ fontSize: 22, color: 'var(--ink)', fontWeight: 500, letterSpacing: '-0.02em' }}>{fmtUSD(forecast, { compact: true })}</div>
        <span style={{ fontSize: 11, color: 'var(--muted)' }}>± $48k · 14d Holt-Winters</span>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H}>
        {[0.25, 0.5, 0.75, 1.0].map(t => (
          <line key={t} x1={padL} x2={W - padR} y1={y(t)} y2={y(t)} stroke="var(--hairline)" strokeWidth="1" vectorEffect="non-scaling-stroke" />
        ))}
        <line x1={padL + w * 0.5} x2={padL + w * 0.5} y1={padT} y2={padT + h} stroke="var(--border)" strokeDasharray="2 3" vectorEffect="non-scaling-stroke" />
        <text x={padL + w * 0.5 + 4} y={padT + 9} fontSize="9" fill="var(--muted)" fontFamily="var(--font-num)">today</text>
        <path d={cone} fill="var(--accent)" opacity="0.13" />
        <path d={midPath} fill="none" stroke="var(--accent)" strokeWidth="1.4" strokeDasharray="3 2" vectorEffect="non-scaling-stroke" />
        <path d={realPath} fill="none" stroke="var(--ink)" strokeWidth="1.6" vectorEffect="non-scaling-stroke" />
        <line x1={padL} x2={W - padR} y1={y(0.95)} y2={y(0.95)} stroke="var(--negative)" strokeWidth="1" strokeDasharray="4 3" vectorEffect="non-scaling-stroke" />
        <text x={W - padR - 4} y={y(0.95) - 3} textAnchor="end" fontSize="9" fill="var(--negative)" fontFamily="var(--font-num)">budget $2.49M</text>
      </svg>
    </div>
  );
}

function BurnCard() {
  const segs = [
    { label: 'Compute',  value: 612, color: 'var(--d1)' },
    { label: 'Storage',  value: 218, color: 'var(--d2)' },
    { label: 'Network',  value: 184, color: 'var(--d3)' },
    { label: 'Data',     value: 142, color: 'var(--d4)' },
    { label: 'AI / GPU', value:  54, color: 'var(--d5)' },
  ];
  const total = segs.reduce((a, b) => a + b.value, 0);
  const budget = 2490;
  return (
    <div className="card" style={{ padding: '12px 14px', display: 'flex', flexDirection: 'column', gap: 8 }}>
      <div style={{ display: 'flex', alignItems: 'center' }}>
        <div className="section-title">Budget burn · Q2 FY26</div>
        <div style={{ flex: 1 }} />
        <Tag tone="warning">on pace +1.8%</Tag>
      </div>
      <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
        <div className="num" style={{ fontSize: 22, color: 'var(--ink)', fontWeight: 500 }}>${(total / 1000).toFixed(2)}M</div>
        <span style={{ fontSize: 11, color: 'var(--muted)' }}>of $2.49M · 48.7%</span>
      </div>
      <div style={{ display: 'flex', height: 10, borderRadius: 999, overflow: 'hidden', background: 'var(--hairline)' }}>
        {segs.map((s, i) => (
          <div key={i} style={{ width: `${(s.value / budget) * 100}%`, background: s.color }} />
        ))}
        <div style={{ flex: 1, background: 'var(--hairline)' }} />
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 4, fontSize: 10.5 }}>
        {segs.map((s) => (
          <div key={s.label}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
              <span className="legend-dot" style={{ background: s.color, width: 6, height: 6 }} />
              <span style={{ color: 'var(--muted)' }}>{s.label}</span>
            </div>
            <div className="mono" style={{ color: 'var(--ink)', fontWeight: 500 }}>${s.value}k</div>
          </div>
        ))}
      </div>
    </div>
  );
}

function Sankey() {
  const W = 760, H = 168;
  const left = [
    { id: 'aws', label: 'AWS', value: 612, color: 'var(--aws)' },
    { id: 'gcp', label: 'GCP', value: 348, color: 'var(--gcp)' },
    { id: 'az',  label: 'Azure', value: 218, color: 'var(--azure)' },
  ];
  const mid = [
    { id: 'compute', label: 'Compute',     value: 482, color: 'var(--d1)' },
    { id: 'ai',      label: 'AI / GPU',    value: 184, color: 'var(--d5)' },
    { id: 'data',    label: 'Data',        value: 218, color: 'var(--d4)' },
    { id: 'storage', label: 'Storage',     value: 188, color: 'var(--d2)' },
    { id: 'network', label: 'Network',     value: 106, color: 'var(--d3)' },
  ];
  const right = [
    { id: 'platform',  label: 'Platform',     value: 384, color: 'oklch(0.7 0.08 230)' },
    { id: 'data',      label: 'Data',         value: 268, color: 'oklch(0.7 0.08 145)' },
    { id: 'product',   label: 'Product',      value: 218, color: 'oklch(0.7 0.08 80)' },
    { id: 'ml',        label: 'ML Research',  value: 184, color: 'oklch(0.7 0.08 320)' },
    { id: 'corp',      label: 'Corp IT',      value: 124, color: 'oklch(0.7 0.08 30)' },
  ];
  const lp = [
    ['aws','compute',280], ['aws','storage',128], ['aws','network',88], ['aws','data',76], ['aws','ai',40],
    ['gcp','compute',132], ['gcp','data',98], ['gcp','ai',82], ['gcp','storage',24], ['gcp','network',12],
    ['az','compute',70], ['az','data',44], ['az','ai',62], ['az','storage',36], ['az','network',6],
  ];
  const ls = [
    ['compute','platform',180], ['compute','product',120], ['compute','data',92], ['compute','ml',60], ['compute','corp',30],
    ['ai','ml',104], ['ai','platform',38], ['ai','product',28], ['ai','data',14],
    ['data','data',120], ['data','platform',60], ['data','product',28], ['data','corp',10],
    ['storage','platform',82], ['storage','data',40], ['storage','product',30], ['storage','corp',36],
    ['network','platform',24], ['network','product',22], ['network','ml',12], ['network','corp',48],
  ];

  const colsX = [10, 240, 510, 700];
  const colW = 12;
  const padY = 6;
  const totalLeft = left.reduce((a, b) => a + b.value, 0);
  const scale = (H - padY * 2 - (left.length - 1) * 4) / totalLeft;

  const layoutCol = (col, x) => {
    let y = padY;
    return col.map((n) => {
      const h = n.value * scale;
      const ny = y;
      y += h + 4;
      return { ...n, x, y: ny, h };
    });
  };
  const L = layoutCol(left, colsX[0]);
  const totalMid = mid.reduce((a, b) => a + b.value, 0);
  const scaleM = (H - padY * 2 - (mid.length - 1) * 4) / totalMid;
  let my = padY;
  const M = mid.map((n) => { const h = n.value * scaleM; const ny = my; my += h + 4; return { ...n, x: colsX[1], y: ny, h }; });
  const totalR = right.reduce((a, b) => a + b.value, 0);
  const scaleR = (H - padY * 2 - (right.length - 1) * 4) / totalR;
  let ry = padY;
  const R = right.map((n) => { const h = n.value * scaleR; const ny = ry; ry += h + 4; return { ...n, x: colsX[2], y: ny, h }; });

  const leftCursor = Object.fromEntries(L.map(n => [n.id, 0]));
  const midCursorIn = Object.fromEntries(M.map(n => [n.id, 0]));
  const midCursorOut = Object.fromEntries(M.map(n => [n.id, 0]));
  const rightCursor = Object.fromEntries(R.map(n => [n.id, 0]));

  const linkPath = (x0, y0, h0, x1, y1, h1) => {
    const cx0 = x0 + (x1 - x0) * 0.5;
    return `M${x0},${y0} C${cx0},${y0} ${cx0},${y1} ${x1},${y1} L${x1},${y1 + h1} C${cx0},${y1 + h1} ${cx0},${y0 + h0} ${x0},${y0 + h0} Z`;
  };

  const links1 = lp.map(([pid, sid, v]) => {
    const p = L.find(n => n.id === pid);
    const s = M.find(n => n.id === sid);
    const h0 = v * scale;
    const h1 = v * scaleM;
    const y0 = p.y + leftCursor[pid];
    const y1 = s.y + midCursorIn[sid];
    leftCursor[pid] += h0;
    midCursorIn[sid] += h1;
    return { d: linkPath(p.x + colW, y0, h0, s.x, y1, h1), color: p.color };
  });
  const links2 = ls.map(([sid, tid, v]) => {
    const s = M.find(n => n.id === sid);
    const t = R.find(n => n.id === tid);
    const h0 = v * scaleM;
    const h1 = v * scaleR;
    const y0 = s.y + midCursorOut[sid];
    const y1 = t.y + rightCursor[tid];
    midCursorOut[sid] += h0;
    rightCursor[tid] += h1;
    return { d: linkPath(s.x + colW, y0, h0, t.x, y1, h1), color: s.color };
  });

  return (
    <div style={{ position: 'relative' }}>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H}>
        {['Provider', 'Service', 'Team'].map((t, i) => (
          <text key={t} x={colsX[i]} y={H + 0} fontSize="9.5" fill="var(--muted)" fontFamily="var(--font-num)" style={{ textTransform: 'uppercase', letterSpacing: '0.12em' }}>{t}</text>
        ))}
        {links1.map((l, i) => <path key={'a' + i} d={l.d} fill={l.color} opacity="0.32" />)}
        {links2.map((l, i) => <path key={'b' + i} d={l.d} fill={l.color} opacity="0.32" />)}
        {[...L, ...M, ...R].map((n) => (
          <g key={n.id + n.x}>
            <rect x={n.x} y={n.y} width={colW} height={n.h} fill={n.color} rx="2" />
            <text x={n.x + colW + 4} y={n.y + Math.min(11, n.h - 2)} fontSize="10.5" fill="var(--ink)" fontWeight="500">{n.label}</text>
            <text x={n.x + colW + 4} y={n.y + Math.min(22, n.h - 2)} fontSize="9" fill="var(--muted)" fontFamily="var(--font-num)">${n.value}k</text>
          </g>
        ))}
      </svg>
      <div style={{ display: 'flex', gap: 14, paddingTop: 16, fontSize: 11, color: 'var(--muted)' }}>
        <span>Top spender · <span className="mono" style={{ color: 'var(--ink)' }}>Platform team / EC2 compute</span> · $284k (23.7%)</span>
        <span style={{ flex: 1 }} />
        <span>Untagged share <span className="mono" style={{ color: 'var(--negative)' }}>4.8%</span> · $56k</span>
      </div>
    </div>
  );
}

function Insight({ tone, body, meta, cta }) {
  const map = { positive: 'positive', negative: 'negative', warning: 'warning', info: 'info' };
  return (
    <div style={{
      display: 'flex', alignItems: 'flex-start', gap: 10,
      padding: '8px 10px',
      background: 'var(--panel)',
      border: '1px solid var(--hairline)',
      borderLeft: `3px solid var(--${map[tone] || 'info'})`,
      borderRadius: 6,
    }}>
      <div style={{ flex: 1, fontSize: 11.5, lineHeight: 1.45, color: 'var(--text)' }}>
        {body}
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4, minWidth: 72 }}>
        <span className="mono" style={{ fontSize: 11, color: `var(--${map[tone] || 'info'})`, fontWeight: 500 }}>{meta}</span>
        <button className="btn" style={{ height: 22, padding: '0 8px', fontSize: 11 }}>{cta} <Ico name="chevR" size={9} /></button>
      </div>
    </div>
  );
}

function Movers() {
  const rows = [
    { svc: 'EKS · prod-us-east-1', d: 38.4, v: 18.4 },
    { svc: 'BigQuery · analytics', d: 22.1, v: 11.8 },
    { svc: 'S3 · ml-artifacts',    d: 14.7, v: 6.2 },
    { svc: 'Cloud Run · checkout', d: -28.4, v: -4.1 },
    { svc: 'RDS · prod-postgres',  d: -12.0, v: -2.8 },
  ];
  return (
    <div className="card" style={{ padding: '12px 14px', display: 'flex', flexDirection: 'column', gap: 6 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <div className="section-title">Top movers · 7d</div>
        <div style={{ flex: 1 }} />
        <span className="chip ghost" style={{ fontSize: 10.5 }}>by Δ$</span>
        <span className="chip" style={{ fontSize: 10.5 }}>by Δ%</span>
      </div>
      {rows.map((r) => {
        const up = r.d > 0;
        return (
          <div key={r.svc} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 0', borderBottom: '1px solid var(--hairline)' }}>
            <span style={{ color: up ? 'var(--negative)' : 'var(--positive)', display: 'flex' }}>
              <Ico name={up ? 'arrowU' : 'arrowD'} size={11} />
            </span>
            <span style={{ flex: 1, fontSize: 11.5, color: 'var(--ink)' }}>{r.svc}</span>
            <span className="mono" style={{ fontSize: 11.5, color: up ? 'var(--negative)' : 'var(--positive)', fontWeight: 500 }}>{pct(r.d)}</span>
            <span className="mono" style={{ fontSize: 11, color: 'var(--muted)', width: 48, textAlign: 'right' }}>{r.v > 0 ? '+' : ''}{r.v.toFixed(1)}k</span>
          </div>
        );
      })}
    </div>
  );
}

function Services() {
  const rows = [
    { svc: 'EC2',       p: 'AWS',   v: 312, share: 25.7, t: [1.1,1.2,1.3,1.4,1.5,1.6,1.7] },
    { svc: 'BigQuery',  p: 'GCP',   v: 184, share: 15.1, t: [.9,1.0,1.1,1.2,1.25,1.3,1.4] },
    { svc: 'EKS',       p: 'AWS',   v: 142, share: 11.7, t: [.7,.8,.85,.9,1.05,1.1,1.3] },
    { svc: 'Azure SQL', p: 'Azure', v:  98, share: 8.1,  t: [.5,.55,.6,.65,.7,.75,.78] },
    { svc: 'S3',        p: 'AWS',   v:  92, share: 7.6,  t: [.5,.55,.58,.6,.65,.68,.7] },
  ];
  return (
    <div className="card" style={{ padding: '12px 14px', display: 'flex', flexDirection: 'column', gap: 6 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <div className="section-title">Top services</div>
        <div style={{ flex: 1 }} />
        <a style={{ fontSize: 11, color: 'var(--muted)' }}>see all 47 →</a>
      </div>
      {rows.map((r) => (
        <div key={r.svc} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 0', borderBottom: '1px solid var(--hairline)' }}>
          <ProviderBadge p={r.p} />
          <span style={{ flex: 1, fontSize: 11.5, color: 'var(--ink)' }}>{r.svc}</span>
          <div style={{ width: 50, height: 16 }}>
            <Spark data={r.t} color="var(--muted)" height={16} showDot={false} />
          </div>
          <span className="mono" style={{ fontSize: 11.5, color: 'var(--ink)', fontWeight: 500, width: 40, textAlign: 'right' }}>${r.v}k</span>
          <span className="mono" style={{ fontSize: 10.5, color: 'var(--muted)', width: 38, textAlign: 'right' }}>{r.share}%</span>
        </div>
      ))}
    </div>
  );
}

function Teams() {
  const rows = [
    { team: 'Platform',    lead: 'Maya Park',  v: 384, b: 380, status: 'over', d: 1.1 },
    { team: 'Data',        lead: 'Sam Reyes',  v: 268, b: 290, status: 'ok',   d: -7.6 },
    { team: 'Product',     lead: 'Jin Cho',    v: 218, b: 240, status: 'ok',   d: -9.1 },
    { team: 'ML Research', lead: 'A. Okafor',  v: 184, b: 160, status: 'over', d: 15.0 },
    { team: 'Corp IT',     lead: 'L. Singh',   v: 124, b: 130, status: 'ok',   d: -4.6 },
  ];
  return (
    <div className="card" style={{ padding: '12px 14px', display: 'flex', flexDirection: 'column', gap: 6 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <div className="section-title">Teams · chargeback</div>
        <div style={{ flex: 1 }} />
        <span className="chip" style={{ fontSize: 10.5 }}>showback</span>
        <span className="chip ghost" style={{ fontSize: 10.5 }}>chargeback</span>
      </div>
      {rows.map((r) => (
        <div key={r.team} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '4px 0', borderBottom: '1px solid var(--hairline)' }}>
          <Avatar name={r.lead} size={18} />
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 11.5, color: 'var(--ink)' }}>{r.team}</div>
            <div style={{ height: 4, background: 'var(--hairline)', borderRadius: 999, overflow: 'hidden', marginTop: 2 }}>
              <div style={{ width: `${Math.min(100, (r.v / r.b) * 100)}%`, height: '100%', background: r.status === 'over' ? 'var(--negative)' : 'var(--positive)' }} />
            </div>
          </div>
          <span className="mono" style={{ fontSize: 11.5, color: 'var(--ink)', fontWeight: 500, width: 40, textAlign: 'right' }}>${r.v}k</span>
          <span className="mono" style={{ fontSize: 10.5, color: r.d > 0 ? 'var(--negative)' : 'var(--positive)', width: 40, textAlign: 'right' }}>{pct(r.d)}</span>
        </div>
      ))}
    </div>
  );
}
