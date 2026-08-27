from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
def read(p): return (ROOT/p).read_text(encoding="utf-8")
class FireProjectionEngineTests(unittest.TestCase):
  def test_engine_owns_fire_projection(self):
    e=read("app-financial-engine.js"); a=read("app.js")
    self.assertIn("function projectFireScenarios",e)
    self.assertIn("projectFireScenarios({",a)
    self.assertNotIn("for (const sc of scenarios) {\n    let cap = cap0",a)
  def test_bundle_versions(self):
    i=read("index.html"); sw=read("sw.js")
    self.assertIn("app-financial-engine.js?v=1.1",i)
    self.assertIn("app.js?v=20260827v18",i)
    self.assertIn("Vestra Service Worker v10.7",sw)
    self.assertIn("vestra-cache-v121",sw)
if __name__=="__main__": unittest.main(verbosity=2)
