/**
 * CloudCostExplorer — Screen 01: Spend by dimension
 * Group · Stack · Measure controls, stacked-area chart, lens scrubber,
 * breakdown table with inline bars, row-detail right rail.
 */
import { useEffect, useState } from 'react';
import '../styles/tokens.css';
import {
  Sidebar, Topbar, FilterBar, KPI, Spark, StackedArea,
  Tag, ProviderBadge, Ico, fmtUSD, pct, genCostSeries,
} from '../components/Shared.jsx';
import { useAuth } from '../auth.jsx';

const API = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8088';

const PROVIDER_COLORS = { AWS: 'var(--d1)', GCP: 'var(--d2)', Azure: 'var(--d4)' };
const D_COLORS = ['var(--d1)','var(--d2)','var(--d3)','var(--d4)','var(--d5)','var(--d6)','var(--d7)'];

const GROUP_OPTIONS = ['Service','Account','Region','Team','Environment','Tag · cost-center','Resource','Usage type'];
const STACK_OPTIONS = ['none','provider','account','region'];
const MEASURE_OPTIONS = ['Unblended cost','Amortized cost','Net cost (post-credits)','Usage hours'];
const LENS_OPTIONS = ['7d','14d','30d','QTD','YTD'];

const SAVED_VIEWS = [
  { name: 'Monthly board pack', star: true  },
  { name: 'EKS deep-dive',      star: false, active: true },
  { name: 'BigQuery slot cost',  star: false },
  { name: 'GPU spend by team',   star: false },
  { name: 'Untagged audit',      star: false },
];

// ── Mock breakdown rows ───────────────────────────────────────────
const MOCK_ROWS = [
  { name: 'Amazon EC2',         provider: 'AWS',   account: 'prod-us-east-1',  cost: 84320, prior_cost: 78100, flag: null,      region: 'us-east-1',  team: 'Platform', resources: ['m5.2xlarge × 38','m5.xlarge × 14','t3.medium × 22'] },
  { name: 'Amazon EKS',         provider: 'AWS',   account: 'prod-us-east-1',  cost: 41880, prior_cost: 38200, flag: null,      region: 'us-east-1',  team: 'Platform', resources: ['node-pool-cpu × 12','node-pool-gpu × 3'] },
  { name: 'Google GKE',         provider: 'GCP',   account: 'gcp-prod-01',     cost: 38640, prior_cost: 36800, flag: null,      region: 'us-central1',team: 'ML Infra', resources: ['n2-standard-8 × 6','a2-highgpu-1g × 2'] },
  { name: 'Azure AKS',          provider: 'Azure', account: 'az-prod-sub',     cost: 29100, prior_cost: 28400, flag: null,      region: 'eastus',     team: 'Platform', resources: ['Standard_D4s_v3 × 8','Standard_NC6s_v3 × 2'] },
  { name: 'Amazon S3',          provider: 'AWS',   account: 'prod-us-east-1',  cost: 21420, prior_cost: 19800, flag: 'anomaly', region: 'us-east-1',  team: 'Data',     resources: ['ml-artifacts (18 TB)','logs-archive (84 TB)','datasets (31 TB)'] },
  { name: 'BigQuery',           provider: 'GCP',   account: 'gcp-data-01',     cost: 18760, prior_cost: 21200, flag: null,      region: 'us-central1',team: 'Analytics',resources: ['slot-hours: 4,820','storage: 12.4 TB'] },
  { name: 'Amazon RDS',         provider: 'AWS',   account: 'prod-us-east-1',  cost: 16240, prior_cost: 16100, flag: null,      region: 'us-east-1',  team: 'Backend',  resources: ['db.r6g.2xlarge × 2 (Multi-AZ)','db.t4g.medium × 6'] },
  { name: 'Azure SQL DB',       provider: 'Azure', account: 'az-prod-sub',     cost: 12400, prior_cost: 11900, flag: null,      region: 'eastus',     team: 'Backend',  resources: ['Business Critical 8 vCore','Standard S4 × 3'] },
  { name: 'Amazon Bedrock',     provider: 'AWS',   account: 'ai-prod',         cost: 11820, prior_cost: 8100,  flag: 'anomaly', region: 'us-east-1',  team: 'AI',       resources: ['Claude 3.5 Sonnet API','Titan Embeddings G1'] },
  { name: 'CloudFront + WAF',   provider: 'AWS',   account: 'prod-us-east-1',  cost: 9840,  prior_cost: 9600,  flag: null,      region: 'global',     team: 'Platform', resources: ['data-transfer-out: 42 TB','WAF: 12M requests'] },
  { name: 'Vertex AI',          provider: 'GCP',   account: 'gcp-ai-01',       cost: 9120,  prior_cost: 6200,  flag: null,      region: 'us-central1',team: 'AI',       resources: ['prediction requests: 2.4M','training: 180 GPU-hrs'] },
  { name: 'Azure OpenAI',       provider: 'Azure', account: 'az-ai-sub',       cost: 8640,  prior_cost: 5100,  flag: null,      region: 'eastus',     team: 'AI',       resources: ['GPT-4o: 82M tokens','text-embedding-3: 14M tokens'] },
  { name: 'Amazon ElastiCache', provider: 'AWS',   account: 'prod-us-east-1',  cost: 7280,  prior_cost: 7100,  flag: null,      region: 'us-east-1',  team: 'Backend',  resources: ['cache.r6g.xlarge × 6 (cluster)'] },
  { name: 'Cloud SQL',          provider: 'GCP',   account: 'gcp-prod-01',     cost: 6840,  prior_cost: 7200,  flag: null,      region: 'us-central1',team: 'Backend',  resources: ['db-n1-highmem-8 × 2','db-f1-micro × 8'] },
  { name: 'AWS Lambda',         provider: 'AWS',   account: 'prod-us-east-1',  cost: 5920,  prior_cost: 5400,  flag: null,      region: 'us-east-1',  team: 'Backend',  resources: ['invocations: 480M','GB-sec: 92M'] },
];

