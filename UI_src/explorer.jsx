/* global React, Sidebar, Topbar, FilterBar, KPI, Spark, StackedArea, Ico, Tag, ProviderBadge, fmtUSD, pct, genCostSeries */

// ─────────────────────────────────────────────────────────────────
// Screen 2 — Cost Explorer
// Pivot/group-by chart with breakdown table. Left rail = dimensions
// & saved views. Bottom strip = scrubbable "lens" for time selection.
// ─────────────────────────────────────────────────────────────────
function ExplorerScreen({ chartMode = 'area' }) {
  const days = 30;
  const ec2 = genCostSeries(28000, days, 0.04, 0.12, 0.20, 11);
  const eks = genCostSeries(14000, days, 0.10, 0.14, 0.16, 31);
  const bq  = genCostSeries(12000, days, 0.06, 0.10, 0.10, 41);
  const s3  = genCostSeries( 9000, days, 0.02, 0.06, 0.05, 51);
  const sql = genCostSeries( 8000, days, 0.03, 0.08, 0.18, 61);
  const lab = genCostSeries( 6000, days, 0.08, 0.13, 0.22, 71);
  const labels = Array.from({ length: days }, (_, i) => String(i + 1).padStart(2, '0'));

  // Range lens selection: days 8..23
  const lensStart = 8, lensEnd = 23;

  return (
    <div className="lumen">
      <Sidebar active="explorer" />
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        <Topbar crumbs={['Acme Inc.', 'Cost Explorer', 'Spend by service']} asMonth="May 2026" />
        <FilterBar
          range="May 9 – 24, 2026"
          granularity="Daily"
          filters={[
            { label: 'Environment', value: 'production' },
            { label: 'Region', value: 'us-east-1, eu-west-1' },
            { label: 'Project', value: 'all 12' },
          ]}
        />

        <div style={{ flex: 1, display: 'flex', minWidth: 0, overflow: 'hidden' }}>
          {/* LEFT RAIL — group by + saved views */}
          <aside style={{
            width: 220, flex: '0 0 220px',
            background: 'var(--panel)',
            borderRight: '1px solid var(--border)',
            padding: '14px 12px',
            display: 'flex', flexDirection: 'column', gap: 14,
            fontSize: 12,
            overflow: 'auto',
          }}>
            <div>
              <div className="eyebrow">Group by</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 6 }}>
                {[['Service', true], ['Account', false], ['Region', false], ['Team', false], ['Environment', false], ['Tag · cost-center', false], ['Resource', false], ['Usage type', false]].map(([n, on]) => (
                  <span key={n} className={`chip ${on ? 'active' : ''}`} style={{ fontSize: 11 }}>
                    {on && <Ico name="check" size={9} />}
                    {n}
                  </span>
                ))}
              </div>
            </div>
            <div>
              <div className="eyebrow">Stack by</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 6 }}>
                {[['none', false], ['provider', true], ['account', false], ['region', false]].map(([n, on]) => (
                  <span key={n} className={`chip ${on ? 'active' : ''}`} style={{ fontSize: 11 }}>{n}</span>
                ))}
              </div>
            </div>
            <div>
              <div className="eyebrow">Measure</div>
              <div style={{ display: 'grid', gap: 4, marginTop: 6 }}>
                {[
                  ['Unblended cost', true],
                  ['Amortized cost', false],
                  ['Net cost (post-credits)', false],
                  ['Usage hours', false],
                  ['$ per RPS', false],
                ].map(([n, on]) => (
                  <div key={n} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '3px 6px', borderRadius: 4, background: on ? 'var(--surface)' : 'transparent', border: on ? '1px solid var(--border)' : '1px solid transparent', color: on ? 'var(--ink)' : 'var(--text)', fontWeight: on ? 500 : 400 }}>
                    <span style={{ width: 10, height: 10, borderRadius: 999, border: '1.5px solid var(--muted)', background: on ? 'var(--ink)' : 'transparent', boxShadow: on ? 'inset 0 0 0 2px var(--surface)' : 'none' }} />
                    {n}
                  </div>
                ))}
              </div>
            </div>
            <div>
              <div className="eyebrow">Saved views</div>
              <div style={{ display: 'grid', gap: 2, marginTop: 6 }}>
                {[
                  { name: 'Monthly board pack', emoji: '★', current: false },
                  { name: 'EKS deep-dive',      emoji: '◆', current: true },
                  { name: 'BigQuery slot cost', emoji: '◆', current: false },
                  { name: 'GPU spend by team',  emoji: '◆', current: false },
                  { name: 'Untagged audit',     emoji: '◆', current: false },
                ].map((v) => (
                  <div key={v.name} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '4px 6px', borderRadius: 4, background: v.current ? 'var(--surface)' : 'transparent', border: v.current ? '1px solid var(--border)' : '1px solid transparent', color: v.current ? 'var(--ink)' : 'var(--text)', fontWeight: v.current ? 500 : 400 }}>
                    <span style={{ color: 'var(--muted)', fontFamily: 'var(--font-num)', fontSize: 10 }}>{v.emoji}</span>
                    <span style={{ flex: 1, fontSize: 11.5 }}>{v.name}</span>
                    {v.current && <Ico name="pin" size={10} />}
                  </div>
                ))}
                <button className="btn ghost" style={{ justifyContent: 'flex-start', padding: '4px 6px', height: 22, fontSize: 11 }}>
                  <Ico name="plus" size={10} /> New view
                </button>
              </div>
            </div>
          </aside>

          {/* MAIN */}
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, padding: '12px 14px', gap: 10, overflow: 'hidden' }}>
            {/* Sub-toolbar */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div>
                <div className="eyebrow">Spend by service</div>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginTop: 2 }}>
                  <div className="num" style={{ fontSize: 26, color: 'var(--ink)', fontWeight: 500, letterSpacing: '-0.02em' }}>$1.84M</div>
                  <span className="mono" style={{ fontSize: 11.5, color: 'var(--negative)' }}>+ 6.4%</span>
                  <span style={{ fontSize: 11, color: 'var(--muted)' }}>vs Apr · 30d window · 47 services</span>
                </div>
              </div>
              <div style={{ flex: 1 }} />
              <div style={{ display: 'flex', background: 'var(--panel)', border: '1px solid var(--border)', borderRadius: 8, padding: 2 }}>
                {['Stacked', 'Area', 'Bar', 'Line', 'Table'].map((m, i) => (
                  <div key={m} style={{
                    padding: '3px 9px', fontSize: 11.5, borderRadius: 6,
                    background: i === 0 ? 'var(--surface)' : 'transparent',
                    color: i === 0 ? 'var(--ink)' : 'var(--muted)',
                    fontWeight: i === 0 ? 500 : 400,
                  }}>{m}</div>
                ))}
              </div>
              <button className="btn ghost"><Ico name="link" size={11} /> Copy link</button>
              <button className="btn"><Ico name="pin" size={11} /> Pin to board</button>
            </div>

            {/* Main chart */}
            <div className="card" style={{ padding: '10px 14px', flex: '0 0 auto' }}>
              <StackedArea
                width={960}
                height={260}
                mode={chartMode}
                xLabels={labels.map((l, i) => i % 3 === 0 ? `May ${l}` : '')}
                highlightIdx={14}
                series={[
                  { name: 'EC2',       color: 'var(--d1)', data: ec2 },
                  { name: 'EKS',       color: 'var(--d5)', data: eks },
                  { name: 'BigQuery',  color: 'var(--d2)', data: bq },
                  { name: 'S3',        color: 'var(--d3)', data: s3 },
                  { name: 'Azure SQL', color: 'var(--d4)', data: sql },
                  { name: 'Lambda',    color: 'var(--d6)', data: lab },
                ]}
              />
              <div style={{ display: 'flex', gap: 14, padding: '6px 0 0', flexWrap: 'wrap', fontSize: 11 }}>
                {[
                  ['EC2',       'var(--d1)', 'AWS',   ec2.reduce((a,b)=>a+b,0)],
                  ['EKS',       'var(--d5)', 'AWS',   eks.reduce((a,b)=>a+b,0)],
                  ['BigQuery',  'var(--d2)', 'GCP',   bq.reduce((a,b)=>a+b,0)],
                  ['S3',        'var(--d3)', 'AWS',   s3.reduce((a,b)=>a+b,0)],
                  ['Azure SQL', 'var(--d4)', 'Azure', sql.reduce((a,b)=>a+b,0)],
                  ['Lambda',    'var(--d6)', 'AWS',   lab.reduce((a,b)=>a+b,0)],
                ].map(([n, c, p, v]) => (
                  <div key={n} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                    <span className="legend-dot" style={{ background: c }} />
                    <span style={{ color: 'var(--ink)', fontWeight: 500 }}>{n}</span>
                    <span style={{ color: 'var(--muted)' }}>· {p}</span>
                    <span className="mono" style={{ color: 'var(--muted)' }}>{fmtUSD(v, { compact: true })}</span>
                  </div>
                ))}
                <span style={{ flex: 1 }} />
                <span style={{ color: 'var(--muted)' }}>showing top 6 of 47 · group remainder as <a style={{ color: 'var(--accent)' }}>Other</a></span>
              </div>
            </div>

            {/* Lens scrubber */}
            <Lens days={days} labels={labels} lensStart={lensStart} lensEnd={lensEnd}
                  data={[ec2, eks, bq, s3, sql, lab].map((d, i) => ({ data: d, color: ['var(--d1)','var(--d5)','var(--d2)','var(--d3)','var(--d4)','var(--d6)'][i] }))} />

            {/* Breakdown table */}
            <BreakdownTable />
          </div>
        </div>
      </div>
    </div>
  );
}

