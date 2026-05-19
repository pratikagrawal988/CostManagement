/* global React, Sidebar, Topbar, FilterBar, KPI, Spark, StackedArea, Ico, Tag, ProviderBadge, fmtUSD, pct, genCostSeries, Avatar */

// ─────────────────────────────────────────────────────────────────
// Screen 7 — AI Cost
// Third-party AI vendors + cloud GPU spend, in one view.
// Token economics, prompt-cache impact, model routing suggestions.
// ─────────────────────────────────────────────────────────────────

// Vendor letter-badges — original color palette, NOT brand mark copies.
const VENDORS = {
  anthropic:   { label: 'A',  full: 'Anthropic',     color: 'oklch(0.68 0.13 50)',  fg: '#fff' },
  openai:      { label: 'O',  full: 'OpenAI',        color: 'oklch(0.22 0.005 250)', fg: '#fff' },
  cursor:      { label: 'C',  full: 'Cursor',        color: 'oklch(0.32 0.02 280)',  fg: '#fff' },
  cohere:      { label: 'Co', full: 'Cohere',        color: 'oklch(0.65 0.13 230)',  fg: '#fff' },
  mistral:     { label: 'M',  full: 'Mistral',       color: 'oklch(0.7 0.16 50)',   fg: '#fff' },
  eleven:      { label: '11', full: 'ElevenLabs',    color: 'oklch(0.48 0.005 270)', fg: '#fff' },
  hf:          { label: 'HF', full: 'Hugging Face',  color: 'oklch(0.75 0.14 78)',   fg: 'oklch(0.25 0.05 70)' },
  pinecone:    { label: 'P',  full: 'Pinecone',      color: 'oklch(0.6 0.13 150)',   fg: '#fff' },
  replicate:   { label: 'R',  full: 'Replicate',     color: 'oklch(0.65 0.13 350)',  fg: '#fff' },
  bedrock:     { label: 'B',  full: 'AWS Bedrock',   color: 'oklch(0.66 0.14 55)',   fg: '#fff' },
  vertex:      { label: 'V',  full: 'GCP Vertex',    color: 'oklch(0.6 0.13 245)',   fg: '#fff' },
  azureoai:    { label: 'Z',  full: 'Azure OpenAI',  color: 'oklch(0.6 0.10 215)',   fg: '#fff' },
  github:      { label: 'G',  full: 'GitHub Copilot',color: 'oklch(0.32 0.005 270)', fg: '#fff' },
  perplex:     { label: 'Px', full: 'Perplexity',    color: 'oklch(0.62 0.10 200)',  fg: '#fff' },
};
function VBadge({ v, size = 18 }) {
  const d = VENDORS[v] || { label: '?', color: 'var(--muted)', fg: '#fff' };
  return (
    <span style={{
      width: size, height: size, borderRadius: 4,
      background: d.color, color: d.fg,
      display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
      fontFamily: 'var(--font-num)', fontSize: size * 0.5,
      fontWeight: 600, letterSpacing: '-0.04em', flex: '0 0 auto',
    }}>{d.label}</span>
  );
}

