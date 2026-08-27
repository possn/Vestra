from pathlib import Path
import json, subprocess, unittest
ROOT=Path(__file__).resolve().parents[1]
def read(p): return (ROOT/p).read_text(encoding="utf-8")
class FinancialEngineTests(unittest.TestCase):
    def run_node(self,expr):
        code=f"global.window={{}};require('./app-financial-engine.js');console.log(JSON.stringify({expr}));"
        out=subprocess.check_output(['node','-e',code],cwd=ROOT,text=True).strip()
        return json.loads(out)
    def test_annual_compounding_applies_interest_once(self):
        rows=self.run_node("window.VestraFinancialEngine.compoundGrowth(100,10,1,1,0)")
        self.assertEqual(len(rows),2)
        self.assertAlmostEqual(rows[-1]['value'],110,places=9)
    def test_monthly_contributions_are_preserved(self):
        rows=self.run_node("window.VestraFinancialEngine.compoundGrowth(0,0,1,12,100)")
        self.assertAlmostEqual(rows[-1]['value'],1200,places=9)
    def test_app_uses_shared_engine(self):
        app=read('app.js')
        self.assertIn('window.VestraFinancialEngine',app)
        self.assertNotIn('function compoundGrowth(',app)
        idx=read('index.html')
        self.assertLess(idx.index('src="app-financial-engine.js'),idx.index('src="app.js'))
        sw=read('sw.js')
        self.assertIn('Vestra Service Worker v10.10',sw)
        self.assertIn('vestra-cache-v124',sw)
        self.assertIn('./app-financial-engine.js',sw)
if __name__=='__main__': unittest.main(verbosity=2)
