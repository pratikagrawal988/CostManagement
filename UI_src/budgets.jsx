/* global React, Sidebar, Topbar, FilterBar, KPI, Spark, Ico, Tag, ProviderBadge, fmtUSD, pct, Avatar */

// ─────────────────────────────────────────────────────────────────
// Screen 4 — Budgets & Forecasts
// Top: KPI strip. Main: Q2 runway viz + budget list. Right: forecast
// scenarios & commitment timeline.
// ─────────────────────────────────────────────────────────────────
function BudgetsScreen() {
  return (
    <div className="lumen">
      <Sidebar active="budgets" />
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        <Topbar crumbs={['Acme Inc.', 'Budgets & Forecast', 'FY26 · Q2']} asMonth="May 2026" />
        <FilterBar
          range="Apr 1 – Jun 30, 2026"
          granularity="Monthly"
          filters={[
            { label: 'Period', value: 'FY26 · Q2' },
            { label: 'Scope', value: 'all budgets · 14' },
            { label: 'Currency', value: 'USD' },
          ]}
          compare="vs plan"
        />

        <div style={{ flex: 1, display: 'flex', minWidth: 0, overflow: 'hidden' }}>
          {/* MAIN */}
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, padding: '14px 14px 0', gap: 12, overflow: 'hidden' }}>
            {/* KPI strip */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10 }}>
              <KPI label="Plan · Q2 FY26"      value="$2.49M"  sub="14 budgets · 5 teams"          accent="var(--accent)" spark={[1.8,2.0,2.2,2.4,2.49,2.49,2.49]} />
              <KPI label="Realized + commit"   value="$2.54M"  sub="forecast EOQ · ▲ $48k"        delta={1.9} kind="invert" accent="var(--negative)" spark={[0.9,1.3,1.7,2.0,2.2,2.4,2.54]} />
              <KPI label="Available runway"    value="42 days" sub="at current burn rate"          accent="var(--d3)" spark={[60,56,52,48,46,44,42]} />
              <KPI label="Commitments active"  value="$1.84M"  sub="68% RIs · 22% SP · 10% CUD"   accent="var(--d2)" spark={[1.2,1.4,1.55,1.65,1.75,1.8,1.84]} />
            </div>

            {/* Runway viz */}
            <div className="card" style={{ padding: '12px 14px 10px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                <div className="section-title">FY26 · Q2 runway · realized + forecast vs plan</div>
                <Tag tone="warning">+1.9% over plan</Tag>
                <div style={{ flex: 1 }} />
                <div style={{ display: 'flex', gap: 4 }}>
                  <span className="chip" style={{ fontSize: 10.5 }}>Cumulative</span>
                  <span className="chip ghost" style={{ fontSize: 10.5 }}>Daily</span>
                  <span className="chip ghost" style={{ fontSize: 10.5 }}>Variance</span>
                </div>
              </div>
              <RunwayChart />
            </div>

            {/* Budgets list */}
            <div className="card" style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 14px', borderBottom: '1px solid var(--hairline)' }}>
                <div className="section-title">Budgets · 14</div>
                <Tag tone="negative">2 over</Tag>
                <Tag tone="warning">3 at risk</Tag>
                <div style={{ flex: 1 }} />
                <button className="btn ghost" style={{ height: 22, fontSize: 11 }}><Ico name="plus" size={10} /> New budget</button>
              </div>
              <div style={{ flex: 1, overflow: 'auto' }}>
                <table className="tbl">
                  <thead>
                    <tr>
                      <th>Budget</th>
                      <th>Owner</th>
                      <th>Period</th>
                      <th className="num">Plan</th>
                      <th className="num">Spent</th>
                      <th style={{ width: 220 }}>Burn</th>
                      <th className="num">Forecast EOQ</th>
                      <th className="num">Δ vs plan</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {[
                      { name: 'Platform · core infra',    owner: 'Maya Park',  plan: 880, spent: 612, fc: 920, status: 'over' },
                      { name: 'Data Platform',            owner: 'Sam Reyes',  plan: 540, spent: 268, fc: 568, status: 'risk' },
                      { name: 'ML Research · GPU',        owner: 'A. Okafor',  plan: 320, spent: 184, fc: 372, status: 'over' },
                      { name: 'Product · web',            owner: 'Jin Cho',    plan: 240, spent: 144, fc: 232, status: 'ok' },
                      { name: 'Product · mobile',         owner: 'Jin Cho',    plan: 180, spent:  74, fc: 158, status: 'ok' },
                      { name: 'Corp IT',                  owner: 'L. Singh',   plan: 130, spent:  56, fc: 124, status: 'ok' },
                      { name: 'Marketing CDN + edge',     owner: 'R. Adesina', plan:  90, spent:  42, fc:  88, status: 'risk' },
                      { name: 'Sandbox / staging',        owner: 'Maya Park',  plan: 110, spent:  46, fc:  96, status: 'ok' },
                    ].map((b) => {
                      const pctUsed = (b.spent / b.plan) * 100;
                      const fcPct = (b.fc / b.plan) * 100;
                      const delta = ((b.fc - b.plan) / b.plan) * 100;
                      const color = b.status === 'over' ? 'var(--negative)' : b.status === 'risk' ? 'var(--warning)' : 'var(--positive)';
                      return (
                        <tr key={b.name}>
                          <td style={{ color: 'var(--ink)', fontWeight: 500 }}>{b.name}</td>
                          <td><div style={{ display: 'flex', alignItems: 'center', gap: 6 }}><Avatar name={b.owner} size={16} />{b.owner}</div></td>
                          <td><span className="mono" style={{ color: 'var(--muted)', fontSize: 11 }}>Q2 · monthly reset</span></td>
                          <td className="num">${b.plan}k</td>
                          <td className="num">${b.spent}k</td>
                          <td>
                            <div style={{ position: 'relative', height: 12 }}>
                              <div style={{ position: 'absolute', inset: 0, height: 8, background: 'var(--hairline)', borderRadius: 999, marginTop: 2 }} />
                              <div style={{ position: 'absolute', height: 8, marginTop: 2, width: `${Math.min(100, pctUsed)}%`, background: color, borderRadius: 999 }} />
                              {/* forecast ghost extension */}
                              {fcPct > pctUsed && (
                                <div style={{ position: 'absolute', height: 8, marginTop: 2, left: `${Math.min(100, pctUsed)}%`, width: `${Math.min(100, fcPct - pctUsed)}%`, background: `repeating-linear-gradient(90deg, ${color} 0 3px, transparent 3px 6px)`, opacity: 0.55 }} />
                              )}
                              {/* plan tick */}
                              <div style={{ position: 'absolute', left: '100%', top: -1, bottom: -1, width: 2, background: 'var(--ink)', marginLeft: -1 }} />
                              <div style={{ position: 'absolute', left: '100%', top: -8, fontFamily: 'var(--font-num)', fontSize: 9, color: 'var(--muted)', transform: 'translateX(-100%)', paddingRight: 4 }}>{pctUsed.toFixed(0)}%</div>
                            </div>
                          </td>
                          <td className="num">${b.fc}k</td>
                          <td className="num"><span style={{ color: delta > 0 ? 'var(--negative)' : 'var(--positive)' }}>{pct(delta)}</span></td>
                          <td><Ico name="chevR" size={11} /></td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          {/* RIGHT — scenarios + commitments */}
          <aside style={{
            width: 320, flex: '0 0 320px',
            background: 'var(--panel)',
            borderLeft: '1px solid var(--border)',
            padding: 14,
            display: 'flex', flexDirection: 'column', gap: 12,
            overflow: 'auto',
          }}>
            <div>
              <div className="eyebrow">Forecast model</div>
              <div style={{ display: 'flex', gap: 4, marginTop: 6, flexWrap: 'wrap' }}>
                <span className="chip active" style={{ fontSize: 11 }}>Holt-Winters</span>
                <span className="chip" style={{ fontSize: 11 }}>Linear+Sched</span>
                <span className="chip" style={{ fontSize: 11 }}>Prophet</span>
                <span className="chip" style={{ fontSize: 11 }}>ARIMA</span>
              </div>
            </div>

            <div>
              <div className="eyebrow" style={{ marginBottom: 6 }}>Scenarios · EOQ</div>
              <Scenario tone="positive" label="Best case" amt="$2.41M" pct={-3.2}
                        body="Reclaim 84 idle gp3 volumes · scale spot-3 to 14n · close 18 zombie BQ schedules" />
              <Scenario tone="neutral"  label="Likely" amt="$2.54M" pct={1.9}
                        body="Current burn rate continues. Includes May 23 ML training run." selected />
              <Scenario tone="negative" label="Worst case" amt="$2.71M" pct={8.8}
                        body="Q2 launch traffic +30%. GPU contract Tier-3 renew at list price." />
            </div>

            <div>
              <div className="eyebrow" style={{ marginBottom: 6 }}>Commitment timeline</div>
              <CommitmentTimeline />
            </div>

            <div>
              <div className="eyebrow" style={{ marginBottom: 6 }}>Alerts</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                <AlertChip tone="negative" txt="Platform · core infra · forecast > 100% plan" who="3 owners notified" />
                <AlertChip tone="warning" txt="Data Platform · forecast > 95% plan" who="auto-throttle BQ slots" />
                <AlertChip tone="info" txt="Q2 closes in 47 days" who="finance review · Jun 5" />
              </div>
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}

function RunwayChart() {
  const W = 970, H = 220, padL = 44, padR = 16, padT = 8, padB = 22;
  const w = W - padL - padR, h = H - padT - padB;
  // 90 days in Q2: Apr 1 → Jun 30. We're at day 44 (May 14).
  const today = 44;
  const total = 90;
  // Plan line (linear from 0 → 2.49)
  const plan = (i) => (i / total) * 2.49;
  // Realized: faster burn
  const realized = Array.from({ length: today + 1 }, (_, i) => (i / total) * 2.49 * (1 + 0.05 * (i / total)));
  // Forecast mid: continues at slightly faster rate
  const fcMid = Array.from({ length: total - today + 1 }, (_, k) => {
    const i = today + k;
    return realized[today] + ((i - today) / total) * 2.49 * 1.05;
  });
  const fcHi = fcMid.map((v, k) => v * (1 + 0.04 * (k / (total - today))));
  const fcLo = fcMid.map((v, k) => v * (1 - 0.04 * (k / (total - today))));
  const max = 2.85;
  const x = (i) => padL + (i / total) * w;
  const y = (v) => padT + h - (v / max) * h;

  const planPath = Array.from({ length: total + 1 }, (_, i) => `${i === 0 ? 'M' : 'L'}${x(i)},${y(plan(i))}`).join(' ');
  const realPath = realized.map((v, i) => `${i === 0 ? 'M' : 'L'}${x(i)},${y(v)}`).join(' ');
  const midPath  = fcMid.map((v, k) => `${k === 0 ? 'M' : 'L'}${x(today + k)},${y(v)}`).join(' ');
  const cone     = fcHi.map((v, k) => `${k === 0 ? 'M' : 'L'}${x(today + k)},${y(v)}`).join(' ')
                 + fcLo.slice().reverse().map((v, k) => `L${x(total - k)},${y(v)}`).join(' ') + ' Z';

  // Where forecast hits 100% plan
  const overrun = fcMid.findIndex((v) => v > 2.49) + today;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H} style={{ marginTop: 4 }}>
      {/* y gridlines */}
      {[0.5, 1.0, 1.5, 2.0, 2.49].map((t, i) => (
        <g key={i}>
          <line x1={padL} x2={W - padR} y1={y(t)} y2={y(t)} stroke="var(--hairline)" strokeWidth="1" vectorEffect="non-scaling-stroke" />
          <text x={padL - 6} y={y(t) + 3} textAnchor="end" fontSize="9.5" fill="var(--muted)" fontFamily="var(--font-num)">{t === 2.49 ? '2.49M' : `${t.toFixed(1)}M`}</text>
        </g>
      ))}
      {/* month dividers */}
      {[0, 30, 60, 90].map(d => (
        <g key={d}>
          <line x1={x(d)} x2={x(d)} y1={padT} y2={padT + h} stroke="var(--hairline)" strokeWidth="1" vectorEffect="non-scaling-stroke" />
          <text x={x(d) + 4} y={H - 6} fontSize="10" fill="var(--muted)" fontFamily="var(--font-num)">{['Apr 1','May 1','Jun 1','Jun 30'][[0,30,60,90].indexOf(d)]}</text>
        </g>
      ))}
      {/* today divider */}
      <line x1={x(today)} x2={x(today)} y1={padT} y2={padT + h} stroke="var(--ink)" strokeWidth="1" strokeDasharray="3 3" vectorEffect="non-scaling-stroke" />
      <text x={x(today) + 4} y={padT + 11} fontSize="10" fill="var(--ink)" fontFamily="var(--font-num)" fontWeight="500">today · May 14</text>

      {/* plan line */}
      <path d={planPath} fill="none" stroke="var(--muted)" strokeWidth="1.4" strokeDasharray="4 3" vectorEffect="non-scaling-stroke" />
      <text x={x(total) - 4} y={y(2.49) - 4} textAnchor="end" fontSize="10" fill="var(--muted)" fontFamily="var(--font-num)">plan $2.49M</text>

      {/* cone */}
      <path d={cone} fill="var(--negative)" opacity="0.12" />
      {/* forecast mid */}
      <path d={midPath} fill="none" stroke="var(--negative)" strokeWidth="1.6" strokeDasharray="2 2" vectorEffect="non-scaling-stroke" />
      {/* realized */}
      <path d={realPath} fill="none" stroke="var(--ink)" strokeWidth="2" vectorEffect="non-scaling-stroke" />

      {/* overrun marker */}
      {overrun > today && (
        <g>
          <circle cx={x(overrun)} cy={y(2.49)} r="4" fill="var(--negative)" stroke="var(--bg)" strokeWidth="1.5" />
          <line x1={x(overrun)} x2={x(overrun)} y1={padT} y2={y(2.49)} stroke="var(--negative)" strokeWidth="1" strokeDasharray="2 2" vectorEffect="non-scaling-stroke" />
          <rect x={x(overrun) - 60} y={padT + 16} width="120" height="36" rx="4" fill="var(--surface)" stroke="var(--border)" />
          <text x={x(overrun)} y={padT + 30} textAnchor="middle" fontSize="10.5" fill="var(--negative)" fontFamily="var(--font-num)" fontWeight="500">Plan hit · Jun 24</text>
          <text x={x(overrun)} y={padT + 44} textAnchor="middle" fontSize="9" fill="var(--muted)" fontFamily="var(--font-num)">−6 days early</text>
        </g>
      )}

      {/* legend */}
      <g transform={`translate(${padL}, ${H - h - 8})`}>
        {[
          { c: 'var(--ink)', l: 'Realized', dash: false },
          { c: 'var(--muted)', l: 'Plan', dash: true },
          { c: 'var(--negative)', l: 'Forecast (likely)', dash: true },
        ].map((it, i) => (
          <g key={i} transform={`translate(${i * 110}, 0)`}>
            <line x1={0} x2={16} y1={0} y2={0} stroke={it.c} strokeWidth="2" strokeDasharray={it.dash ? '3 2' : ''} />
            <text x={20} y={3} fontSize="10" fill="var(--muted)">{it.l}</text>
          </g>
        ))}
      </g>
    </svg>
  );
}

function Scenario({ tone, label, amt, pct, body, selected }) {
  return (
    <div style={{
      display: 'flex', flexDirection: 'column', gap: 4,
      padding: '8px 10px', marginBottom: 6,
      background: 'var(--surface)',
      border: '1px solid var(--border)',
      borderLeft: `3px solid var(--${tone === 'neutral' ? 'accent' : tone})`,
      borderRadius: 6,
      outline: selected ? '1px solid var(--ink)' : 'none',
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <span style={{ fontSize: 11.5, fontWeight: 500, color: 'var(--ink)' }}>{label}</span>
        {selected && <Tag tone="info">selected</Tag>}
        <span style={{ flex: 1 }} />
        <span className="num" style={{ fontSize: 13, color: 'var(--ink)', fontWeight: 500 }}>{amt}</span>
        <span className="mono" style={{ fontSize: 10.5, color: `var(--${tone === 'positive' ? 'positive' : tone === 'negative' ? 'negative' : 'muted'})` }}>
          {pct > 0 ? '+' : ''}{pct.toFixed(1)}%
        </span>
      </div>
      <div style={{ fontSize: 11, color: 'var(--muted)', lineHeight: 1.4 }}>{body}</div>
    </div>
  );
}

function CommitmentTimeline() {
  // 6 commitments along a horizontal timeline. Show start, end, label.
  const W = 290, H = 130, padL = 6, padR = 6, padT = 18, padB = 18;
  const w = W - padL - padR, h = H - padT - padB;
  // Time window: now (day 0) → 365d
  const rows = [
    { name: '3yr Compute Savings Plan',  start:  -540, end:  555, val: '$840k', tone: 'positive' },
    { name: 'RI · m6i 1yr no-up',         start:  -120, end:  245, val: '$320k', tone: 'positive' },
    { name: 'CUD · BigQuery slots',       start:   -60, end:  305, val: '$180k', tone: 'positive' },
    { name: 'EA · Azure Reserved 3yr',    start:  -240, end:  855, val: '$420k', tone: 'info' },
    { name: 'GPU contract · Tier 3',       start:    20, end:  385, val: '$280k', tone: 'warning' },
  ];
  const minD = -560, maxD = 880;
  const x = (d) => padL + ((d - minD) / (maxD - minD)) * w;
  const rowY = (i) => padT + i * 20 + 4;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H}>
      {/* today */}
      <line x1={x(0)} x2={x(0)} y1={padT - 4} y2={H - padB + 4} stroke="var(--ink)" strokeWidth="1" strokeDasharray="2 2" />
      <text x={x(0)} y={padT - 7} textAnchor="middle" fontSize="9" fill="var(--ink)" fontFamily="var(--font-num)">today</text>
      {/* x ticks */}
      {[-365, 0, 365, 730].map(d => (
        <g key={d}>
          <line x1={x(d)} x2={x(d)} y1={H - padB + 1} y2={H - padB + 4} stroke="var(--muted)" />
          <text x={x(d)} y={H - 4} textAnchor="middle" fontSize="8.5" fill="var(--muted)" fontFamily="var(--font-num)">
            {d === 0 ? "'26" : d === 365 ? "'27" : d === -365 ? "'25" : "'28"}
          </text>
        </g>
      ))}
      {rows.map((r, i) => (
        <g key={i} transform={`translate(0, ${rowY(i)})`}>
          <rect x={x(r.start)} y={0} width={x(r.end) - x(r.start)} height={12} fill={`var(--${r.tone})`} opacity="0.18" rx="2" />
          <rect x={x(Math.max(r.start, 0))} y={0} width={Math.max(0, x(r.end) - x(Math.max(r.start, 0)))} height={12} fill={`var(--${r.tone})`} opacity="0.6" rx="2" />
          <text x={x(r.start) + 4} y={9} fontSize="9" fill="var(--ink)" fontWeight="500">{r.name}</text>
          <text x={x(r.end) - 4} y={9} textAnchor="end" fontSize="9" fill="var(--ink)" fontFamily="var(--font-num)">{r.val}</text>
        </g>
      ))}
    </svg>
  );
}

function AlertChip({ tone, txt, who }) {
  return (
    <div style={{
      padding: '6px 8px', display: 'flex', gap: 8,
      background: 'var(--surface)',
      borderLeft: `3px solid var(--${tone})`,
      border: '1px solid var(--border)', borderLeft: `3px solid var(--${tone})`,
      borderRadius: 4,
    }}>
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: 11.5, color: 'var(--ink)' }}>{txt}</div>
        <div style={{ fontSize: 10.5, color: 'var(--muted)' }}>{who}</div>
      </div>
    </div>
  );
}

Object.assign(window, { BudgetsScreen });
