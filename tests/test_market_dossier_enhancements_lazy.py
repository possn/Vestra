from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "index.html").read_text(encoding="utf-8")
LOADER = (ROOT / "market-runtime-loader.js").read_text(encoding="utf-8")
SW = (ROOT / "sw.js").read_text(encoding="utf-8")


class LazyMarketDossierEnhancementTests(unittest.TestCase):
    def test_dossier_enhancements_are_not_in_initial_html(self):
        self.assertNotIn('src="market-company-brief.js', INDEX)
        self.assertNotIn('src="market-metric-cleanup.js', INDEX)
        self.assertIn('market-runtime-loader.js?v=1.2', INDEX)

    def test_cleanup_loads_before_company_brief(self):
        cleanup = "loadHelper('VestraMarketMetricCleanup', 'market-metric-cleanup.js?v=1.0')"
        brief = "loadHelper('VestraMarketCompanyBrief', 'market-company-brief.js?v=1.0')"
        self.assertIn(cleanup, LOADER)
        self.assertIn(brief, LOADER)
        self.assertLess(LOADER.index(cleanup), LOADER.index(brief))

    def test_enhancements_start_after_core_without_blocking_market_ready(self):
        self.assertIn(".then(loadCore)", LOADER)
        self.assertIn("void ensureDossierEnhancements().catch", LOADER)
        block_start = LOADER.index(".then(loadCore)")
        block_end = LOADER.index(".catch(err => {", block_start)
        block = LOADER[block_start:block_end]
        self.assertIn("return api;", block)
        self.assertNotIn("await ensureDossierEnhancements", block)

    def test_enhancements_remain_precached_offline(self):
        self.assertIn('"./market-company-brief.js"', SW)
        self.assertIn('"./market-metric-cleanup.js"', SW)

    def test_loader_rollout_is_versioned(self):
        self.assertIn("version: '1.2'", LOADER)
        self.assertIn("detail: { version: '1.2' }", LOADER)


if __name__ == "__main__":
    unittest.main(verbosity=2)
