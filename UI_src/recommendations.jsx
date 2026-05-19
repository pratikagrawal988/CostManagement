/* global React, Sidebar, Topbar, FilterBar, KPI, Spark, Ico, Tag, ProviderBadge, fmtUSD, pct */

// ─────────────────────────────────────────────────────────────────
// Screen 5 — Recommendations
// Savings opportunities, scorable, actionable. Right rail = detail.
// ─────────────────────────────────────────────────────────────────
function RecommendationsScreen() {
  const recs = [
    {
      id: 'rec-441', sel: true,
      title: 'Right-size 142 over-provisioned EC2 instances',
      svc: 'EC2', p: 'AWS', cat: 'Right-size',
      savings: 48200, period: '/mo',
      complexity: 'low', risk: 'low', confidence: 94,
      blast: 'prod · 12 services',
      desc: 'CPU < 18% over 30 days. Move m6i.2xlarge → m6i.xlarge (Graviton fallback if Linux).',
      owner: 'Platform',
    },
    {
      id: 'rec-417',
      title: 'Convert 84 idle gp3 volumes to snapshots',
      svc: 'EBS', p: 'AWS', cat: 'Cleanup',
      savings: 4200, period: '/mo',
      complexity: 'low', risk: 'medium', confidence: 88,
      blast: 'staging · platform',
      desc: 'Detached for 14+ days. Snapshot + delete preserves recovery path.',
      owner: 'Platform',
    },
    {
      id: 'rec-402',
      title: 'Adopt Compute Savings Plan · 3yr no-upfront · $1.4M/yr',
      svc: 'EC2 + Fargate + Lambda', p: 'AWS', cat: 'Commitment',
      savings: 312000, period: '/yr',
      complexity: 'medium', risk: 'low', confidence: 96,
      blast: 'all environments',
      desc: 'Sustained baseline > 64% over 90d qualifies. Locks $0.0312/hr vs $0.0464.',
      owner: 'FinOps',
    },
    {
      id: 'rec-389',
      title: 'Move 8 cold S3 buckets to Glacier IR',
      svc: 'S3', p: 'AWS', cat: 'Storage',
      savings: 9600, period: '/mo',
      complexity: 'low', risk: 'low', confidence: 92,
      blast: 'ml-artifacts · logs-archive',
      desc: 'No reads in 90 days, 14.2 TB total. Glacier IR keeps ms retrieval.',
      owner: 'Data',
    },
    {
      id: 'rec-374',
      title: 'Close 27 idle Azure SQL instances in staging',
      svc: 'Azure SQL', p: 'Azure', cat: 'Cleanup',
      savings: 11200, period: '/mo',
      complexity: 'low', risk: 'medium', confidence: 84,
      blast: 'staging only',
      desc: 'Zero connections over 21 days. Auto-snapshot before stop.',
      owner: 'Data',
    },
    {
      id: 'rec-362',
      title: 'Schedule BigQuery slots · auto-scale to 600 off-hours',
      svc: 'BigQuery', p: 'GCP', cat: 'Schedule',
      savings: 8400, period: '/mo',
      complexity: 'medium', risk: 'low', confidence: 90,
      blast: 'data team workloads',
      desc: 'Slot usage 18:00–06:00 averages 38%. Reserve 600, autoscale on demand.',
      owner: 'Data',
    },
    {
      id: 'rec-348',
      title: 'Switch 4 NAT Gateways to VPC endpoints for S3 + DynamoDB',
      svc: 'VPC', p: 'AWS', cat: 'Network',
      savings: 6800, period: '/mo',
      complexity: 'medium', risk: 'low', confidence: 86,
      blast: 'prod-aws-1',
      desc: 'Avoid per-GB NAT charges on intra-region S3/DDB traffic.',
      owner: 'Platform',
    },
  ];
  const selected = recs.find(r => r.sel) || recs[0];

  return (
    <div className="lumen">
      <Sidebar active="recommendations" />
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        <Topbar crumbs={['Acme Inc.', 'Recommendations']} asMonth="May 2026" />
        <FilterBar
          range="Across all open"
          granularity="Monthly"
          filters={[
            { label: 'Category', value: 'all 6' },
            { label: 'Status', value: 'open · 28' },
            { label: 'Owner', value: 'all teams' },
          ]}
          compare="annual savings"
        />

        <div style={{ flex: 1, display: 'flex', minWidth: 0, overflow: 'hidden' }}>
          {/* MAIN */}
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, padding: '14px 14px 0', gap: 12, overflow: 'hidden' }}>
            {/* Hero pipeline */}
            <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr 1fr 1fr', gap: 10 }}>
              <div className="card" style={{ padding: '14px 18px', display: 'flex', flexDirection: 'column', gap: 6, background: 'linear-gradient(180deg, oklch(0.97 0.02 150) 0%, var(--surface) 70%)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span className="legend-dot" style={{ background: 'var(--positive)' }} />
                  <span className="eyebrow">Potential savings · annualized</span>
                  <span style={{ flex: 1 }} />
                  <Tag tone="positive">+4 new today</Tag>
                </div>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: 10 }}>
                  <div className="num display" style={{ fontStyle: 'normal', fontFamily: 'var(--font-num)', fontSize: 38, color: 'var(--ink)', fontWeight: 500, letterSpacing: '-0.025em', lineHeight: 1 }}>$842,400</div>
                  <span className="mono" style={{ fontSize: 13, color: 'var(--positive)' }}>+ 18.4%</span>
                </div>
                <div style={{ fontSize: 11.5, color: 'var(--muted)' }}>28 open recommendations · ø $30k each · 91% one-click eligible</div>
                {/* Funnel */}
                <div style={{ display: 'flex', marginTop: 6, alignItems: 'center', gap: 4 }}>
                  {[
                    { label: 'Open', v: 842, c: 'var(--d1)' },
                    { label: 'Triaged', v: 612, c: 'var(--d3)' },
                    { label: 'Approved', v: 384, c: 'var(--d2)' },
                    { label: 'Applied', v: 184, c: 'var(--positive)' },
                  ].map((s, i, arr) => (
                    <React.Fragment key={s.label}>
                      <div style={{ display: 'flex', flexDirection: 'column', flex: s.v / 842 * 1.4, gap: 2 }}>
                        <div className="mono" style={{ fontSize: 10.5, color: 'var(--ink)', fontWeight: 500 }}>${s.v}k</div>
                        <div style={{ height: 8, background: s.c, borderRadius: 4, opacity: 0.7 }} />
                        <div style={{ fontSize: 10, color: 'var(--muted)' }}>{s.label}</div>
                      </div>
                      {i < arr.length - 1 && <Ico name="chevR" size={10} />}
                    </React.Fragment>
                  ))}
                </div>
              </div>

              <KPI label="Applied · 30d"      value="$184k"   sub="68% of triaged"             delta={42} accent="var(--positive)" spark={[40,60,80,110,140,165,184]} />
              <KPI label="Avg time to apply"  value="3.2 days" sub="↓ from 8.4 days Q1"        delta={-62} accent="var(--d2)" spark={[8,7,6,5,4,3.6,3.2]} />
              <KPI label="One-click eligible" value="91%"     sub="auto-revert window 48h"     delta={4} accent="var(--accent)" spark={[80,82,85,87,89,90,91]} />
            </div>

            {/* Category bar */}
            <div style={{ display: 'flex', gap: 6, alignItems: 'center', flexWrap: 'wrap' }}>
              {[
                ['All',          '28', true],
                ['Right-size',   '9'],
                ['Cleanup',      '6'],
                ['Commitment',   '4'],
                ['Storage',      '4'],
                ['Schedule',     '3'],
                ['Network',      '2'],
              ].map(([n, c, on]) => (
                <span key={n} className={`chip ${on ? 'active' : ''}`} style={{ fontSize: 11.5, height: 24 }}>
                  {n}
                  <span className="mono" style={{ fontSize: 10, opacity: 0.6, marginLeft: 2 }}>{c}</span>
                </span>
              ))}
              <div style={{ flex: 1 }} />
              <div className="chip ghost" style={{ fontSize: 11 }}>Sort: highest savings</div>
              <div className="chip ghost" style={{ fontSize: 11 }}>Filter: low risk</div>
            </div>

            {/* Recs grid */}
            <div style={{ flex: 1, overflow: 'auto', display: 'flex', flexDirection: 'column', gap: 8, paddingBottom: 14 }}>
              {recs.map((r) => <RecCard key={r.id} rec={r} />)}
            </div>
          </div>

          {/* RIGHT — selected recommendation */}
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
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <Tag tone="positive">Right-size</Tag>
                <span className="mono" style={{ fontSize: 10.5, color: 'var(--muted)' }}>rec-441 · 30d obs.</span>
                <div style={{ flex: 1 }} />
                <button className="btn ghost" style={{ padding: '0 6px' }}><Ico name="link" size={11} /></button>
              </div>
              <h3 style={{ margin: '6px 0 4px', fontSize: 16, color: 'var(--ink)', fontWeight: 500, letterSpacing: '-0.01em', lineHeight: 1.3 }}>
                Right-size 142 EC2 instances to <span className="mono" style={{ fontSize: 13 }}>m6i.xlarge</span>
              </h3>
              <div style={{ fontSize: 12, color: 'var(--text)', lineHeight: 1.5 }}>
                Instances running at <b className="mono">&lt; 18%</b> CPU and <b className="mono">&lt; 24%</b> memory P95 across 30 days.
                Step-down keeps headroom; Graviton fallback applied where AMI compatible.
              </div>
            </div>

            {/* Savings hero */}
            <div className="card" style={{ padding: '10px 12px', background: 'linear-gradient(180deg, oklch(0.97 0.03 150) 0%, var(--surface) 60%)' }}>
              <div className="eyebrow">Net savings</div>
              <div style={{ display: 'flex', alignItems: 'baseline', gap: 8 }}>
                <div className="num" style={{ fontSize: 24, color: 'var(--positive)', fontWeight: 500 }}>$48.2k</div>
                <span style={{ fontSize: 11, color: 'var(--muted)' }}>/ month</span>
              </div>
              <div className="mono" style={{ fontSize: 11, color: 'var(--muted)' }}>$578.4k / year · payback &lt; 1 month</div>
              {/* Before/after bar */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 8 }}>
                <span style={{ fontSize: 10.5, color: 'var(--muted)', width: 44 }}>before</span>
                <div style={{ flex: 1, height: 10, background: 'var(--hairline)', borderRadius: 2, position: 'relative' }}>
                  <div style={{ width: '100%', height: '100%', background: 'var(--d4)', opacity: 0.7, borderRadius: 2 }} />
                </div>
                <span className="mono" style={{ fontSize: 11, color: 'var(--ink)', width: 50, textAlign: 'right' }}>$118k</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 4 }}>
                <span style={{ fontSize: 10.5, color: 'var(--muted)', width: 44 }}>after</span>
                <div style={{ flex: 1, height: 10, background: 'var(--hairline)', borderRadius: 2, position: 'relative' }}>
                  <div style={{ width: '59%', height: '100%', background: 'var(--positive)', opacity: 0.7, borderRadius: 2 }} />
                </div>
                <span className="mono" style={{ fontSize: 11, color: 'var(--ink)', width: 50, textAlign: 'right' }}>$70k</span>
              </div>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6 }}>
              <Detail label="Risk"        value="Low"  tone="positive" sub="auto-revert 48h" />
              <Detail label="Complexity"  value="Low"  tone="positive" sub="batched · IaC patch" />
              <Detail label="Confidence"  value="94%"  sub="z=3.1 vs cohort" />
              <Detail label="Blast"       value="142 instances" sub="prod · 12 services" />
            </div>

            <div>
              <div className="eyebrow" style={{ marginBottom: 6 }}>Impacted resources · top 5</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
                {[
                  ['i-0a2b3c · checkout-api',     'm6i.2xl', 'm6i.xl',  '$612/mo'],
                  ['i-0d3e4f · search-svc',       'm6i.2xl', 'm6i.xl',  '$612/mo'],
                  ['i-0e7g8h · payments-worker',  'r6i.xl',  't3.large','$520/mo'],
                  ['i-0g9h0i · auth-svc',         'c6i.2xl', 'c6i.xl',  '$480/mo'],
                  ['i-0i1j2k · notify-svc',       'm6i.xl',  'm6g.xl',  '$182/mo'],
                ].map((r, i) => (
                  <div key={i} style={{ display: 'flex', gap: 6, fontSize: 11, padding: '2px 0', borderBottom: '1px dashed var(--hairline)' }}>
                    <span className="mono" style={{ flex: 1, color: 'var(--ink)' }}>{r[0]}</span>
                    <span className="mono" style={{ color: 'var(--muted)' }}>{r[1]}</span>
                    <Ico name="arrowR" size={10} />
                    <span className="mono" style={{ color: 'var(--positive)' }}>{r[2]}</span>
                    <span className="mono" style={{ width: 56, textAlign: 'right' }}>{r[3]}</span>
                  </div>
                ))}
                <a style={{ fontSize: 11, color: 'var(--accent)', marginTop: 4 }}>see all 142 →</a>
              </div>
            </div>

            <div>
              <div className="eyebrow" style={{ marginBottom: 4 }}>Approval flow</div>
              <ApprovalFlow />
            </div>

            <div style={{ display: 'flex', gap: 6, paddingTop: 4 }}>
              <button className="btn primary" style={{ flex: 1, justifyContent: 'center', height: 30 }}>
                <Ico name="check" size={12} /> Apply now · $48.2k/mo
              </button>
              <button className="btn" style={{ height: 30 }}>Schedule</button>
              <button className="btn ghost" style={{ height: 30, padding: '0 8px' }}>Snooze</button>
            </div>
            <div style={{ fontSize: 10.5, color: 'var(--muted)', textAlign: 'center' }}>
              Auto-revert window 48h · rollback link sent to <span className="mono">#finops-alerts</span>
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}

