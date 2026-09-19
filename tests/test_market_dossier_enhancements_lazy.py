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
        core = LOADER.index(".then(loadCore)")
        fire_and_forget = LOADER.index("void ensureDossierEnhancements().catch", core)
        return_api = LOADER.index("return api;", fire_and_forget)
        public_chain = LOADER.index("return loadPromise.then(api =>", return_api)
        self.assertLess(core, fire_and_forget)
        self.assertLess(fire_and_forget, return_api)
        self.assertLess(return_api, public_chain)
        self.assertNotIn("await ensureDossierEnhancements", LOADER[core:public_chain])

    def test_enhancements_remain_precached_offline(self):
        self.assertIn('"./market-company-brief.js"', SW)
        self.assertIn('"./market-metric-cleanup.js"', SW)

    def test_loader_rollout_is_versioned(self):
        self.assertIn("version: '1.2'", LOADER)
        self.assertIn("detail: { version: '1.2' }", LOADER)


if __name__ == "__main__":
    unittest.main(verbosity=2)
