from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[1]
def read(p): return (ROOT/p).read_text(encoding='utf-8')
def write(p,s): (ROOT/p).write_text(s,encoding='utf-8')
def once(s,old,new,label):
    n=s.count(old)
    if n!=1: raise SystemExit(f'{label}: expected 1 occurrence, found {n}')
    return s.replace(old,new,1)

app=read('app.js')
anchor="""if (!PASSIVE_DEFAULTS || !APPRECIATION_DEFAULTS || !DEFAULT_RETURN_SETTINGS ||
    typeof normalizeReturnSettings !== 'function' || typeof getReturnClassDefinitions !== 'function') {
  throw new Error('VestraReturnAssumptions não foi carregado antes de app.js');
}
"""
imp="""
/* ─── FINANCIAL ENGINE — moved to app-financial-engine.js ─ */
const { compoundGrowth } = window.VestraFinancialEngine || {};
if (typeof compoundGrowth !== 'function') {
  throw new Error('VestraFinancialEngine não foi carregado antes de app.js');
}
"""
app=once(app,anchor,anchor+imp,'financial engine import')
pat=r"\nfunction compoundGrowth\(principal, rateAnnual, years, freq = 12, contributions = 0\) \{.*?\n\}\n"
app,n=re.subn(pat,'\n',app,count=1,flags=re.S)
if n!=1: raise SystemExit(f'compoundGrowth extraction: {n}')
if 'function compoundGrowth(' in app: raise SystemExit('local compoundGrowth remains')
write('app.js',app)

index=read('index.html')
index=once(index,'<script defer="" src="app-return-assumptions.js?v=1.0"></script>\n','<script defer="" src="app-return-assumptions.js?v=1.0"></script>\n<script defer="" src="app-financial-engine.js?v=1.0"></script>\n','index financial engine')
index=index.replace('app.js?v=20260827v15','app.js?v=20260827v16')
write('index.html',index)

sw=read('sw.js')
sw=sw.replace('Vestra Service Worker v10.4','Vestra Service Worker v10.5').replace('vestra-cache-v118','vestra-cache-v119')
sw=once(sw,'  "./app-return-assumptions.js",\n','  "./app-return-assumptions.js",\n  "./app-financial-engine.js",\n','SW financial engine')
write('sw.js',sw)

for path in (ROOT/'tests').glob('test_*.py'):
    s=path.read_text(encoding='utf-8')
    s=s.replace('Vestra Service Worker v10.4','Vestra Service Worker v10.5').replace('vestra-cache-v118','vestra-cache-v119')
    s=s.replace('app.js?v=20260827v15','app.js?v=20260827v16')
    path.write_text(s,encoding='utf-8')

(ROOT/'tests/test_financial_engine.py').write_text('''from pathlib import Path\nimport json, subprocess, unittest\nROOT=Path(__file__).resolve().parents[1]\ndef read(p): return (ROOT/p).read_text(encoding="utf-8")\nclass FinancialEngineTests(unittest.TestCase):\n    def run_node(self,expr):\n        code=f"global.window={{}};require('./app-financial-engine.js');console.log(JSON.stringify({expr}));"\n        out=subprocess.check_output(['node','-e',code],cwd=ROOT,text=True).strip()\n        return json.loads(out)\n    def test_annual_compounding_applies_interest_once(self):\n        rows=self.run_node("window.VestraFinancialEngine.compoundGrowth(100,10,1,1,0)")\n        self.assertEqual(len(rows),2)\n        self.assertAlmostEqual(rows[-1]['value'],110,places=9)\n    def test_monthly_contributions_are_preserved(self):\n        rows=self.run_node("window.VestraFinancialEngine.compoundGrowth(0,0,1,12,100)")\n        self.assertAlmostEqual(rows[-1]['value'],1200,places=9)\n    def test_app_uses_shared_engine(self):\n        app=read('app.js')\n        self.assertIn('window.VestraFinancialEngine',app)\n        self.assertNotIn('function compoundGrowth(',app)\n        idx=read('index.html')\n        self.assertLess(idx.index('src=\"app-financial-engine.js'),idx.index('src=\"app.js'))\n        sw=read('sw.js')\n        self.assertIn('Vestra Service Worker v10.5',sw)\n        self.assertIn('vestra-cache-v119',sw)\n        self.assertIn('./app-financial-engine.js',sw)\nif __name__=='__main__': unittest.main(verbosity=2)\n''',encoding='utf-8')
print('financial engine extraction prepared')