function RecCard({ rec }) {
  const annual = rec.period === '/yr' ? rec.savings : rec.savings * 12;
  const riskTone = rec.risk === 'low' ? 'positive' : rec.risk === 'medium' ? 'warning' : 'negative';
  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: '52px 1fr 110px 110px 130px 200px',
      gap: 12,
      alignItems: 'center',
      padding: '12px 14px',
      background: rec.sel ? 'var(--surface)' : 'var(--surface)',
      border: '1px solid var(--border)',
      borderLeft: rec.sel ? '3px solid var(--ink)' : '3px solid var(--positive)',
      borderRadius: 8,
      boxShadow: rec.sel ? 'var(--shadow-pop)' : 'var(--shadow-1)',
    }}>
      {/* Savings cell */}
      <div style={{ display: 'flex', flexDirection: 'column' }}>
        <div className="num" style={{ fontSize: 16, color: 'var(--ink)', fontWeight: 500, lineHeight: 1 }}>${(rec.savings / 1000).toFixed(rec.savings < 10000 ? 1 : 0)}k</div>
        <div className="mono" style={{ fontSize: 9.5, color: 'var(--muted)' }}>{rec.period}</div>
      </div>

      <div style={{ minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 2 }}>
          <span style={{ fontSize: 13, color: 'var(--ink)', fontWeight: 500, letterSpacing: '-0.005em' }}>{rec.title}</span>
        </div>
        <div style={{ display: 'flex', gap: 6, alignItems: 'center', fontSize: 11, color: 'var(--muted)' }}>
          <ProviderBadge p={rec.p} />
          <span className="mono">{rec.svc}</span>
          <span>·</span>
          <span>{rec.cat}</span>
          <span>·</span>
          <span>owner <span style={{ color: 'var(--ink)' }}>{rec.owner}</span></span>
          <span>·</span>
          <span style={{ fontFamily: 'var(--font-num)' }}>{rec.id}</span>
        </div>
        <div style={{ fontSize: 11.5, color: 'var(--text)', marginTop: 4, lineHeight: 1.4 }}>{rec.desc}</div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: 4, alignItems: 'flex-start' }}>
        <Tag tone={riskTone}>{rec.risk} risk</Tag>
        <Tag tone="info">{rec.complexity} effort</Tag>
      </div>

      <div>
        <div className="eyebrow" style={{ fontSize: 9 }}>Confidence</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 4, marginTop: 2 }}>
          <div className="num" style={{ fontSize: 14, color: 'var(--ink)', fontWeight: 500 }}>{rec.confidence}%</div>
          <div style={{ flex: 1, height: 4, background: 'var(--hairline)', borderRadius: 999, overflow: 'hidden' }}>
            <div style={{ width: `${rec.confidence}%`, height: '100%', background: 'var(--positive)' }} />
          </div>
        </div>
        <div className="mono" style={{ fontSize: 10, color: 'var(--muted)', marginTop: 2 }}>annual ${(annual / 1000).toFixed(0)}k</div>
      </div>

      <div style={{ fontSize: 11, color: 'var(--muted)' }}>
        <div className="eyebrow" style={{ fontSize: 9 }}>Blast radius</div>
        <div style={{ color: 'var(--ink)', marginTop: 2 }}>{rec.blast}</div>
      </div>

      <div style={{ display: 'flex', gap: 4, justifyContent: 'flex-end' }}>
        {rec.sel ? (
          <>
            <button className="btn primary" style={{ height: 28 }}><Ico name="check" size={11} /> Apply</button>
            <button className="btn" style={{ height: 28 }}>Schedule</button>
          </>
        ) : (
          <>
            <button className="btn ghost" style={{ height: 26, padding: '0 6px' }}>Dismiss</button>
            <button className="btn" style={{ height: 26 }}>Review</button>
            <button className="btn primary" style={{ height: 26 }}>Apply</button>
          </>
        )}
      </div>
    </div>
  );
}