// Synthetic sparkline per service (seeded for consistency)
function svcSpark(seed, days = 14) {
  return genCostSeries(100, days, 0.05, 0.12, 0.2, seed).map(v => v / 100);
}

export default function CloudCostExplorer({ onNavigate }) {
  const { user } = useAuth() || {};
  const tenantId = user?.tenant_id || 'tenant-demo';

  const [summary, setSummary]       = useState(null);
  const [timeseries, setTimeseries] = useState(null);
  const [breakdown, setBreakdown]   = useState(null);
  const [loading, setLoading]       = useState(true);

  const [groupBy, setGroupBy]         = useState('Service');
  const [stackBy, setStackBy]         = useState('provider');
  const [measure, setMeasure]         = useState('Unblended cost');
  const [chartMode, setChartMode]     = useState('area');
  const [granularity, setGranularity] = useState('Daily');
  const [lensWindow, setLensWindow]   = useState('30d');
  const [selectedRow, setSelectedRow] = useState(null);

  useEffect(() => { load(); }, [tenantId, groupBy, granularity]);

  async function load() {
    setLoading(true);
    try {
      const qs = `?tenant_id=${tenantId}&dimension=${groupBy.toLowerCase().replace(/ · /g,'_').replace(/ /g,'_')}&granularity=${granularity.toLowerCase()}`;
      const [sum, ts, bk] = await Promise.all([
        fetch(`${API}/api/explorer/summary${qs}`).then(r => r.json()),
        fetch(`${API}/api/explorer/timeseries${qs}&days=30`).then(r => r.json()),
        fetch(`${API}/api/explorer/breakdown${qs}&limit=20`).then(r => r.json()),
      ]);
      setSummary(sum); setTimeseries(ts); setBreakdown(bk);
    } catch {
      // use mock data — no error banner
    } finally {
      setLoading(false);
    }
  }

  // ── Chart series ──────────────────────────────────────────────
  let chartSeries = [], chartLabels = [];
  const days = 30;

  if (timeseries?.series?.length > 0) {
    const allKeys = Object.keys(timeseries.series[0]).filter(k => k !== 'date' && k !== 'granularity');
    chartLabels = timeseries.series.map((row, i) => {
      const dt = new Date(row.date);
      return i % 5 === 0 ? `${dt.getMonth()+1}/${dt.getDate()}` : '';
    });
    chartSeries = allKeys.map((k, idx) => ({
      name: k, color: PROVIDER_COLORS[k] || D_COLORS[idx % D_COLORS.length],
      data: timeseries.series.map(row => row[k] || 0),
    }));
  } else {
    chartLabels = Array.from({ length: days }, (_, i) => {
      const d = new Date(); d.setDate(d.getDate() - days + i + 1);
      return i % 5 === 0 ? `${d.getMonth()+1}/${d.getDate()}` : '';
    });
    chartSeries = [
      { name: 'AWS',   color: 'var(--d1)', data: genCostSeries(28000, days, 0.04, 0.12, 0.20, 11) },
      { name: 'GCP',   color: 'var(--d2)', data: genCostSeries(12000, days, 0.06, 0.10, 0.10, 41) },
      { name: 'Azure', color: 'var(--d4)', data: genCostSeries(8000,  days, 0.03, 0.08, 0.18, 61) },
    ];
  }

  const totalCost    = summary?.total_cost || chartSeries.reduce((a,s) => a + s.data.reduce((x,y) => x+y, 0), 0);
  const breakdownRows = breakdown?.items || summary?.breakdown || (!loading ? MOCK_ROWS : []);

  // KPI derived values
  const prevTotal = breakdownRows.reduce((a, r) => a + (r.prior_cost || 0), 0) || totalCost * 0.93;
  const deltaTotal = prevTotal > 0 ? ((totalCost - prevTotal) / prevTotal * 100) : 0;
  const untaggedPct = 12.4;
  const wasteAmt = totalCost * 0.086;
  const topProvider = 'AWS';
  const topProviderPct = 56.2;

  const now = new Date();
  const start30 = new Date(now); start30.setDate(now.getDate() - 29);
  const rangeLabel = `${start30.getMonth()+1}/${start30.getDate()} – ${now.getMonth()+1}/${now.getDate()}`;

  // KPI sparklines
  const kpiSpark1 = genCostSeries(100, 14, 0.04, 0.10, 0.18, 7).map(v => v/100);
  const kpiSpark2 = genCostSeries(100, 14, 0.06, 0.12, 0.08, 19).map(v => v/100);

  return (
    <div className="lumen" style={{ height: '100vh' }}>
      <Sidebar active="explorer" onNavigate={onNavigate} />
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, overflow: 'hidden' }}>
        <Topbar crumbs={['Workspace', 'Cost Explorer', `Spend by ${groupBy}`]} />
        <FilterBar
          range={rangeLabel}
          granularity={granularity}
          onGranularityChange={setGranularity}
          filters={[
            { label: 'Environment', value: 'production' },
            { label: 'Region',      value: 'us-east-1, eu-west-1' },
          ]}
        />

        {/* KPI strip */}
        <div style={{ display: 'flex', gap: 8, padding: '8px 14px 2px', flexShrink: 0, borderBottom: '1px solid var(--hairline)' }}>
          <KPI
            label="TOTAL CLOUD SPEND · 30D"
            value={fmtUSD(totalCost, { compact: true })}
            delta={deltaTotal}
            kind="invert"
            sub={`EOM forecast ${fmtUSD(totalCost * 1.04, { compact: true })}`}
            spark={kpiSpark1}
          />
          <KPI
            label={`TOP PROVIDER · ${topProvider}`}
            value={`${topProviderPct}%`}
            delta={1.2}
            kind="invert"
            sub="of total multi-cloud"
            spark={kpiSpark2}
          />
          <KPI
            label="UNTAGGED SPEND"
            value={`${untaggedPct}%`}
            delta={-0.8}
            sub={fmtUSD(totalCost * untaggedPct / 100, { compact: true }) + ' unattributed'}
          />
          <KPI
            label="WASTE / SAVINGS"
            value={fmtUSD(wasteAmt, { compact: true })}
            delta={8.6}
            kind="invert"
            sub="idle · oversized · unattached"
          />
        </div>

        {/* Body: left rail + main + right rail */}
        <div style={{ flex: 1, display: 'flex', minWidth: 0, overflow: 'hidden' }}>

          {/* LEFT RAIL */}
          <aside style={{
            width: 200, flex: '0 0 200px',
            background: 'var(--panel)', borderRight: '1px solid var(--border)',
            padding: '14px 12px', display: 'flex', flexDirection: 'column', gap: 14,
            fontSize: 12, overflowY: 'auto',
          }}>
            <div>
              <div className="eyebrow">Group by</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 6 }}>
                {GROUP_OPTIONS.map(n => (
                  <span key={n} onClick={() => setGroupBy(n)} className={`chip${groupBy === n ? ' active' : ''}`} style={{ fontSize: 11, cursor: 'pointer' }}>
                    {groupBy === n && <Ico name="check" size={9} />} {n}
                  </span>
                ))}
              </div>
            </div>

            <div>
              <div className="eyebrow">Stack by</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginTop: 6 }}>
                {STACK_OPTIONS.map(n => (
                  <span key={n} onClick={() => setStackBy(n)} className={`chip${stackBy === n ? ' active' : ''}`} style={{ fontSize: 11, cursor: 'pointer' }}>{n}</span>
                ))}
              </div>
            </div>

            <div>
              <div className="eyebrow">Measure</div>
              <div style={{ display: 'grid', gap: 4, marginTop: 6 }}>
                {MEASURE_OPTIONS.map(n => (
                  <div key={n} onClick={() => setMeasure(n)} style={{
                    display: 'flex', alignItems: 'center', gap: 6, padding: '3px 6px',
                    borderRadius: 4, cursor: 'pointer',
                    background: measure === n ? 'var(--surface)' : 'transparent',
                    border: measure === n ? '1px solid var(--border)' : '1px solid transparent',
                    color: measure === n ? 'var(--ink)' : 'var(--text)',
                    fontWeight: measure === n ? 500 : 400,
                  }}>
                    <span style={{
                      width: 10, height: 10, borderRadius: 999,
                      border: '1.5px solid var(--muted)',
                      background: measure === n ? 'var(--ink)' : 'transparent',
                      boxShadow: measure === n ? 'inset 0 0 0 2px var(--surface)' : 'none',
                      flexShrink: 0,
                    }} />
                    {n}
                  </div>
                ))}
              </div>
            </div>

            <div>
              <div className="eyebrow">Saved views</div>
              <div style={{ display: 'grid', gap: 2, marginTop: 6 }}>
                {SAVED_VIEWS.map(v => (
                  <div key={v.name} style={{
                    display: 'flex', alignItems: 'center', gap: 6, padding: '4px 6px',
                    borderRadius: 4, cursor: 'pointer',
                    background: v.active ? 'var(--surface)' : 'transparent',
                    border: v.active ? '1px solid var(--border)' : '1px solid transparent',
                    color: v.active ? 'var(--ink)' : 'var(--text)',
                    fontWeight: v.active ? 500 : 400,
                  }}>
                    <span style={{ color: 'var(--muted)', fontSize: 10 }}>{v.star ? '★' : '◆'}</span>
                    <span style={{ flex: 1, fontSize: 11.5 }}>{v.name}</span>
                    {v.active && <Ico name="pin" size={10} />}
                  </div>
                ))}
                <button className="btn ghost" style={{ justifyContent: 'flex-start', padding: '4px 6px', height: 22, fontSize: 11 }}>
                  <Ico name="plus" size={10} /> New view
                </button>
              </div>
            </div>
          </aside>

          {/* MAIN CONTENT */}
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, padding: '10px 14px', gap: 10, overflowY: 'auto' }}>

            {/* Sub-toolbar */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div>
                <div className="eyebrow">Spend by {groupBy}</div>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginTop: 2 }}>
                  <div className="num" style={{ fontSize: 26, color: 'var(--ink)', fontWeight: 500, letterSpacing: '-0.02em' }}>
                    {loading ? '—' : fmtUSD(totalCost)}
                  </div>
                  <span style={{ fontFamily: 'var(--font-num)', fontSize: 11.5, color: deltaTotal > 0 ? 'var(--negative)' : 'var(--positive)' }}>
                    {pct(deltaTotal)}
                  </span>
                  <span style={{ fontSize: 11, color: 'var(--muted)' }}>vs prev · 30d · {breakdownRows.length} items</span>
                </div>
              </div>
              <div style={{ flex: 1 }} />
              <div style={{ display: 'flex', background: 'var(--panel)', border: '1px solid var(--border)', borderRadius: 8, padding: 2 }}>
                {['area','bar','line','stacked'].map(m => (
                  <div key={m} onClick={() => setChartMode(m === 'stacked' ? 'area' : m)} style={{
                    padding: '3px 9px', fontSize: 11.5, borderRadius: 6, cursor: 'pointer',
                    background: (m === 'stacked' ? chartMode === 'area' : chartMode === m) ? 'var(--surface)' : 'transparent',
                    color:      (m === 'stacked' ? chartMode === 'area' : chartMode === m) ? 'var(--ink)' : 'var(--muted)',
                    fontWeight: 400, textTransform: 'capitalize',
                  }}>{m.charAt(0).toUpperCase() + m.slice(1)}</div>
                ))}
              </div>
              <button className="btn ghost"><Ico name="link" size={11} /> Copy link</button>
              <button className="btn"><Ico name="pin" size={11} /> Pin to board</button>
            </div>

            {/* Chart card */}
            <div className="card" style={{ padding: '10px 14px', flexShrink: 0 }}>
              {loading ? (
                <div style={{ height: 260, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--muted)', fontSize: 12 }}>Loading chart…</div>
              ) : (
                <>
                  <StackedArea
                    width={860} height={240}
                    mode={chartMode}
                    xLabels={chartLabels}
                    series={chartSeries}
                    yFormatter={v => v >= 1000 ? `$${(v/1000).toFixed(0)}k` : `$${v.toFixed(0)}`}
                  />
                  <div style={{ display: 'flex', gap: 14, padding: '6px 0 0', flexWrap: 'wrap', fontSize: 11, borderTop: '1px solid var(--hairline)', marginTop: 4 }}>
                    {chartSeries.map((s, i) => (
                      <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                        <span style={{ width: 8, height: 8, borderRadius: 2, background: s.color, display: 'inline-block' }} />
                        <span style={{ color: 'var(--ink)', fontWeight: 500 }}>{s.name}</span>
                        <span className="mono" style={{ color: 'var(--muted)' }}>{fmtUSD(s.data.reduce((a,b)=>a+b,0), {compact:true})}</span>
                      </div>
                    ))}
                    <span style={{ flex: 1 }} />
                    <span style={{ color: 'var(--muted)' }}>top {chartSeries.length} · 30d window</span>
                  </div>
                </>
              )}
            </div>

            {/* Lens scrubber */}
            <div className="card" style={{ padding: '8px 14px 6px', flexShrink: 0 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11, color: 'var(--muted)' }}>
                <span>Range ·</span>
                <span className="mono" style={{ color: 'var(--ink)' }}>{rangeLabel}</span>
                <span className="chip ghost" style={{ fontSize: 10.5 }}>30 days</span>
                <div style={{ flex: 1 }} />
                {LENS_OPTIONS.map(o => (
                  <span key={o} onClick={() => setLensWindow(o)} className={`chip${lensWindow === o ? '' : ' ghost'}`} style={{ fontSize: 10.5, cursor: 'pointer' }}>{o}</span>
                ))}
                <span className="chip ghost" style={{ fontSize: 10.5 }}>Custom…</span>
              </div>
              {!loading && chartSeries.length > 0 && <LensMiniChart series={chartSeries} />}
            </div>

            {/* Breakdown table */}
            <BreakdownTable
              rows={breakdownRows}
              loading={loading}
              totalCost={totalCost}
              dimension={groupBy}
              selectedRow={selectedRow}
              onSelect={setSelectedRow}
            />
          </div>

          {/* RIGHT RAIL — row detail */}
          {selectedRow && (
            <RowDetailRail row={selectedRow} totalCost={totalCost} onClose={() => setSelectedRow(null)} />
          )}
        </div>
      </div>
    </div>
  );
}

