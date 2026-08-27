from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def read(p): return (ROOT/p).read_text(encoding='utf-8')
def write(p,s): (ROOT/p).write_text(s,encoding='utf-8')
def once(s,o,n,l):
    c=s.count(o)
    if c!=1: raise SystemExit(f'{l}: expected 1, found {c}')
    return s.replace(o,n,1)

app=read('app.js')
app=once(app,
"const { compoundGrowth, projectFireScenarios } = window.VestraFinancialEngine || {};\nif (![compoundGrowth, projectFireScenarios].every(fn => typeof fn === 'function')) {\n  throw new Error('VestraFinancialEngine não foi carregado antes de app.js');\n}",
"const { compoundGrowth, projectFireScenarios, projectDividendScenarios } = window.VestraFinancialEngine || {};\nif (![compoundGrowth, projectFireScenarios, projectDividendScenarios].every(fn => typeof fn === 'function')) {\n  throw new Error('VestraFinancialEngine não foi carregado antes de app.js');\n}",
'financial engine import')

old='''  const allData = scenarios.map(sc => {
    const labels = [], netArr = [], grossArr = [];
    let curPortfolio = portfolioVal;
    for (let y = 0; y <= years; y++) {
      labels.push(y === 0 ? (latest ? String(latest.year) : "Hoje") : `+${y}a`);
      if (y === 0) {
        // Ano 0: valores REAIS do resumo, não calculados
        grossArr.push(baseGross);
        netArr.push(baseNet);
      } else {
        // Anos seguintes: carteira cresce, aplica yield e retenção
        const projGross = curPortfolio * (sc.yield / 100);
        const projNet = projGross * (1 - retRate);
        grossArr.push(projGross);
        netArr.push(projNet);
      }
      curPortfolio = curPortfolio * (1 + portfolioGrowth / 100) + contrib * 12;
    }
    return { ...sc, labels, netArr, grossArr };
  });'''
new='''  const allData = projectDividendScenarios({
    portfolioValue: portfolioVal,
    baseGross,
    baseNet,
    retentionRate: retRate,
    portfolioGrowthPct: portfolioGrowth,
    monthlyContribution: contrib,
    years,
    baseLabel: latest ? String(latest.year) : "Hoje",
    scenarios,
  });'''
app=once(app,old,new,'dividend projection loop')
write('app.js',app)

idx=read('index.html')
idx=once(idx,'app-financial-engine.js?v=1.1','app-financial-engine.js?v=1.2','engine bundle')
idx=once(idx,'app.js?v=20260827v18','app.js?v=20260827v19','app bundle')
write('index.html',idx)

sw=read('sw.js')
sw=once(sw,'Vestra Service Worker v10.7','Vestra Service Worker v10.8','sw version')
sw=once(sw,'vestra-cache-v121','vestra-cache-v122','sw cache')
write('sw.js',sw)

for p in (ROOT/'tests').glob('test_*.py'):
    s=p.read_text(encoding='utf-8')
    s=s.replace('app-financial-engine.js?v=1.1','app-financial-engine.js?v=1.2')
    s=s.replace('app.js?v=20260827v18','app.js?v=20260827v19')
    s=s.replace('Vestra Service Worker v10.7','Vestra Service Worker v10.8')
    s=s.replace('vestra-cache-v121','vestra-cache-v122')
    p.write_text(s,encoding='utf-8')

(ROOT/'tests/test_dividend_projection_engine.py').write_text('''from pathlib import Path\nimport unittest\nROOT=Path(__file__).resolve().parents[1]\ndef read(p): return (ROOT/p).read_text(encoding="utf-8")\nclass DividendProjectionEngineTests(unittest.TestCase):\n  def test_engine_owns_dividend_projection(self):\n    e=read("app-financial-engine.js"); a=read("app.js")\n    self.assertIn("function projectDividendScenarios",e)\n    self.assertIn("projectDividendScenarios({",a)\n    self.assertNotIn("const allData = scenarios.map(sc => {",a)\n  def test_projection_preserves_year_zero_and_growth_contract(self):\n    e=read("app-financial-engine.js")\n    for token in ("grossArr.push(gross0)","netArr.push(net0)","curPortfolio * (yieldPct / 100)","contribution * 12"):\n      self.assertIn(token,e)\n  def test_bundle_versions(self):\n    i=read("index.html"); sw=read("sw.js")\n    self.assertIn("app-financial-engine.js?v=1.2",i)\n    self.assertIn("app.js?v=20260827v19",i)\n    self.assertIn("Vestra Service Worker v10.8",sw)\n    self.assertIn("vestra-cache-v122",sw)\nif __name__=="__main__": unittest.main(verbosity=2)\n''',encoding='utf-8')
print('dividend projection extraction prepared')