function Detail({ label, value, sub, tone }) {
  return (
    <div className="card-flush" style={{ padding: '6px 10px', background: 'var(--surface)' }}>
      <div className="eyebrow" style={{ fontSize: 9.5 }}>{label}</div>
      <div style={{ fontSize: 13, fontWeight: 500, color: `var(--${tone || 'ink'})`, marginTop: 2 }}>{value}</div>
      {sub && <div style={{ fontSize: 10, color: 'var(--muted)' }}>{sub}</div>}
    </div>
  );
}

function ApprovalFlow() {
  const steps = [
    { label: 'Detected', who: 'Lumen', done: true },
    { label: 'Reviewed', who: 'Maya Park', done: true },
    { label: 'Approved', who: 'CFO · J. Kowalski', done: false, current: true },
    { label: 'Apply',    who: 'auto · Terraform PR', done: false },
  ];
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      {steps.map((s, i) => (
        <div key={s.label} style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{
            width: 16, height: 16, borderRadius: 999,
            background: s.done ? 'var(--positive)' : s.current ? 'var(--surface)' : 'var(--surface)',
            border: '1.5px solid',
            borderColor: s.done ? 'var(--positive)' : s.current ? 'var(--ink)' : 'var(--border)',
            color: 'white',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 9,
          }}>
            {s.done && '✓'}
            {s.current && <span style={{ width: 6, height: 6, background: 'var(--ink)', borderRadius: 999 }} />}
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 11.5, color: s.done || s.current ? 'var(--ink)' : 'var(--muted)', fontWeight: s.current ? 500 : 400 }}>{s.label}</div>
            <div style={{ fontSize: 10.5, color: 'var(--muted)' }}>{s.who}</div>
          </div>
          {s.current && <Tag tone="info">awaiting</Tag>}
        </div>
      ))}
    </div>
  );
}

Object.assign(window, { RecommendationsScreen });