function AIScreen({ chartMode = 'area' }) {
  const days = 14;
  const anth = genCostSeries(4200, days, 0.18, 0.16, 0.10, 13);
  const oai  = genCostSeries(3200, days, 0.10, 0.14, 0.10, 17);
  const curs = genCostSeries(1200, days, 0.02, 0.06, 0.30, 19);
  const gpu  = genCostSeries(5800, days, 0.06, 0.12, 0.15, 23);
  const tools= genCostSeries( 800, days, 0.04, 0.10, 0.10, 29);
  const labels = Array.from({ length: days }, (_, i) => String(i + 1).padStart(2, '0'));

  return (
    <div className="lumen">
      <Sidebar active="ai" />
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0 }}>
        <Topbar crumbs={['Acme Inc.', 'AI cost']} asMonth="May 2026" />
        <FilterBar
          range="May 1 – 14, 2026"
          granularity="Daily"
          filters={[
            { label: 'Workload', value: 'inference + training + seats' },
            { label: 'App', value: 'all 14' },
            { label: 'Model family', value: 'all' },
          ]}
        />

        <div style={{ flex: 1, display: 'flex', minWidth: 0, overflow: 'hidden' }}>
          {/* MAIN */}
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minWidth: 0, padding: '14px 14px 0', gap: 12, overflow: 'hidden' }}>
            {/* Hero header */}
            <div style={{ display: 'flex', alignItems: 'flex-end', gap: 14 }}>
              <div>
                <div className="eyebrow">AI spend · third-party + cloud GPU</div>
                <div style={{ display: 'flex', alignItems: 'baseline', gap: 12, marginTop: 2 }}>
                  <h1 className="display" style={{ margin: 0, fontSize: 32, color: 'var(--ink)', lineHeight: 1 }}>
                    the AI bill
                  </h1>
                  <span style={{ fontSize: 12, color: 'var(--muted)' }}>9 vendors · 24 models · 14 apps · 142 seats</span>
                </div>
              </div>
              <div style={{ flex: 1 }} />
              <div style={{ display: 'flex', background: 'var(--panel)', border: '1px solid var(--border)', borderRadius: 8, padding: 2 }}>
                {['Spend', 'Tokens', 'Calls', 'Seats'].map((m, i) => (
                  <div key={m} style={{
                    padding: '4px 10px', fontSize: 11.5, borderRadius: 6,
                    background: i === 0 ? 'var(--surface)' : 'transparent',
                    color: i === 0 ? 'var(--ink)' : 'var(--muted)',
                    fontWeight: i === 0 ? 500 : 400,
                  }}>{m}</div>
                ))}
              </div>
            </div>

            {/* KPI strip */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 10 }}>
              <KPI label="MTD AI spend"      value="$214.8k" sub="forecast EOM $478k · ±$24k" delta={42.1} kind="invert" big
                   spark={anth.map((v,i)=>v+oai[i]+curs[i]+gpu[i]+tools[i])} />
              <KPI label="% of cloud spend"   value="14.7%"   sub="up from 9.4% in Apr"      delta={5.3} kind="invert" accent="var(--d5)" spark={[6.2,7.1,8.4,9.4,11.2,13.1,14.7]} />
              <KPI label="Tokens · 14d"       value="2.18B"   sub="74% input · 26% output"   delta={36.4} accent="var(--accent)" spark={[0.9,1.0,1.2,1.4,1.6,1.9,2.18]} />
              <KPI label="Blended $/1M tok"   value="$0.96"   sub="↓ $1.42 in Apr"           delta={-32.4} accent="var(--positive)" spark={[1.42,1.32,1.22,1.10,1.04,1.0,0.96]} />
              <KPI label="Prompt cache hit"   value="62.4%"   sub="saved $42.8k MTD"         delta={18.0} accent="var(--d2)" spark={[42,46,50,54,58,60,62.4]} />
            </div>

            {/* Spend chart + Mix split */}
            <div style={{ display: 'grid', gridTemplateColumns: '1.55fr 1fr', gap: 10 }}>
              <div className="card" style={{ padding: '12px 14px', display: 'flex', flexDirection: 'column', minHeight: 250 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 4 }}>
                  <div className="section-title">Spend by vendor · 14d</div>
                  <div style={{ flex: 1 }} />
                  <div style={{ display: 'flex', gap: 14, fontSize: 11 }}>
                    {[
                      ['Anthropic',     'var(--d4)', anth.reduce((a,b)=>a+b,0)],
                      ['OpenAI',        'var(--d1)', oai.reduce((a,b)=>a+b,0)],
                      ['Cursor seats',  'var(--d6)', curs.reduce((a,b)=>a+b,0)],
                      ['Cloud GPU',     'var(--d3)', gpu.reduce((a,b)=>a+b,0)],
                      ['Vector + tools','var(--d2)', tools.reduce((a,b)=>a+b,0)],
                    ].map(([n, c, v]) => (
                      <div key={n} style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
                        <span className="legend-dot" style={{ background: c }} />
                        <span style={{ color: 'var(--muted)' }}>{n}</span>
                        <span className="mono" style={{ color: 'var(--ink)', fontWeight: 500 }}>{fmtUSD(v, { compact: true })}</span>
                      </div>
                    ))}
                  </div>
                </div>
                <StackedArea
                  width={680} height={196}
                  mode={chartMode}
                  xLabels={labels.map((l, i) => i % 2 === 0 ? `May ${l}` : '')}
                  highlightIdx={10}
                  series={[
                    { name: 'Anthropic',     color: 'var(--d4)', data: anth },
                    { name: 'OpenAI',        color: 'var(--d1)', data: oai },
                    { name: 'Cursor seats',  color: 'var(--d6)', data: curs },
                    { name: 'Cloud GPU',     color: 'var(--d3)', data: gpu },
                    { name: 'Vector + tools',color: 'var(--d2)', data: tools },
                  ]}
                />
                <div style={{ display: 'flex', gap: 10, padding: '4px 0 0', fontSize: 11, color: 'var(--muted)', borderTop: '1px solid var(--hairline)', marginTop: 4 }}>
                  <span>Tue May 11 · launched RAG v3 · <span className="mono" style={{ color: 'var(--ink)' }}>+$28k</span> sustained</span>
                  <div style={{ flex: 1 }} />
                  <span>peak hour 16:00 UTC · weekend dip −38%</span>
                </div>
              </div>

              {/* Cost mix card */}
              <CostMixCard />
            </div>

            {/* Vendor & Model leaderboard */}
            <div className="card" style={{ flex: 1, minHeight: 0, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 14px', borderBottom: '1px solid var(--hairline)' }}>
                <div className="section-title">Vendor & model leaderboard</div>
                <span style={{ fontSize: 11, color: 'var(--muted)' }}>14d · expand for model breakdown</span>
                <div style={{ flex: 1 }} />
                <span className="chip" style={{ fontSize: 10.5 }}>by $</span>
                <span className="chip ghost" style={{ fontSize: 10.5 }}>by tokens</span>
                <span className="chip ghost" style={{ fontSize: 10.5 }}>by $/1M tok</span>
              </div>
              <div style={{ flex: 1, overflow: 'auto' }}>
                <ModelTable />
              </div>
            </div>
          </div>

          {/* RIGHT — model router + seats + insights */}
          <aside style={{
            width: 340, flex: '0 0 340px',
            background: 'var(--panel)',
            borderLeft: '1px solid var(--border)',
            padding: 14,
            display: 'flex', flexDirection: 'column', gap: 12,
            overflow: 'auto',
            fontSize: 12,
          }}>
            {/* App attribution */}
            <div>
              <div className="eyebrow" style={{ marginBottom: 6 }}>Apps · spend · cost / call</div>
              <AppList />
            </div>

            {/* Model router suggestions */}
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
                <span style={{ color: 'var(--accent)', display: 'flex' }}><Ico name="sparkles" size={12} /></span>
                <div className="eyebrow">Model router · suggested swaps</div>
                <div style={{ flex: 1 }} />
                <Tag tone="positive">save $38.4k/mo</Tag>
              </div>
              <Swap from="claude-3.5-sonnet"  fromV="anthropic" to="claude-haiku-4-5"   toV="anthropic" app="support-copilot" save="$12.4k" tone="positive" />
              <Swap from="gpt-4o"             fromV="openai"    to="gpt-4o-mini"         toV="openai"    app="doc-summarizer"   save="$8.6k"  tone="positive" />
              <Swap from="gpt-4o"             fromV="openai"    to="claude-haiku-4-5"   toV="anthropic" app="onboarding-agent" save="$6.8k"  tone="info"
                    note="benchmark · 4% quality lift" />
              <Swap from="text-embed-3-large" fromV="openai"    to="embed-v4"            toV="cohere"    app="search-rag"       save="$5.2k"  tone="positive"
                    note="1024-d · matches recall" />
              <Swap from="claude-3.5-sonnet"  fromV="anthropic" to="cached + sonnet"     toV="anthropic" app="finops-assistant" save="$5.4k"  tone="info"
                    note="enable prompt cache" />
            </div>

            {/* Cursor seats */}
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
                <VBadge v="cursor" size={14} />
                <div className="eyebrow">Cursor seats · 142 issued</div>
                <div style={{ flex: 1 }} />
                <span className="mono" style={{ fontSize: 11, color: 'var(--muted)' }}>$5.96k / mo</span>
              </div>
              <SeatHeatmap />
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 10.5, color: 'var(--muted)', marginTop: 4 }}>
                <span><span className="mono" style={{ color: 'var(--negative)' }}>18 idle ≥14d</span> · reclaim $756/mo</span>
                <span><span className="mono" style={{ color: 'var(--warning)' }}>9 over quota</span></span>
              </div>
            </div>

            <button className="btn primary" style={{ justifyContent: 'center', height: 30 }}>
              <Ico name="check" size={12} /> Apply 5 swaps · save $38.4k/mo
            </button>
          </aside>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
