from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def read(p): return (ROOT/p).read_text(encoding='utf-8')
def write(p,s): (ROOT/p).write_text(s,encoding='utf-8')
def once(s,o,n,l):
    c=s.count(o)
    if c!=1: raise SystemExit(f'{l}: expected 1, found {c}')
    return s.replace(o,n,1)
app=read('app.js')
app=once(app,"const { compoundGrowth } = window.VestraFinancialEngine || {};\nif (typeof compoundGrowth !== 'function') {\n  throw new Error('VestraFinancialEngine não foi carregado antes de app.js');\n}","const { compoundGrowth, projectFireScenarios } = window.VestraFinancialEngine || {};\nif (![compoundGrowth, projectFireScenarios].every(fn => typeof fn === 'function')) {\n  throw new Error('VestraFinancialEngine não foi carregado antes de app.js');\n}",'financial engine import')
old='''  const results = [];
  for (const sc of scenarios) {
    let cap = cap0, exp = exp0, hit = null;
    const fireNum = sc.swr > 0 ? exp0 / sc.swr : Infinity;
    for (let t = 0; t <= H; t++) {
      const pass = passiveYieldRate * cap;
      const fn = sc.swr > 0 ? exp / sc.swr : Infinity;
      if (!hit && cap >= fn) hit = {t, cap, exp, pass, fireNum: fn};
      if (t < H) {
        cap = cap * (1 + sc.r) + saveM * 12;
        exp = exp * (1 + sc.inf);
      }
    }
    results.push({sc, hit, fireNum});
  }'''
new='''  const results = projectFireScenarios({
    capital: cap0,
    annualExpenses: exp0,
    monthlySavings: saveM,
    horizonYears: H,
    passiveYieldRate,
    scenarios,
  });'''
app=once(app,old,new,'fire loop')
write('app.js',app)
idx=read('index.html').replace('app-financial-engine.js?v=1.0','app-financial-engine.js?v=1.1').replace('app.js?v=20260827v17','app.js?v=20260827v18')
write('index.html',idx)
sw=read('sw.js').replace('Vestra Service Worker v10.6','Vestra Service Worker v10.7').replace('vestra-cache-v120','vestra-cache-v121')
write('sw.js',sw)
for p in (ROOT/'tests').glob('test_*.py'):
    s=p.read_text(encoding='utf-8').replace('app-financial-engine.js?v=1.0','app-financial-engine.js?v=1.1').replace('app.js?v=20260827v17','app.js?v=20260827v18').replace('Vestra Service Worker v10.6','Vestra Service Worker v10.7').replace('vestra-cache-v120','vestra-cache-v121')
    p.write_text(s,encoding='utf-8')
(ROOT/'tests/test_fire_projection_engine.py').write_text('''from pathlib import Path\nimport unittest\nROOT=Path(__file__).resolve().parents[1]\ndef read(p): return (ROOT/p).read_text(encoding="utf-8")\nclass FireProjectionEngineTests(unittest.TestCase):\n  def test_engine_owns_fire_projection(self):\n    e=read("app-financial-engine.js"); a=read("app.js")\n    self.assertIn("function projectFireScenarios",e)\n    self.assertIn("projectFireScenarios({",a)\n    self.assertNotIn("for (const sc of scenarios) {\\n    let cap = cap0",a)\n  def test_bundle_versions(self):\n    i=read("index.html"); sw=read("sw.js")\n    self.assertIn("app-financial-engine.js?v=1.1",i)\n    self.assertIn("app.js?v=20260827v18",i)\n    self.assertIn("Vestra Service Worker v10.7",sw)\n    self.assertIn("vestra-cache-v121",sw)\nif __name__=="__main__": unittest.main(verbosity=2)\n''',encoding='utf-8')
print('FIRE projection extraction prepared')
