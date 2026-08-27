from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
def read(p): return (ROOT/p).read_text(encoding="utf-8")

class AppReturnAssumptionsTests(unittest.TestCase):
    def test_defaults_are_preserved_exactly(self):
        s=read("app-return-assumptions.js")
        for token in ("'acoes/etfs':1.8", "'depositos':2", "'obrigacoes':3", "'acoes/etfs':6", "'ppr':3.5", "twrMinYears:0.5"):
            self.assertIn(token,s)
        self.assertIn("normalizeReturnSettings",s)
        self.assertIn("getReturnClassDefinitions",s)

    def test_app_uses_shared_assumptions_without_local_duplicates(self):
        app=read("app.js")
        self.assertIn("window.VestraReturnAssumptions",app)
        self.assertIn("normalizeReturnSettings((state && state.settings && state.settings.returnDefaults) || {}, parseNum)",app)
        self.assertNotIn("const PASSIVE_DEFAULTS = {",app)
        self.assertNotIn("const APPRECIATION_DEFAULTS = {",app)
        self.assertNotIn("const DEFAULT_RETURN_SETTINGS = {",app)
        self.assertNotIn("function getReturnClassDefinitions()",app)

    def test_module_load_order_and_cache(self):
        index=read("index.html")
        self.assertLess(index.index('src="app-return-assumptions.js'),index.index('src="app.js'))
        sw=read("sw.js")
        self.assertIn("Vestra Service Worker v10.9",sw)
        self.assertIn("vestra-cache-v123",sw)
        self.assertIn('./app-return-assumptions.js',sw)

if __name__=='__main__': unittest.main(verbosity=2)
