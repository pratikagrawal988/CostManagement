/* global React, Sidebar, Topbar, FilterBar, KPI, Spark, Ico, Tag, ProviderBadge, fmtUSD, pct, genCostSeries, Avatar */

// ─────────────────────────────────────────────────────────────────
// Screen 6 — Resource Drill-down
// Treemap on the left, resource detail on the right. Novel: a
// "depth breadcrumb" lets you drill 5 levels with one keystroke.
// ─────────────────────────────────────────────────────────────────
function DrilldownScreen() {
  return (
    <div className="lumen">
      <Sidebar active="drilldown" />
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        <Topbar crumbs={['Acme Inc.', 'Resources', 'AWS · prod-aws-1', 'EKS', 'prod-us-east-1']} asMonth="May 2026" />
        <FilterBar
          range="May 1 – 14, 2026"
          granularity="Daily"
          filters={[
            { label: 'Tag · team', value: 'Platform' },
            { label: 'Resource', value: 'all 1,284' },
            { label: 'State', value: 'running' },
          ]}
        />

        {/* Drill ribbon */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 0,
          padding: '8px 14px',
          background: 'var(--bg)',
          borderBottom: '1px solid var(--hairline)',
          fontSize: 12,
        }}>
          {[
            { lvl: 'Org',     name: 'Acme Inc.',      v: '$1.18M', done: true },
            { lvl: 'Account', name: 'prod-aws-1',     v: '$612k',  done: true },
            { lvl: 'Service', name: 'EKS',            v: '$142k',  done: true },
            { lvl: 'Cluster', name: 'prod-us-east-1', v: '$98k',   active: true },
            { lvl: 'Workload',name: '— choose —',     v: null },
            { lvl: 'Pod',     name: '— choose —',     v: null },
          ].map((d, i, arr) => (
            <React.Fragment key={i}>
              <div style={{ display: 'flex', flexDirection: 'column', minWidth: 0, padding: '0 12px', borderLeft: i === 0 ? 'none' : '1px solid var(--hairline)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                  <span className="eyebrow" style={{ fontSize: 9 }}>{d.lvl}</span>
                  {d.active && <span style={{ width: 5, height: 5, borderRadius: 999, background: 'var(--accent)' }} />}
                </div>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: 6 }}>
                  <span className="mono" style={{ fontSize: 12.5, color: d.v ? 'var(--ink)' : 'var(--muted)', fontWeight: d.active ? 500 : 400 }}>{d.name}</span>
                  {d.v && <span className="mono" style={{ fontSize: 10.5, color: 'var(--muted)' }}>{d.v}</span>}
                </div>
              </div>
              {i < arr.length - 1 && <Ico name="chevR" size={10} />}
            </React.Fragment>
          ))}
          <div style={{ flex: 1 }} />
          <span className="kbd">[</span>
          <span style={{ color: 'var(--muted)', fontSize: 11, margin: '0 4px' }}>up</span>
          <span className="kbd">]</span>
          <span style={{ color: 'var(--muted)', fontSize: 11, margin: '0 4px' }}>down</span>
        </div>

        <div style={{ flex: 1, display: 'flex', minWidth: 0, overflow: 'hidden' }}>
          {/* MAIN — treemap */}
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, padding: '12px 14px', gap: 10, overflow: 'hidden' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <div className="section-title">prod-us-east-1 · workloads</div>
              <span style={{ fontSize: 11, color: 'var(--muted)' }}>1,284 resources · 14 namespaces · 24 nodes</span>
              <div style={{ flex: 1 }} />
              <div style={{ display: 'flex', background: 'var(--panel)', border: '1px solid var(--border)', borderRadius: 8, padding: 2 }}>
                {['Treemap', 'Sunburst', 'Table', 'Graph'].map((m, i) => (
                  <div key={m} style={{
                    padding: '3px 9px', fontSize: 11.5, borderRadius: 6,
                    background: i === 0 ? 'var(--surface)' : 'transparent',
                    color: i === 0 ? 'var(--ink)' : 'var(--muted)',
                    fontWeight: i === 0 ? 500 : 400,
                  }}>{m}</div>
                ))}
              </div>
              <div style={{ display: 'flex', background: 'var(--panel)', border: '1px solid var(--border)', borderRadius: 8, padding: 2 }}>
                {['Size: cost', 'Color: util'].map((m, i) => (
                  <div key={m} style={{
                    padding: '3px 9px', fontSize: 11.5, borderRadius: 6,
                    color: 'var(--muted)',
                  }}>{m}</div>
                ))}
              </div>
            </div>

            <div className="card" style={{ flex: 1, padding: 8, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
              <Treemap />
              {/* legend */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 6px 0', fontSize: 11 }}>
                <span style={{ color: 'var(--muted)' }}>color · CPU utilization</span>
                <div style={{ display: 'flex', height: 8, width: 200, borderRadius: 2, overflow: 'hidden' }}>
                  <div style={{ flex: 1, background: 'oklch(0.55 0.2 26)' }} />
                  <div style={{ flex: 1, background: 'oklch(0.7 0.16 50)' }} />
                  <div style={{ flex: 1, background: 'oklch(0.78 0.12 90)' }} />
                  <div style={{ flex: 1, background: 'oklch(0.7 0.13 150)' }} />
                  <div style={{ flex: 1, background: 'oklch(0.55 0.13 200)' }} />
                </div>
                <span className="mono" style={{ fontSize: 10, color: 'var(--muted)' }}>0%</span>
                <span style={{ flex: 1 }} />
                <span className="mono" style={{ fontSize: 10, color: 'var(--muted)' }}>100%</span>
                <span style={{ flex: 1 }} />
                <span style={{ color: 'var(--muted)' }}>size · monthly cost</span>
              </div>
            </div>
          </div>

          {/* RIGHT — selected resource */}
          <aside style={{
            width: 380, flex: '0 0 380px',
            background: 'var(--panel)',
            borderLeft: '1px solid var(--border)',
            padding: 14,
            display: 'flex', flexDirection: 'column', gap: 12,
            overflow: 'auto',
            fontSize: 12,
          }}>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <ProviderBadge p="AWS" />
                <span className="mono" style={{ fontSize: 11, color: 'var(--muted)' }}>EKS / Deployment</span>
                <div style={{ flex: 1 }} />
                <Tag tone="negative">over-provisioned</Tag>
              </div>
              <h3 style={{ margin: '6px 0 2px', fontSize: 18, color: 'var(--ink)', fontWeight: 500, letterSpacing: '-0.01em' }}>
                checkout-api
              </h3>
              <div className="mono" style={{ fontSize: 11, color: 'var(--muted)' }}>
                arn:aws:eks:us-east-1:412...:deployment/checkout-api
              </div>
              <div style={{ display: 'flex', gap: 4, marginTop: 6, flexWrap: 'wrap' }}>
                <Tag>team=platform</Tag>
                <Tag>service=checkout</Tag>
                <Tag>env=prod</Tag>
                <Tag>tier=critical</Tag>
                <Tag tone="warning">cost-owner=∅</Tag>
              </div>
            </div>

            {/* Cost KPI */}
            <div className="card" style={{ padding: '10px 12px' }}>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
                <div className="num" style={{ fontSize: 22, color: 'var(--ink)', fontWeight: 500 }}>$12,840</div>
                <span style={{ fontSize: 11, color: 'var(--muted)' }}>/ mo</span>
                <Tag tone="negative">▲ 18%</Tag>
                <div style={{ flex: 1 }} />
                <span className="mono" style={{ fontSize: 11, color: 'var(--muted)' }}>14 pods · 28 vCPU</span>
              </div>
              <Spark data={[8,8.2,8.4,8.5,9,9.5,10.2,10.6,11.0,11.4,11.9,12.4,12.7,12.8]} color="var(--accent)" height={40} />
            </div>

            {/* Utilization */}
            <div>
              <div className="eyebrow" style={{ marginBottom: 6 }}>Utilization · 14d P95</div>
              <UtilBar label="CPU"    used={16} req={100} color="var(--d4)" tone="negative" />
              <UtilBar label="Memory" used={24} req={100} color="var(--d4)" tone="negative" />
              <UtilBar label="Net I/O" used={48} req={100} color="var(--d3)" tone="warning" />
              <UtilBar label="Disk"    used={72} req={100} color="var(--d2)" tone="positive" />
            </div>

            {/* Dependencies */}
            <div>
              <div className="eyebrow" style={{ marginBottom: 6 }}>Dependencies · 7d traffic</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 3, fontSize: 11 }}>
                {[
                  ['payments-api',   'inbound',  4_120_000, '$0'],
                  ['fraud-detector', 'outbound', 2_640_000, '$0'],
                  ['rds · prod-pg',  'outbound',   840_000, '$1,840'],
                  ['s3 · receipts',  'outbound',   420_000, '$220'],
                  ['stripe (ext)',   'outbound',   180_000, '$84'],
                ].map((r, i) => (
                  <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '2px 0', borderBottom: '1px dashed var(--hairline)' }}>
                    <Ico name={r[1] === 'inbound' ? 'arrowR' : 'arrowR'} size={10} />
                    <span className="mono" style={{ flex: 1, color: 'var(--ink)' }}>{r[0]}</span>
                    <span style={{ fontSize: 10, color: 'var(--muted)' }}>{r[1]}</span>
                    <span className="mono" style={{ fontSize: 10.5, color: 'var(--muted)', width: 72, textAlign: 'right' }}>{(r[2] / 1_000_000).toFixed(2)}M req</span>
                    <span className="mono" style={{ fontSize: 11, color: 'var(--ink)', width: 50, textAlign: 'right' }}>{r[3]}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* Cost composition */}
            <div>
              <div className="eyebrow" style={{ marginBottom: 6 }}>Cost composition</div>
              <CompBar segs={[
                { label: 'Compute',    v: 7800, c: 'var(--d1)' },
                { label: 'EBS gp3',    v: 2240, c: 'var(--d2)' },
                { label: 'NAT / data', v: 1640, c: 'var(--d3)' },
                { label: 'ECR pulls',  v:  680, c: 'var(--d5)' },
                { label: 'CloudWatch', v:  480, c: 'var(--d6)' },
              ]} />
            </div>

            {/* Actions */}
            <div style={{ display: 'flex', gap: 6, paddingTop: 4 }}>
              <button className="btn primary" style={{ flex: 1, justifyContent: 'center', height: 30 }}>
                <Ico name="check" size={12} /> Apply right-size
              </button>
              <button className="btn" style={{ height: 30 }}>Tag…</button>
              <button className="btn ghost" style={{ height: 30, padding: '0 8px' }}><Ico name="link" size={12} /></button>
            </div>
            <div style={{ fontSize: 10.5, color: 'var(--muted)' }}>
              Suggested · <span className="mono">m6i.2xl → m6i.xl</span> · save <span className="mono" style={{ color: 'var(--positive)' }}>$4.8k/mo</span>
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
// TREEMAP — squarified-ish layout. Manually packed rectangles for
// realism, with utilization-based color.
// ─────────────────────────────────────────────────────────────────
function Treemap() {
  // Total area: roughly 820 x 460. Bigger boxes = more cost.
  // Color encodes CPU utilization: red = under-utilized (waste), green = healthy mid, blue = high (saturated).
  const utilColor = (util) => {
    if (util < 25) return 'oklch(0.68 0.17 28)';       // red
    if (util < 45) return 'oklch(0.75 0.14 50)';       // amber
    if (util < 65) return 'oklch(0.8 0.12 95)';        // yellow-green
    if (util < 85) return 'oklch(0.7 0.13 150)';       // green
    return 'oklch(0.6 0.13 210)';                       // blue-ish
  };
  const utilColorTxt = (util) => util < 45 ? 'oklch(0.25 0.05 28)' : 'oklch(0.18 0.05 150)';

  // Manually packed layout (so the result actually reads like a treemap, not random rectangles)
  // Each item: { x, y, w, h, name, cost, util, pods, ns }
  // Coordinate space 100 x 100 — we'll scale to container.
  const items = [
    // Big block — checkout namespace
    { x:  0, y:  0, w: 38, h: 56, name: 'checkout-api',    cost: 12840, util: 16, pods: 14, ns: 'checkout', selected: true },
    { x:  0, y: 56, w: 20, h: 44, name: 'checkout-worker', cost:  6420, util: 38, pods:  8, ns: 'checkout' },
    { x: 20, y: 56, w: 18, h: 44, name: 'checkout-cron',   cost:  3210, util: 22, pods:  3, ns: 'checkout' },

    // Search namespace
    { x: 38, y:  0, w: 24, h: 44, name: 'search-svc',      cost:  8120, util: 62, pods:  6, ns: 'search' },
    { x: 38, y: 44, w: 24, h: 22, name: 'search-indexer',  cost:  4060, util: 54, pods:  4, ns: 'search' },
    { x: 38, y: 66, w: 14, h: 34, name: 'embed-svc',       cost:  2820, util: 71, pods:  3, ns: 'search' },
    { x: 52, y: 66, w: 10, h: 34, name: 'query-cache',     cost:  1820, util: 89, pods:  2, ns: 'search' },

    // Payments
    { x: 62, y:  0, w: 22, h: 36, name: 'payments-api',    cost:  6840, util: 58, pods:  8, ns: 'payments' },
    { x: 62, y: 36, w: 22, h: 22, name: 'fraud-detector',  cost:  4220, util: 64, pods:  4, ns: 'payments' },
    { x: 62, y: 58, w: 12, h: 24, name: 'ledger',          cost:  2640, util: 42, pods:  3, ns: 'payments' },
    { x: 74, y: 58, w: 10, h: 24, name: 'risk-stream',     cost:  1980, util: 48, pods:  2, ns: 'payments' },
    { x: 62, y: 82, w: 22, h: 18, name: 'payouts',         cost:  1620, util: 28, pods:  2, ns: 'payments' },

    // Platform shared
    { x: 84, y:  0, w: 16, h: 24, name: 'auth-svc',        cost:  3280, util: 36, pods:  4, ns: 'platform' },
    { x: 84, y: 24, w: 16, h: 22, name: 'gateway',         cost:  3120, util: 81, pods:  4, ns: 'platform' },
    { x: 84, y: 46, w: 16, h: 22, name: 'notify-svc',      cost:  1840, util: 18, pods:  3, ns: 'platform' },
    { x: 84, y: 68, w: 16, h: 16, name: 'config-svc',      cost:    920, util: 12, pods:  2, ns: 'platform' },
    { x: 84, y: 84, w: 16, h: 16, name: 'cron-runner',     cost:    640, util:  8, pods:  2, ns: 'platform' },
  ];

  return (
    <div style={{ position: 'relative', flex: 1, minHeight: 0, borderRadius: 4, overflow: 'hidden' }}>
      <div style={{ position: 'absolute', inset: 0, padding: 2 }}>
        <div style={{ position: 'relative', width: '100%', height: '100%' }}>
          {items.map((it, i) => {
            const bg = utilColor(it.util);
            return (
              <div key={i} style={{
                position: 'absolute',
                left: `${it.x}%`, top: `${it.y}%`,
                width: `calc(${it.w}% - 2px)`, height: `calc(${it.h}% - 2px)`,
                background: bg,
                outline: it.selected ? '2px solid var(--ink)' : 'none',
                outlineOffset: it.selected ? -2 : 0,
                borderRadius: 3,
                padding: 8,
                display: 'flex', flexDirection: 'column', justifyContent: 'space-between',
                overflow: 'hidden',
                color: utilColorTxt(it.util),
                cursor: 'pointer',
                boxShadow: 'inset 0 0 0 1px rgba(255,255,255,0.18)',
              }}>
                {/* hatch overlay for waste */}
                {it.util < 25 && (
                  <div style={{ position: 'absolute', inset: 0, backgroundImage: 'repeating-linear-gradient(45deg, rgba(0,0,0,0.05) 0 3px, transparent 3px 8px)' }} />
                )}
                <div style={{ position: 'relative', display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <div style={{ fontSize: it.w * it.h > 800 ? 13 : 11, fontWeight: 500, lineHeight: 1.1, letterSpacing: '-0.005em' }}>{it.name}</div>
                  {it.w * it.h > 600 && (
                    <div style={{ display: 'flex', gap: 6, fontSize: 9.5, fontFamily: 'var(--font-num)', opacity: 0.85 }}>
                      <span>ns/{it.ns}</span>
                      <span>· {it.pods}p</span>
                    </div>
                  )}
                </div>
                <div style={{ position: 'relative', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', fontFamily: 'var(--font-num)', fontSize: it.w * it.h > 800 ? 12 : 10 }}>
                  <span style={{ fontWeight: 600 }}>${(it.cost / 1000).toFixed(1)}k</span>
                  <span style={{ opacity: 0.8 }}>{it.util}%</span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function UtilBar({ label, used, req, color, tone }) {
  const pct = (used / req) * 100;
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '3px 0' }}>
      <span style={{ width: 56, fontSize: 11, color: 'var(--muted)' }}>{label}</span>
      <div style={{ flex: 1, position: 'relative', height: 14 }}>
        <div style={{ position: 'absolute', inset: 0, height: 8, marginTop: 3, background: 'var(--hairline)', borderRadius: 2 }} />
        <div style={{ position: 'absolute', height: 8, marginTop: 3, width: `${pct}%`, background: color, borderRadius: 2 }} />
        {/* request marker */}
        <div style={{ position: 'absolute', left: '100%', top: 0, bottom: 0, width: 1, background: 'var(--ink)', marginLeft: -1 }} />
      </div>
      <span className="mono" style={{ fontSize: 11, width: 70, textAlign: 'right', color: `var(--${tone})` }}>{used}% / 100%</span>
    </div>
  );
}

function CompBar({ segs }) {
  const total = segs.reduce((a, b) => a + b.v, 0);
  return (
    <div>
      <div style={{ display: 'flex', height: 12, borderRadius: 999, overflow: 'hidden', background: 'var(--hairline)' }}>
        {segs.map((s, i) => (
          <div key={i} style={{ width: `${(s.v / total) * 100}%`, background: s.c }} />
        ))}
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 4, marginTop: 6, fontSize: 11 }}>
        {segs.map((s) => (
          <div key={s.label} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span className="legend-dot" style={{ background: s.c, width: 7, height: 7 }} />
            <span style={{ color: 'var(--muted)', flex: 1 }}>{s.label}</span>
            <span className="mono" style={{ color: 'var(--ink)', fontWeight: 500 }}>${s.v.toLocaleString()}</span>
            <span className="mono" style={{ color: 'var(--muted)', width: 36, textAlign: 'right', fontSize: 10 }}>{((s.v / total) * 100).toFixed(0)}%</span>
          </div>
        ))}
      </div>
    </div>
  );
}

Object.assign(window, { DrilldownScreen });
