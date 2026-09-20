from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class LazyMarketCoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = (ROOT / "index.html").read_text(encoding="utf-8")
        cls.loader = (ROOT / "market-runtime-loader.js").read_text(encoding="utf-8")
        cls.app = (ROOT / "app.js").read_text(encoding="utf-8")
        cls.data_loader = (ROOT / "market-data-loader.js").read_text(encoding="utf-8")
        cls.navigation = (ROOT / "portfolio-sheet-navigation.js").read_text(encoding="utf-8")

    def test_market_core_is_not_in_initial_html(self):
        self.assertNotIn('src="market.js?v=20260831v2"', self.index)
        self.assertIn('src="market-runtime-loader.js?v=1.2"', self.index)
        self.assertIn('portfolio-sheet-navigation.js?v=1.5', self.index)
        self.assertIn('market-data-loader.js?v=2.6', self.index)

    def test_loader_is_single_flight_bounded_and_does_not_fake_market_api(self):
        self.assertIn("if (!loadPromise)", self.loader)
        self.assertIn("function ensureHelpers()", self.loader)
        self.assertIn("function ensureEnhancements()", self.loader)
        self.assertIn("market-metric-cleanup.js?v=1.2", self.loader)
        self.assertIn("market-company-brief.js?v=2.1", self.loader)
        self.assertNotIn("ensureEnhancements().then(() => window.VestraMarket)", self.loader)
        self.assertNotIn("ensureEnhancements().then(() => api)", self.loader)
        self.assertIn("ensureEnhancements().catch(err => console.warn", self.loader)
        self.assertNotIn('src="market-metric-cleanup.js', self.index)
        self.assertNotIn('src="market-company-brief.js', self.index)
        self.assertIn("Promise.all([", self.loader)
        self.assertIn("const TIMEOUT_MS = 12000;", self.loader)
        self.assertIn("script.dataset.vestraMarketCore = '1';", self.loader)
        self.assertIn("loadPromise = null;", self.loader)
        self.assertIn("window.VestraMarketLoader = Object.freeze", self.loader)
        self.assertNotIn("window.VestraMarket =", self.loader)

    def test_market_navigation_loads_real_core_then_data(self):
        self.assertIn('if (view === "market")', self.app)
        self.assertIn("window.VestraMarketLoader?.ensure?.({ loadData: true })", self.app)
        self.assertIn("api.ensureLoaded()", self.loader)

    def test_portfolio_dossier_waits_for_lazy_core(self):
        self.assertIn("api=await window.VestraMarketLoader?.ensure?.()", self.navigation)
        self.assertIn("const result=api.openTicker(tk);", self.navigation)

    def test_dossier_hydration_wrapper_reinstalls_when_core_arrives_late(self):
        self.assertIn("vestra:market-core-ready", self.loader)
        self.assertIn("window.addEventListener('vestra:market-core-ready'", self.data_loader)
        self.assertIn("installApiWrapper();", self.data_loader)


if __name__ == "__main__":
    unittest.main(verbosity=2)