function Lens({ days, labels, lensStart, lensEnd, data }) {
  const W = 960, H = 46, padL = 38, padR = 12;
  const w = W - padL - padR;
  const x = (i) => padL + (i / (days - 1)) * w;
  // Build cumulative stacked points
  const totals = Array.from({ length: days }, (_, i) => data.reduce((a, s) => a + s.data[i], 0));
  const max = Math.max(...totals);
  const stackedAreas = [];
  for (let si = 0; si < data.length; si++) {
    const top = [], bot = [];
    let acc;
    for (let i = 0; i < days; i++) {
      acc = 0;
      for (let k = 0; k < si; k++) acc += data[k].data[i];
      const yBot = H - (acc / max) * (H - 6) - 2;
      const yTop = H - ((acc + data[si].data[i]) / max) * (H - 6) - 2;
      top.push([x(i), yTop]); bot.push([x(i), yBot]);
    }
    const d = top.map((p, i) => `${i === 0 ? 'M' : 'L'}${p[0]},${p[1]}`).join(' ')
            + bot.reverse().map(p => ` L${p[0]},${p[1]}`).join(' ') + ' Z';
    stackedAreas.push({ d, color: data[si].color });
  }
  const xS = x(lensStart), xE = x(lensEnd);

  return (
    <div className="card" style={{ padding: '8px 14px 6px', display: 'flex', flexDirection: 'column', gap: 4 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11, color: 'var(--muted)' }}>
        <span>Range · </span>
        <span className="mono" style={{ color: 'var(--ink)' }}>May 9</span>
        <Ico name="arrowR" size={10} />
        <span className="mono" style={{ color: 'var(--ink)' }}>May 24</span>
        <span className="chip ghost" style={{ fontSize: 10.5 }}>16 days</span>
        <div style={{ flex: 1 }} />
        <span className="chip ghost" style={{ fontSize: 10.5 }}>1d</span>
        <span className="chip ghost" style={{ fontSize: 10.5 }}>7d</span>
        <span className="chip" style={{ fontSize: 10.5 }}>14d</span>
        <span className="chip ghost" style={{ fontSize: 10.5 }}>30d</span>
        <span className="chip ghost" style={{ fontSize: 10.5 }}>QTD</span>
        <span className="chip ghost" style={{ fontSize: 10.5 }}>YTD</span>
        <span className="chip ghost" style={{ fontSize: 10.5 }}>Custom…</span>
      </div>
      <div style={{ position: 'relative' }}>
        <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H} preserveAspectRatio="none">
          {stackedAreas.map((s, i) => <path key={i} d={s.d} fill={s.color} opacity="0.6" />)}
          {/* unselected mask */}
          <rect x={padL} y="0" width={xS - padL} height={H} fill="var(--panel)" opacity="0.7" />
          <rect x={xE} y="0" width={W - padR - xE} height={H} fill="var(--panel)" opacity="0.7" />
          {/* selection borders */}
          <line x1={xS} x2={xS} y1="0" y2={H} stroke="var(--ink)" strokeWidth="1.5" />
          <line x1={xE} x2={xE} y1="0" y2={H} stroke="var(--ink)" strokeWidth="1.5" />
          {/* x ticks */}
          {labels.map((l, i) => i % 5 === 0 && (
            <text key={i} x={x(i)} y={H - 1} textAnchor="middle" fontSize="9" fill="var(--muted)" fontFamily="var(--font-num)">May {l}</text>
          ))}
        </svg>
        {/* handles */}
        {[xS, xE].map((px, i) => (
          <div key={i} style={{
            position: 'absolute', left: `${(px / W) * 100}%`, top: 0, bottom: 0,
            width: 8, marginLeft: -4,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <div style={{ width: 4, height: 18, background: 'var(--ink)', borderRadius: 2, boxShadow: '0 0 0 1px var(--bg)' }} />
          </div>
        ))}
      </div>
    </div>
  );
}

function BreakdownTable() {
  const rows = [
    { svc: 'EC2',       p: 'AWS',  acct: 'prod-aws-1',       env: 'production', cur: 312840, prev: 295120, share: 0.169, t: [.7,.8,.85,.9,.95,1.05,1.15,1.18,1.22,1.3,1.32,1.4,1.42,1.48], owner: 'Platform' },
    { svc: 'EKS',       p: 'AWS',  acct: 'prod-aws-1',       env: 'production', cur: 184220, prev: 156400, share: 0.100, t: [.6,.65,.7,.78,.82,.88,.95,1.0,1.12,1.2,1.25,1.32,1.38,1.4], owner: 'Platform', flag: 'anomaly' },
    { svc: 'BigQuery',  p: 'GCP',  acct: 'data-analytics',   env: 'production', cur: 142180, prev: 138700, share: 0.077, t: [.8,.82,.85,.88,.9,.95,.98,1.0,1.02,1.05,1.08,1.1,1.12,1.14], owner: 'Data' },
    { svc: 'S3',        p: 'AWS',  acct: 'prod-aws-1',       env: 'production', cur:  92410, prev:  90120, share: 0.050, t: [.9,.92,.93,.95,.96,.97,.98,1.0,1.01,1.02,1.03,1.04,1.05,1.06], owner: 'Platform' },
    { svc: 'Azure SQL', p: 'Azure',acct: 'enterprise-az',    env: 'production', cur:  84620, prev:  88300, share: 0.046, t: [1.05,1.04,1.03,1.02,1.0,.98,.96,.95,.94,.93,.92,.92,.91,.9], owner: 'Data' },
    { svc: 'Lambda',    p: 'AWS',  acct: 'prod-aws-1',       env: 'production', cur:  62800, prev:  54200, share: 0.034, t: [.5,.55,.6,.65,.7,.78,.82,.9,.95,1.0,1.05,1.12,1.16,1.2], owner: 'Product' },
    { svc: 'GKE',       p: 'GCP',  acct: 'data-analytics',   env: 'production', cur:  48910, prev:  42100, share: 0.027, t: [.7,.75,.8,.82,.85,.88,.92,.95,1.0,1.05,1.08,1.12,1.16,1.2], owner: 'Data' },
    { svc: 'Cloud Run', p: 'GCP',  acct: 'prod-gcp-svc',     env: 'production', cur:  38240, prev:  46700, share: 0.021, t: [1.2,1.15,1.1,1.05,1.0,.95,.92,.88,.84,.82,.8,.78,.78,.77], owner: 'Product' },
    { svc: 'RDS',       p: 'AWS',  acct: 'prod-aws-1',       env: 'production', cur:  32100, prev:  34800, share: 0.017, t: [1.1,1.08,1.05,1.04,1.02,1.0,.98,.97,.95,.94,.93,.92,.92,.91], owner: 'Platform' },
    { svc: 'CloudFront',p: 'AWS',  acct: 'prod-aws-1',       env: 'production', cur:  21420, prev:  19800, share: 0.012, t: [.85,.88,.9,.92,.94,.96,.98,1.0,1.02,1.04,1.06,1.08,1.1,1.12], owner: 'Platform' },
  ];

  return (
    <div className="card" style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 14px', borderBottom: '1px solid var(--hairline)' }}>
        <div className="section-title">Breakdown</div>
        <span style={{ fontSize: 11, color: 'var(--muted)' }}>47 rows · selected May 9–24</span>
        <div style={{ flex: 1 }} />
        <div className="chip ghost" style={{ fontSize: 11 }}><Ico name="search" size={10} /> Filter rows…</div>
        <div className="chip ghost" style={{ fontSize: 11 }}>Columns: 8</div>
        <button className="btn ghost" style={{ height: 22, fontSize: 11 }}>Group →</button>
      </div>
      <div style={{ flex: 1, overflow: 'auto' }}>
        <table className="tbl">
          <thead>
            <tr>
              <th style={{ width: 32 }}></th>
              <th>Service</th>
              <th>Account</th>
              <th>Owner</th>
              <th>Env</th>
              <th className="num">Cost</th>
              <th style={{ width: 110 }}>Share</th>
              <th className="num">Δ vs prev</th>
              <th style={{ width: 92 }}>14d trend</th>
              <th style={{ width: 20 }}></th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const delta = (r.cur - r.prev) / r.prev * 100;
              return (
                <tr key={r.svc}>
                  <td><ProviderBadge p={r.p} /></td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span style={{ color: 'var(--ink)', fontWeight: 500 }}>{r.svc}</span>
                      {r.flag === 'anomaly' && <Tag tone="negative">⚠ anomaly</Tag>}
                    </div>
                  </td>
                  <td><span className="mono" style={{ color: 'var(--muted)' }}>{r.acct}</span></td>
                  <td>{r.owner}</td>
                  <td><span style={{ fontSize: 11, color: 'var(--muted)' }}>{r.env}</span></td>
                  <td className="num">{fmtUSD(r.cur)}</td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <div className="inline-bar" style={{ flex: 1 }}><i style={{ width: `${r.share * 100 / 0.17}%`, background: 'var(--d1)' }} /></div>
                      <span className="mono" style={{ fontSize: 10.5, color: 'var(--muted)', width: 30, textAlign: 'right' }}>{(r.share * 100).toFixed(1)}%</span>
                    </div>
                  </td>
                  <td className="num"><span style={{ color: delta > 0 ? 'var(--negative)' : 'var(--positive)' }}>{pct(delta)}</span></td>
                  <td><div style={{ width: 84, height: 18 }}><Spark data={r.t} color={delta > 0 ? 'var(--negative)' : 'var(--positive)'} height={18} showDot={false} /></div></td>
                  <td><Ico name="chevR" size={11} /></td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 14px', borderTop: '1px solid var(--hairline)', fontSize: 11, color: 'var(--muted)' }}>
        <span>Showing 10 of 47 services · others ≤ $20k</span>
        <div style={{ flex: 1 }} />
        <span>Total selected · </span>
        <span className="mono" style={{ color: 'var(--ink)', fontWeight: 500 }}>$1.84M</span>
        <span>·</span>
        <span className="mono" style={{ color: 'var(--negative)' }}>+6.4% vs prev</span>
      </div>
    </div>
  );
}

Object.assign(window, { ExplorerScreen });
