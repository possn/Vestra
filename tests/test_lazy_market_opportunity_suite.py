from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "index.html").read_text(encoding="utf-8")
LOADER = (ROOT / "market-static-universe.js").read_text(encoding="utf-8")


class LazyMarketOpportunitySuiteTests(unittest.TestCase):
    def test_market_only_modules_leave_initial_html(self):
        for name in (
            "market-metals.js",
            "market-opportunities.js",
            "market-opportunity-lenses.js",
        ):
            self.assertNotIn(f'src="{name}', INDEX)

    def test_opportunity_suite_is_loaded_in_dependency_order(self):
        start = LOADER.index("function ensureOpportunitySuite()")
        end = LOADER.index("\n  function ensureMarketCompanions()", start)
        block = LOADER[start:end]
        base = block.index("'market-opportunities.js?v=1.2'")
        lenses = block.index("'market-opportunity-lenses.js?v=3.1'")
        self.assertLess(base, lenses)
        self.assertIn("if (!base) return null;", block)
        self.assertIn("opportunitySuitePromise", block)

    def test_metals_and_opportunity_suite_start_only_with_market_companions(self):
        start = LOADER.index("function ensureMarketCompanions()")
        end = LOADER.index("\n  function announceReady", start)
        block = LOADER[start:end]
        self.assertIn("ensureMetalsCompanion();", block)
        self.assertIn("void ensureOpportunitySuite();", block)

        eager = LOADER[LOADER.index("// Dashboard/mobile companions remain eager"):]
        self.assertNotIn("ensureMetalsCompanion();", eager)
        self.assertNotIn("ensureOpportunitySuite();", eager)

    def test_loader_version_is_bumped_for_clean_pwa_rollout(self):
        self.assertIn("market-static-universe.js?v=1.21", INDEX)
        self.assertIn("version: '1.21'", LOADER)


if __name__ == "__main__":
    unittest.main(verbosity=2)
