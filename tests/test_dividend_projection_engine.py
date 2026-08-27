from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
def read(p): return (ROOT/p).read_text(encoding="utf-8")
class DividendProjectionEngineTests(unittest.TestCase):
  def test_engine_owns_dividend_projection(self):
    e=read("app-financial-engine.js"); a=read("app.js")
    self.assertIn("function projectDividendScenarios",e)
    self.assertIn("projectDividendScenarios({",a)
    self.assertNotIn("const allData = scenarios.map(sc => {",a)
  def test_projection_preserves_year_zero_and_growth_contract(self):
    e=read("app-financial-engine.js")
    for token in ("grossArr.push(gross0)","netArr.push(net0)","curPortfolio * (yieldPct / 100)","contribution * 12"):
      self.assertIn(token,e)
  def test_bundle_versions(self):
    i=read("index.html"); sw=read("sw.js")
    self.assertIn("app-financial-engine.js?v=1.2",i)
    self.assertIn("app.js?v=20260827v20",i)
    self.assertIn("Vestra Service Worker v10.9",sw)
    self.assertIn("vestra-cache-v123",sw)
if __name__=="__main__": unittest.main(verbosity=2)
