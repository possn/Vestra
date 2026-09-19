from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class LazyMarketRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = (ROOT / "index.html").read_text(encoding="utf-8")
        cls.loader = (ROOT / "market-runtime-loader.js").read_text(encoding="utf-8")
        cls.app = (ROOT / "app.js").read_text(encoding="utf-8")
        cls.nav = (ROOT / "portfolio-sheet-navigation.js").read_text(encoding="utf-8")

    def test_heavy_market_runtime_is_not_in_initial_html(self):
        self.assertIn('src="market-runtime-loader.js?v=1.1"', self.index)
        self.assertIn('src="market-static-universe.js?v=1.13"', self.index)
        self.assertIn('src="portfolio-sheet-navigation.js?v=1.3"', self.index)
        for src in (
            "market-live-overlay.js", "market-congress-live.js", "market-portfolio-context.js",
            "market-watch-snapshots.js", "market-dossier-signals.js", "market-search-suggestions.js",
            "market-row-ui.js", "market.js", "market-data-loader.js", "market-company-brief.js",
            "market-opportunities.js", "vestra-portfolio-ui.js", "politicians.js",
        ):
            self.assertNotIn(f'src="{src}', self.index)

    def test_core_runtime_loads_in_dependency_order(self):
        core = self.loader[self.loader.index("const CORE_MODULES"):self.loader.index("const ENHANCEMENT_MODULES")]
        expected = [
            "market-live-overlay.js?v=1.2",
            "market-congress-live.js?v=1.0",
            "market-portfolio-context.js?v=1.0",
            "market-watch-snapshots.js?v=1.0",
            "market-dossier-signals.js?v=1.0",
            "market-search-suggestions.js?v=1.2",
            "market-row-ui.js?v=1.0",
            "market.js?v=20260831v2",
            "market-data-loader.js?v=2.5",
        ]
        positions = [core.index(item) for item in expected]
        self.assertEqual(positions, sorted(positions))
        self.assertIn("await loadSequence(CORE_MODULES);", self.loader)
        self.assertIn("if (!api?.ensureLoaded || !api?.openTicker)", self.loader)

    def test_enhancements_are_off_the_first_market_paint_path(self):
        self.assertIn("const ENHANCEMENT_MODULES", self.loader)
        self.assertIn("setTimeout(() => { void ensureEnhancements(); }, 0);", self.loader)
        self.assertIn("market-company-brief.js?v=1.0", self.loader)
        self.assertIn("market-opportunities.js?v=1.1", self.loader)
        self.assertIn("politicians.js?v=2.1", self.loader)
        self.assertIn("version: '1.1'", self.loader)

    def test_market_navigation_and_portfolio_dossiers_boot_runtime(self):
        self.assertIn('if (view === "market")', self.app)
        self.assertIn("ensureMarketRuntimeReady({ loadData: true })", self.app)
        self.assertIn("if (!market?.openPortfolioAsset) market = await ensureMarketRuntimeReady();", self.app)
        self.assertIn("const loader=window.VestraMarketRuntime;", self.nav)
        self.assertIn("if(loader?.ensure) api=await loader.ensure();", self.nav)
        self.assertIn("await api.ensureLoaded?.()", self.nav)

    def test_loader_is_single_flight_and_retryable(self):
        self.assertIn("if (!runtimePromise)", self.loader)
        self.assertIn("runtimePromise = null;", self.loader)
        self.assertIn("const MODULE_TIMEOUT_MS = 8000;", self.loader)
        self.assertIn("if (script.isConnected) script.remove();", self.loader)
        self.assertIn("script.async = false;", self.loader)


if __name__ == "__main__":
    unittest.main(verbosity=2)