// Cost Mix — donut + breakdown by workload type
// ─────────────────────────────────────────────────────────────────
function CostMixCard() {
  const data = [
    { label: 'Inference',         v: 132, c: 'var(--d1)' },
    { label: 'Fine-tune / train', v:  38, c: 'var(--d4)' },
    { label: 'Eval + guardrails', v:  14, c: 'var(--d3)' },
    { label: 'Dev tools (seats)', v:  18, c: 'var(--d6)' },
    { label: 'Vector + storage',  v:  12, c: 'var(--d2)' },
  ];
  const total = data.reduce((a, b) => a + b.v, 0);
  // donut
  const R = 52, r = 32, cx = 60, cy = 60;
  let acc = 0;
  const segs = data.map((d) => {
    const start = acc / total * Math.PI * 2 - Math.PI / 2;
    acc += d.v;
    const end = acc / total * Math.PI * 2 - Math.PI / 2;
    const large = end - start > Math.PI ? 1 : 0;
    const x0 = cx + R * Math.cos(start), y0 = cy + R * Math.sin(start);
    const x1 = cx + R * Math.cos(end),   y1 = cy + R * Math.sin(end);
    const xi0 = cx + r * Math.cos(end),  yi0 = cy + r * Math.sin(end);
    const xi1 = cx + r * Math.cos(start),yi1 = cy + r * Math.sin(start);
    const path = `M${x0},${y0} A${R},${R} 0 ${large} 1 ${x1},${y1} L${xi0},${yi0} A${r},${r} 0 ${large} 0 ${xi1},${yi1} Z`;
    return { d, path };
  });
  return (
    <div className="card" style={{ padding: '12px 14px', display: 'flex', flexDirection: 'column' }}>
      <div className="section-title">Mix · by workload</div>
      <div style={{ display: 'flex', gap: 14, alignItems: 'center', marginTop: 6 }}>
        <svg viewBox="0 0 120 120" width="120" height="120" style={{ flex: '0 0 120px' }}>
          {segs.map((s, i) => <path key={i} d={s.path} fill={s.d.c} opacity="0.92" />)}
          <text x="60" y="56" textAnchor="middle" fontSize="9.5" fill="var(--muted)" fontFamily="var(--font-num)" style={{ textTransform: 'uppercase', letterSpacing: '0.1em' }}>14d</text>
          <text x="60" y="72" textAnchor="middle" fontSize="16" fill="var(--ink)" fontWeight="600" fontFamily="var(--font-num)">${total}k</text>
        </svg>
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 3 }}>
          {data.map((d) => (
            <div key={d.label} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11.5 }}>
              <span className="legend-dot" style={{ background: d.c, width: 7, height: 7 }} />
              <span style={{ color: 'var(--ink)', flex: 1 }}>{d.label}</span>
              <span className="mono" style={{ color: 'var(--ink)', fontWeight: 500 }}>${d.v}k</span>
              <span className="mono" style={{ color: 'var(--muted)', width: 36, textAlign: 'right', fontSize: 10 }}>{((d.v / total) * 100).toFixed(0)}%</span>
            </div>
          ))}
        </div>
      </div>
      <div style={{ display: 'flex', gap: 6, marginTop: 8, padding: '6px 8px', background: 'var(--positive-soft)', borderRadius: 6 }}>
        <span style={{ color: 'var(--positive)', display: 'flex' }}><Ico name="check" size={12} /></span>
        <div style={{ fontSize: 11, color: 'var(--positive)', lineHeight: 1.4 }}>
          <b>Prompt cache</b> reduced input tokens 51% on Claude.<br/>
          <span style={{ color: 'var(--text)' }}>Saved <span className="mono" style={{ fontWeight: 500 }}>$42.8k</span> MTD · projected <span className="mono" style={{ fontWeight: 500 }}>$94k</span> EOM.</span>
        </div>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