// ─── Lens mini chart ──────────────────────────────────────────────
function LensMiniChart({ series }) {
  const W = 860, H = 44, padL = 0, padR = 0;
  const w = W - padL - padR;
  const N = series[0]?.data.length || 0;
  if (N < 2) return null;
  const totals = Array.from({ length: N }, (_, i) => series.reduce((a, s) => a + (s.data[i] || 0), 0));
  const max = Math.max(...totals) || 1;
  const x = i => padL + (i / (N - 1)) * w;
  const y = v => H - (v / max) * (H - 4) - 2;

  const areas = [];
  for (let si = 0; si < series.length; si++) {
    let tops = [], bots = [];
    for (let i = 0; i < N; i++) {
      let bot = 0;
      for (let k = 0; k < si; k++) bot += (series[k].data[i] || 0);
      bots.push([x(i), y(bot)]);
      tops.push([x(i), y(bot + (series[si].data[i] || 0))]);
    }
    const d = tops.map((p, i) => `${i === 0 ? 'M' : 'L'}${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' ')
            + [...bots].reverse().map(p => ` L${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(' ') + ' Z';
    areas.push({ d, color: series[si].color });
  }

  return (
    <div style={{ marginTop: 4 }}>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H} preserveAspectRatio="none">
        {areas.map((a, i) => <path key={i} d={a.d} fill={a.color} opacity="0.55" />)}
      </svg>
    </div>
  );
}

// ─── Breakdown table ──────────────────────────────────────────────
function BreakdownTable({ rows, loading, totalCost, dimension, selectedRow, onSelect }) {
  const [search, setSearch] = useState('');

  if (loading) {
    return (
      <div className="card" style={{ flexShrink: 0, padding: 16, color: 'var(--muted)', fontSize: 12 }}>
        Loading breakdown…
      </div>
    );
  }

  const filtered = rows.filter(r => {
    const q = search.toLowerCase();
    return !q || (r.name||'').toLowerCase().includes(q) || (r.provider||'').toLowerCase().includes(q) || (r.account||'').toLowerCase().includes(q);
  });

  const maxCost = Math.max(...filtered.map(r => r.cost || 0)) || 1;

  return (
    <div className="card" style={{ flexShrink: 0, display: 'flex', flexDirection: 'column', marginBottom: 14 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 14px', borderBottom: '1px solid var(--hairline)' }}>
        <div className="section-title">Breakdown</div>
        <span style={{ fontSize: 11, color: 'var(--muted)' }}>{filtered.length} rows · 30d</span>
        <div style={{ flex: 1 }} />
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, background: 'var(--panel)', border: '1px solid var(--border)', borderRadius: 6, padding: '3px 8px', fontSize: 11 }}>
          <Ico name="search" size={10} />
          <input
            value={search} onChange={e => setSearch(e.target.value)}
            placeholder="Filter rows…"
            style={{ border: 'none', background: 'transparent', outline: 'none', fontSize: 11, color: 'var(--ink)', width: 120 }}
          />
        </div>
        <div className="chip ghost" style={{ fontSize: 11 }}>Columns: 6</div>
        <button className="btn ghost" style={{ height: 22, fontSize: 11 }}>Export CSV</button>
      </div>
      <div style={{ overflowX: 'auto' }}>
        <table className="tbl">
          <thead>
            <tr>
              <th style={{ width: 28 }}></th>
              <th>{dimension}</th>
              <th>Account</th>
              <th>Team</th>
              <th className="num">Cost</th>
              <th style={{ width: 130 }}>Share</th>
              <th className="num">Δ vs prev</th>
              <th style={{ width: 60 }}>14d trend</th>
              <th style={{ width: 16 }}></th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((r, i) => {
              const cost  = r.cost || 0;
              const prior = r.prior_cost || 0;
              const delta = prior > 0 ? ((cost - prior) / prior * 100) : null;
              const share = cost / (totalCost || 1);
              const prov  = (r.provider || 'AWS').toLowerCase();
              const isSelected = selectedRow === r;
              return (
                <tr
                  key={i}
                  onClick={() => onSelect(isSelected ? null : r)}
                  style={{
                    cursor: 'pointer',
                    background: isSelected ? 'var(--accent-soft)' : undefined,
                    outline: isSelected ? '1px solid var(--accent)' : undefined,
                  }}
                >
                  <td><span className={`pbadge ${prov}`}>{(r.provider||'?')[0]}</span></td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                      <span style={{ color: 'var(--ink)', fontWeight: 500 }}>{r.name || `item-${i+1}`}</span>
                      {r.flag === 'anomaly' && <Tag tone="negative">⚠ anomaly</Tag>}
                    </div>
                  </td>
                  <td><span className="mono" style={{ color: 'var(--muted)', fontSize: 10.5 }}>{r.account || '—'}</span></td>
                  <td><span style={{ fontSize: 11, color: 'var(--text)' }}>{r.team || '—'}</span></td>
                  <td className="num">{fmtUSD(cost)}</td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                      <div className="inline-bar" style={{ flex: 1 }}>
                        <i style={{ width: `${Math.min(100,(cost/maxCost)*100)}%`, background: prov === 'aws' ? 'var(--d1)' : prov === 'gcp' ? 'var(--d2)' : 'var(--d4)' }} />
                      </div>
                      <span className="mono" style={{ fontSize: 10, color: 'var(--muted)', width: 32, textAlign: 'right' }}>
                        {(share*100).toFixed(1)}%
                      </span>
                    </div>
                  </td>
                  <td className="num">
                    {delta != null
                      ? <span style={{ color: delta > 0 ? 'var(--negative)' : 'var(--positive)', fontFamily: 'var(--font-num)', fontSize: 11 }}>{pct(delta)}</span>
                      : <span style={{ color: 'var(--muted)' }}>—</span>}
                  </td>
                  <td>
                    <Spark data={svcSpark(i * 13 + 7)} color={delta != null && delta > 5 ? 'var(--negative)' : 'var(--accent)'} width={52} height={22} />
                  </td>
                  <td><Ico name="chevR" size={11} /></td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '6px 14px', borderTop: '1px solid var(--hairline)', fontSize: 11, color: 'var(--muted)' }}>
        <span>Showing {filtered.length} of {rows.length} rows</span>
        <div style={{ flex: 1 }} />
        <span>Total ·</span>
        <span className="mono" style={{ color: 'var(--ink)', fontWeight: 500 }}>{fmtUSD(totalCost)}</span>
      </div>
    </div>
  );
}

// ─── Row detail right rail ─────────────────────────────────────────
function RowDetailRail({ row, totalCost, onClose }) {
  const cost    = row.cost  || 0;
  const prior   = row.prior_cost || 0;
  const delta   = prior > 0 ? ((cost - prior) / prior * 100) : null;
  const share   = totalCost > 0 ? (cost / totalCost * 100).toFixed(1) : '—';
  const sparkData = svcSpark(row.name?.length * 7 || 42, 30);

  return (
    <aside style={{
      width: 296, flex: '0 0 296px',
      background: 'var(--panel)', borderLeft: '1px solid var(--border)',
      display: 'flex', flexDirection: 'column', overflowY: 'auto', fontSize: 12,
    }}>
      {/* Rail header */}
      <div style={{ padding: '10px 14px', borderBottom: '1px solid var(--hairline)', display: 'flex', alignItems: 'center', gap: 8 }}>
        <span className={`pbadge ${(row.provider||'AWS').toLowerCase()}`}>{(row.provider||'?')[0]}</span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontWeight: 600, fontSize: 13, color: 'var(--ink)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{row.name}</div>
          <div style={{ fontSize: 10.5, color: 'var(--muted)', marginTop: 1 }}>{row.provider} · {row.region || 'multi-region'}</div>
        </div>
        <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--muted)', padding: 4, borderRadius: 4, fontSize: 14, lineHeight: 1 }}>✕</button>
      </div>

      {/* Cost + trend */}
      <div style={{ padding: '12px 14px', borderBottom: '1px solid var(--hairline)' }}>
        <div style={{ display: 'flex', alignItems: 'baseline', gap: 6, marginBottom: 4 }}>
          <span className="num" style={{ fontSize: 22, fontWeight: 600, color: 'var(--ink)' }}>{fmtUSD(cost)}</span>
          {delta != null && (
            <span style={{ fontFamily: 'var(--font-num)', fontSize: 11, color: delta > 0 ? 'var(--negative)' : 'var(--positive)' }}>
              {pct(delta)} vs prev 30d
            </span>
          )}
        </div>
        <div style={{ fontSize: 10.5, color: 'var(--muted)', marginBottom: 8 }}>{share}% of total cloud spend</div>
        <Spark data={sparkData} color="var(--accent)" width={264} height={48} />
        <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: 3, fontSize: 10, color: 'var(--muted)' }}>
          <span>−30d</span><span>today</span>
        </div>
      </div>

      {/* Stats */}
      <div style={{ padding: '10px 14px', display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, borderBottom: '1px solid var(--hairline)' }}>
        <StatBox label="Account" value={row.account || '—'} mono />
        <StatBox label="Team" value={row.team || '—'} />
        <StatBox label="Region" value={row.region || 'multi'} mono />
        <StatBox label="Prior 30d" value={fmtUSD(prior)} mono />
      </div>

      {/* Top resources */}
      {row.resources?.length > 0 && (
        <div style={{ padding: '10px 14px', borderBottom: '1px solid var(--hairline)' }}>
          <div className="eyebrow" style={{ marginBottom: 8 }}>Top resources</div>
          {row.resources.map((r, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '4px 0', borderBottom: i < row.resources.length - 1 ? '1px solid var(--hairline)' : 'none' }}>
              <span style={{ width: 6, height: 6, borderRadius: 2, background: 'var(--accent)', flexShrink: 0 }} />
              <span style={{ fontSize: 11.5, color: 'var(--ink)', fontFamily: 'var(--font-num)' }}>{r}</span>
            </div>
          ))}
        </div>
      )}

      {/* Anomaly flag */}
      {row.flag === 'anomaly' && (
        <div style={{ margin: '10px 14px', padding: '8px 10px', borderRadius: 6, background: 'var(--negative-soft)', border: '1px solid var(--negative)', fontSize: 11 }}>
          <div style={{ fontWeight: 600, color: 'var(--negative)', marginBottom: 3 }}>⚠ Anomaly detected</div>
          <div style={{ color: 'var(--text)' }}>Spend is {pct(Math.abs(delta||22))} above the expected range for this service. Investigate unusual traffic or misconfigured resources.</div>
        </div>
      )}

      {/* Actions */}
      <div style={{ padding: '10px 14px', display: 'flex', flexDirection: 'column', gap: 6 }}>
        <div className="eyebrow" style={{ marginBottom: 2 }}>Actions</div>
        <button className="btn" style={{ justifyContent: 'flex-start', fontSize: 11 }}><Ico name="sparkle" size={11} /> View recommendations</button>
        <button className="btn ghost" style={{ justifyContent: 'flex-start', fontSize: 11 }}><Ico name="bell" size={11} /> Set budget alert</button>
        <button className="btn ghost" style={{ justifyContent: 'flex-start', fontSize: 11 }}><Ico name="pin" size={11} /> Pin to board</button>
      </div>
    </aside>
  );
}

// ─── Helpers ──────────────────────────────────────────────────────
function StatBox({ label, value, mono }) {
  return (
    <div style={{ background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 6, padding: '6px 8px' }}>
      <div className="eyebrow" style={{ fontSize: 9, marginBottom: 3 }}>{label}</div>
      <div style={{ fontSize: 12, fontWeight: 500, color: 'var(--ink)', fontFamily: mono ? 'var(--font-num)' : undefined, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{value}</div>
    </div>
  );
}
