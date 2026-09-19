from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class LazyMarketRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = (ROOT / "index.html").read_text(encoding="utf-8")
        cls.loader = (ROOT / "app-market-runtime-loader.js").read_text(encoding="utf-8")
        cls.app = (ROOT / "app.js").read_text(encoding="utf-8")
        cls.nav = (ROOT / "portfolio-sheet-navigation.js").read_text(encoding="utf-8")
        cls.data_loader = (ROOT / "market-data-loader.js").read_text(encoding="utf-8")
        cls.sw = (ROOT / "sw.js").read_text(encoding="utf-8")

    def test_market_monolith_is_not_executed_on_initial_html_load(self):
        self.assertNotIn('<script defer="" src="market.js?v=20260831v2"></script>', self.index)
        self.assertIn('<script defer="" src="app-market-runtime-loader.js?v=1.0"></script>', self.index)

    def test_loader_is_single_flight_bounded_retryable_and_announces_ready(self):
        self.assertIn("if (window.VestraMarket) return Promise.resolve(window.VestraMarket);", self.loader)
        self.assertIn("if (loadPromise) return loadPromise;", self.loader)
        self.assertIn("const TIMEOUT_MS = 12000;", self.loader)
        self.assertIn("loadPromise = null;", self.loader)
        self.assertIn("script.remove();", self.loader)
        self.assertIn("script.dataset.vestraMarketRuntime = '1';", self.loader)
        self.assertIn("'vestra:market-runtime-ready'", self.loader)
        self.assertIn("src: SRC", self.loader)

    def test_entering_market_loads_runtime_then_static_universe(self):
        start = self.app.index("function setView(view)")
        end = self.app.index("function openModal", start)
        block = self.app[start:end]
        self.assertIn('if (view === "market")', block)
        self.assertIn("window.VestraMarketRuntimeLoader", block)
        self.assertIn("loader.ensure()", block)
        self.assertIn("api?.ensureLoaded?.()", block)

    def test_portfolio_dossier_first_touch_loads_runtime(self):
        start = self.app.index("const openResearch = async ev=>")
        end = self.app.index("const researchBtn=", start)
        block = self.app[start:end]
        self.assertIn("window.VestraMarketRuntimeLoader?.ensure?.()", block)
        self.assertIn("window.VestraMarket.openPortfolioAsset(it)", block)

    def test_navigation_can_lazy_boot_market_before_opening_company(self):
        start = self.nav.index("async function openCompany")
        end = self.nav.index("function cleanupPortfolioChrome", start)
        block = self.nav[start:end]
        self.assertIn("let api=window.VestraMarket;", block)
        self.assertIn("api=await window.VestraMarketRuntimeLoader?.ensure?.()", block)
        self.assertIn("api.openTicker(tk)", block)

    def test_dossier_wrapper_reinstalls_after_lazy_runtime_arrives(self):
        self.assertIn(
            "window.addEventListener('vestra:market-runtime-ready',()=>{ installApiWrapper(); },{passive:true});",
            self.data_loader,
        )

    def test_market_runtime_remains_precached_for_offline_first_use(self):
        self.assertIn('"./app-market-runtime-loader.js"', self.sw)
        self.assertIn('"./market.js"', self.sw)


if __name__ == "__main__":
    unittest.main(verbosity=2)