// Model leaderboard table — vendors + models with $/1M tokens
// ─────────────────────────────────────────────────────────────────
function ModelTable() {
  const rows = [
    // Anthropic
    { vendor: 'anthropic', model: 'claude-3.5-sonnet',  v: 28420, tok: '142M',  cost1M: 11.20, share: 0.132, t: [.7,.8,.9,1.0,1.1,1.2,1.3,1.32,1.4,1.42,1.5,1.55,1.6,1.62], app: 'support-copilot · finops · 8 more', tag: 'flagship' },
    { vendor: 'anthropic', model: 'claude-haiku-4-5',   v: 18240, tok: '512M',  cost1M:  1.20, share: 0.084, t: [.4,.5,.6,.7,.8,.9,1.0,1.1,1.2,1.32,1.4,1.5,1.6,1.7], app: 'finops-assistant · code-review · 5 more', tag: 'workhorse' },
    { vendor: 'anthropic', model: 'claude-3-opus',      v:  6420, tok:  '12M',  cost1M: 38.80, share: 0.029, t: [1.0,.95,.9,.92,.95,1.0,.98,.96,.94,.92,.9,.88,.86,.84], app: 'analytics-nl · doc-summarizer' },
    // OpenAI
    { vendor: 'openai',    model: 'gpt-4o',             v: 21680, tok:  '98M',  cost1M:  9.40, share: 0.101, t: [.9,.95,1.0,1.05,1.1,1.12,1.15,1.18,1.2,1.22,1.25,1.28,1.3,1.32], app: 'doc-summarizer · onboarding · 4 more' },
    { vendor: 'openai',    model: 'gpt-4o-mini',        v:  9420, tok: '348M',  cost1M:  0.62, share: 0.044, t: [.6,.65,.7,.78,.85,.92,1.0,1.05,1.1,1.15,1.2,1.25,1.3,1.34], app: 'low-latency apps · 6 more' },
    { vendor: 'openai',    model: 'o3-mini',            v: 12640, tok:  '34M',  cost1M: 22.40, share: 0.059, t: [.3,.4,.5,.6,.7,.8,.9,1.0,1.1,1.2,1.3,1.4,1.5,1.6], app: 'planner · search-rag', tag: 'reasoning' },
    { vendor: 'openai',    model: 'text-embedding-3',   v:  3820, tok: '1.4B',  cost1M:  0.13, share: 0.018, t: [.7,.8,.85,.9,.92,.94,.96,.98,1.0,1.02,1.04,1.06,1.08,1.10], app: 'search-rag · doc-index' },
    // Cohere
    { vendor: 'cohere',    model: 'rerank-3',           v:  2820, tok:   '—',  cost1M:  '—',   share: 0.013, t: [.8,.85,.88,.9,.92,.94,.96,.98,1.0,1.02,1.04,1.06,1.08,1.10], app: 'search-rag', tag: 'per-call' },
    { vendor: 'cohere',    model: 'embed-v4',           v:  1640, tok: '820M',  cost1M:  0.12, share: 0.008, t: [.4,.5,.6,.7,.8,.85,.9,.95,1.0,1.04,1.08,1.12,1.16,1.2], app: 'eval pilot' },
    // Mistral
    { vendor: 'mistral',   model: 'mistral-large-2',    v:  4820, tok:  '38M',  cost1M:  6.40, share: 0.022, t: [.6,.7,.8,.85,.9,.92,.94,.96,.98,1.0,1.02,1.04,1.06,1.08], app: 'EU-region failover' },
    { vendor: 'mistral',   model: 'codestral',          v:  2240, tok:  '64M',  cost1M:  3.20, share: 0.010, t: [.5,.6,.7,.78,.85,.9,.94,.98,1.0,1.04,1.08,1.12,1.16,1.2], app: 'code-review-bot' },
    // Cursor (per-seat, not per-token)
    { vendor: 'cursor',    model: 'cursor · pro seats',  v: 5960, tok:   '—',  cost1M: '—',    share: 0.028, t: [.95,.96,.97,.98,.99,1.0,1.0,1.0,1.01,1.02,1.02,1.03,1.03,1.04], app: '142 devs · 124 active', tag: 'per-seat' },
    // Cloud GPU (bedrock + vertex + raw)
    { vendor: 'bedrock',   model: 'llama-3-70b · on-demand', v: 6420, tok: '184M', cost1M: 2.80, share: 0.030, t: [.7,.75,.8,.85,.88,.92,.95,.98,1.0,1.04,1.08,1.12,1.16,1.2], app: 'eval · privacy region' },
    { vendor: 'vertex',    model: 'gemini-1.5-pro',        v: 3820, tok: '24M',  cost1M: 7.20, share: 0.018, t: [.4,.5,.6,.65,.7,.75,.8,.85,.9,.95,1.0,1.04,1.08,1.12], app: 'analytics-nl pilot' },
    { vendor: 'azureoai',  model: 'gpt-4o · az-deploy',     v: 5840, tok: '32M',  cost1M: 9.40, share: 0.027, t: [.8,.82,.84,.86,.88,.9,.92,.94,.96,.98,1.0,1.02,1.04,1.06], app: 'enterprise SLA region', tag: 'EU + SOC2' },
    // Vector + tools
    { vendor: 'pinecone',  model: 'serverless · 8 indices', v: 2840, tok: '—',   cost1M: '—',  share: 0.013, t: [.85,.86,.87,.88,.89,.9,.91,.92,.93,.94,.95,.96,.97,.98], app: 'search-rag indices', tag: 'storage+read' },
    { vendor: 'replicate', model: 'flux-pro · img-gen',     v: 1640, tok: '—',   cost1M: '—',  share: 0.008, t: [.4,.5,.6,.65,.7,.75,.8,.85,.9,.95,1.0,1.05,1.1,1.15], app: 'marketing-gen', tag: 'per-image' },
    { vendor: 'eleven',    model: 'tts · multilingual-v2',  v:  640, tok: '—',   cost1M: '—',  share: 0.003, t: [.5,.6,.7,.78,.85,.9,.94,.98,1.0,1.02,1.04,1.06,1.08,1.1], app: 'support voicebot', tag: 'per-char' },
  ];

  return (
    <table className="tbl">
      <thead>
        <tr>
          <th style={{ width: 32 }}></th>
          <th>Vendor / Model</th>
          <th>Apps using</th>
          <th className="num">Spend · 14d</th>
          <th style={{ width: 110 }}>Share</th>
          <th className="num">Tokens</th>
          <th className="num">$ / 1M tok</th>
          <th style={{ width: 88 }}>14d trend</th>
          <th style={{ width: 20 }}></th>
        </tr>
      </thead>
      <tbody>
        {rows.map((r, i) => {
          const cost1MStr = typeof r.cost1M === 'number' ? `$${r.cost1M.toFixed(2)}` : r.cost1M;
          const efficient = typeof r.cost1M === 'number' && r.cost1M < 2;
          const expensive = typeof r.cost1M === 'number' && r.cost1M > 15;
          return (
            <tr key={i}>
              <td><VBadge v={r.vendor} /></td>
              <td>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span className="mono" style={{ color: 'var(--ink)', fontWeight: 500, fontSize: 11.5 }}>{r.model}</span>
                  {r.tag && <Tag tone={r.tag === 'flagship' ? 'info' : r.tag === 'reasoning' ? 'warning' : 'neutral'}>{r.tag}</Tag>}
                </div>
                <div style={{ fontSize: 10.5, color: 'var(--muted)' }}>{VENDORS[r.vendor]?.full}</div>
              </td>
              <td><span style={{ fontSize: 11, color: 'var(--text)' }}>{r.app}</span></td>
              <td className="num">{fmtUSD(r.v)}</td>
              <td>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <div className="inline-bar" style={{ flex: 1 }}><i style={{ width: `${(r.share * 100) / 0.14 * 100}%`, background: VENDORS[r.vendor]?.color || 'var(--accent)' }} /></div>
                  <span className="mono" style={{ fontSize: 10.5, color: 'var(--muted)', width: 32, textAlign: 'right' }}>{(r.share * 100).toFixed(1)}%</span>
                </div>
              </td>
              <td className="num"><span style={{ color: 'var(--muted)' }}>{r.tok}</span></td>
              <td className="num">
                <span style={{ color: efficient ? 'var(--positive)' : expensive ? 'var(--negative)' : 'var(--ink)', fontWeight: efficient || expensive ? 500 : 400 }}>
                  {cost1MStr}
                </span>
              </td>
              <td><div style={{ width: 84, height: 18 }}><Spark data={r.t} color={VENDORS[r.vendor]?.color || 'var(--accent)'} height={18} showDot={false} /></div></td>
              <td><Ico name="chevR" size={11} /></td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

// ─────────────────────────────────────────────────────────────────
// Apps list — right-rail attribution
// ─────────────────────────────────────────────────────────────────
function AppList() {
  const apps = [
    { name: 'support-copilot',    spend: 38420, calls: '2.4M', cpc: 0.0160, owner: 'CX' },
    { name: 'finops-assistant',   spend: 24820, calls: '420k', cpc: 0.0591, owner: 'Lumen' },
    { name: 'search-rag',          spend: 22640, calls: '8.6M', cpc: 0.0026, owner: 'Search' },
    { name: 'code-review-bot',     spend: 18240, calls: '184k', cpc: 0.0991, owner: 'DevEx' },
    { name: 'onboarding-agent',    spend: 14820, calls: '128k', cpc: 0.1158, owner: 'Growth' },
    { name: 'doc-summarizer',      spend: 11420, calls: '218k', cpc: 0.0524, owner: 'CS' },
    { name: 'analytics-nl-query',  spend:  9820, calls:  '64k', cpc: 0.1534, owner: 'BI' },
    { name: 'marketing-gen',       spend:  4620, calls:  '12k', cpc: 0.3850, owner: 'Marketing' },
  ];
  const max = apps[0].spend;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
      {apps.map((a) => (
        <div key={a.name} style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '3px 0' }}>
          <div style={{ minWidth: 0, flex: 1 }}>
            <div className="mono" style={{ fontSize: 11.5, color: 'var(--ink)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{a.name}</div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 2 }}>
              <div className="inline-bar" style={{ flex: 1, height: 4 }}>
                <i style={{ width: `${(a.spend / max) * 100}%`, background: 'var(--accent)' }} />
              </div>
              <span className="mono" style={{ fontSize: 9.5, color: 'var(--muted)' }}>{a.calls} calls · ${a.cpc.toFixed(3)}/call</span>
            </div>
          </div>
          <span className="mono" style={{ fontSize: 11.5, color: 'var(--ink)', fontWeight: 500, width: 50, textAlign: 'right' }}>${(a.spend / 1000).toFixed(1)}k</span>
        </div>
      ))}
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
// Swap suggestion — model router
// ─────────────────────────────────────────────────────────────────
function Swap({ from, fromV, to, toV, app, save, tone, note }) {
  return (
    <div style={{
      padding: '7px 9px', marginBottom: 5,
      background: 'var(--surface)',
      border: '1px solid var(--border)',
      borderLeft: `3px solid var(--${tone})`,
      borderRadius: 6,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 11 }}>
        <VBadge v={fromV} size={14} />
        <span className="mono" style={{ color: 'var(--muted)', textDecoration: 'line-through' }}>{from}</span>
        <Ico name="arrowR" size={10} />
        <VBadge v={toV} size={14} />
        <span className="mono" style={{ color: 'var(--ink)', fontWeight: 500 }}>{to}</span>
        <div style={{ flex: 1 }} />
        <span className="mono" style={{ color: `var(--${tone})`, fontSize: 11.5, fontWeight: 500 }}>{save}/mo</span>
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: 2 }}>
        <span style={{ fontSize: 10.5, color: 'var(--muted)' }}>in <span className="mono" style={{ color: 'var(--text)' }}>{app}</span>{note ? ' · ' + note : ''}</span>
        <button className="btn ghost" style={{ height: 18, padding: '0 6px', fontSize: 10 }}>Apply</button>
      </div>
    </div>
  );
}

// ─────────────────────────────────────────────────────────────────
// Seat heatmap — Cursor seats, activity over 14 days
// 142 seats; show as 12-col grid of 12 rows = 144. Color = activity
// ─────────────────────────────────────────────────────────────────
function SeatHeatmap() {
  // generate seed-based activity 0..1
  let s = 11;
  const rnd = () => { s = (s * 9301 + 49297) % 233280; return s / 233280; };
  const cells = Array.from({ length: 142 }, (_, i) => {
    const r = rnd();
    // 13% idle, 18% under, 50% healthy, 19% heavy
    if (r < 0.13) return { v: 0, label: 'idle ≥14d' };
    if (r < 0.31) return { v: 1, label: 'low' };
    if (r < 0.81) return { v: 2, label: 'healthy' };
    return { v: 3, label: 'heavy' };
  });
  const colorOf = (v) => v === 0 ? 'oklch(0.85 0.04 28)' : v === 1 ? 'oklch(0.85 0.04 80)' : v === 2 ? 'oklch(0.72 0.13 150)' : 'oklch(0.5 0.13 280)';
  return (
    <div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(24, 1fr)', gap: 2 }}>
        {cells.map((c, i) => (
          <div key={i} style={{ aspectRatio: '1 / 1', background: colorOf(c.v), borderRadius: 2 }} title={c.label} />
        ))}
      </div>
      <div style={{ display: 'flex', gap: 8, fontSize: 10, color: 'var(--muted)', marginTop: 4 }}>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 3 }}><i style={{ width: 8, height: 8, background: 'oklch(0.85 0.04 28)' }} /> idle</span>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 3 }}><i style={{ width: 8, height: 8, background: 'oklch(0.85 0.04 80)' }} /> low</span>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 3 }}><i style={{ width: 8, height: 8, background: 'oklch(0.72 0.13 150)' }} /> healthy</span>
        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 3 }}><i style={{ width: 8, height: 8, background: 'oklch(0.5 0.13 280)' }} /> heavy</span>
        <span style={{ flex: 1 }} />
        <span>142 seats · 14d</span>
      </div>
    </div>
  );
}

Object.assign(window, { AIScreen });
