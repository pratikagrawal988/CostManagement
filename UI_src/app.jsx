/* global React, ReactDOM, DesignCanvas, DCSection, DCArtboard, useTweaks, TweaksPanel, TweakSection, TweakRadio, TweakToggle, TweakColor, OverviewScreen, ExplorerScreen, AnomaliesScreen, BudgetsScreen, RecommendationsScreen, DrilldownScreen, AIScreen */

const TWEAK_DEFAULTS = /*EDITMODE-BEGIN*/{
  "theme":      "light",
  "chartMode":  "area",
  "density":    "regular",
  "accent":     "#3b5bdb"
}/*EDITMODE-END*/;

const ACCENT_MAP = {
  '#3b5bdb': { accent: 'oklch(0.55 0.13 250)', brand: 'oklch(0.28 0.06 250)' }, // indigo
  '#c2410c': { accent: 'oklch(0.58 0.16 35)',  brand: 'oklch(0.32 0.08 35)' },  // ember
  '#3f7d56': { accent: 'oklch(0.55 0.11 150)', brand: 'oklch(0.30 0.06 150)' }, // sage
  '#475569': { accent: 'oklch(0.4 0.02 270)',  brand: 'oklch(0.22 0.01 270)' }, // graphite
};

function App() {
  const [t, setTweak] = useTweaks(TWEAK_DEFAULTS);
  const themeClass = t.theme === 'dark' ? 'theme-dark' : '';
  const densClass = t.density === 'comfy' ? 'dens-comfy' : t.density === 'compact' ? 'dens-compact' : '';
  const wrapClass = `${themeClass} ${densClass}`.trim();
  const accentVars = ACCENT_MAP[t.accent] || ACCENT_MAP.indigo;
  const wrapStyle = { '--accent': accentVars.accent, '--brand': accentVars.brand, width: '100%', height: '100%' };

  // Each artboard wraps its screen in the theme+density+accent overrides.
  const W = 1440, H = 900;
  const wrap = (Screen, extra = {}) => (
    <div className={wrapClass} style={wrapStyle}>
      <Screen chartMode={t.chartMode} {...extra} />
    </div>
  );

  return (
    <>
      <DesignCanvas>
        <DCSection id="finops" title="Lumen · FinOps OS" subtitle="A cloud cost intelligence platform for CFO + FinOps · AWS, GCP, Azure — 6 flows, side by side. Use the toolbar to pan/zoom, double-click any artboard to focus.">
          <DCArtboard id="overview"        label="01 · Executive Overview"    width={W} height={H}>{wrap(OverviewScreen)}</DCArtboard>
          <DCArtboard id="explorer"        label="02 · Cost Explorer"         width={W} height={H}>{wrap(ExplorerScreen)}</DCArtboard>
          <DCArtboard id="anomalies"       label="03 · Anomaly Detection"     width={W} height={H}>{wrap(AnomaliesScreen)}</DCArtboard>
          <DCArtboard id="budgets"         label="04 · Budgets & Forecast"    width={W} height={H}>{wrap(BudgetsScreen)}</DCArtboard>
          <DCArtboard id="recommendations" label="05 · Recommendations"       width={W} height={H}>{wrap(RecommendationsScreen)}</DCArtboard>
          <DCArtboard id="ai"              label="06 · AI Cost · vendors + GPU" width={W} height={H}>{wrap(AIScreen)}</DCArtboard>
          <DCArtboard id="drilldown"       label="07 · Resource Drill-down"   width={W} height={H}>{wrap(DrilldownScreen)}</DCArtboard>
        </DCSection>
      </DesignCanvas>

      <TweaksPanel title="Lumen tweaks">
        <TweakSection label="Theme" />
        <TweakRadio label="Mode" value={t.theme} options={['light', 'dark']}
                    onChange={(v) => setTweak('theme', v)} />
        <TweakColor label="Accent" value={t.accent}
                    options={['#3b5bdb', '#c2410c', '#3f7d56', '#475569']}
                    onChange={(v) => setTweak('accent', v)} />

        <TweakSection label="Charts" />
        <TweakRadio label="Chart style" value={t.chartMode} options={['area', 'bar', 'line']}
                    onChange={(v) => setTweak('chartMode', v)} />

        <TweakSection label="Layout" />
        <TweakRadio label="Density" value={t.density} options={['compact', 'regular', 'comfy']}
                    onChange={(v) => setTweak('density', v)} />
      </TweaksPanel>
    </>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
