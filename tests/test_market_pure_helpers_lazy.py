from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "index.html").read_text(encoding="utf-8")
LOADER = (ROOT / "market-runtime-loader.js").read_text(encoding="utf-8")
SW = (ROOT / "sw.js").read_text(encoding="utf-8")

HELPERS = (
    ("VestraMarketLiveOverlay", "market-live-overlay.js?v=1.2"),
    ("VestraMarketCongressLive", "market-congress-live.js?v=1.0"),
    ("VestraMarketPortfolioContext", "market-portfolio-context.js?v=1.0"),
    ("VestraMarketWatchSnapshots", "market-watch-snapshots.js?v=1.0"),
    ("VestraMarketDossierSignals", "market-dossier-signals.js?v=1.0"),
    ("VestraMarketSearchSuggestions", "market-search-suggestions.js?v=1.2"),
    ("VestraMarketRowUI", "market-row-ui.js?v=1.0"),
)


class LazyMarketPureHelpersTests(unittest.TestCase):
    def test_helpers_are_not_in_initial_html(self):
        for _, src in HELPERS:
            path = src.split("?")[0]
            self.assertNotIn(f'src="{path}', INDEX)

    def test_helpers_are_loaded_before_market_core(self):
        core = LOADER.index("script.src = 'market.js?v=20260920v1';")
        for global_name, src in HELPERS:
            token = f"loadHelper('{global_name}', '{src}')"
            self.assertIn(token, LOADER)
            self.assertLess(LOADER.index(token), core)

    def test_helper_load_is_parallel_single_flight_and_retryable(self):
        self.assertIn("function ensureHelpers()", LOADER)
        self.assertIn("Promise.all([", LOADER)
        self.assertIn("if (!helpersPromise) {", LOADER)
        self.assertIn("return helpersPromise;", LOADER)
        self.assertIn("helpersPromise = null;", LOADER)
        self.assertIn("script.dataset.vestraMarketHelper = globalName;", LOADER)

    def test_helpers_remain_precached_offline(self):
        for _, src in HELPERS:
            path = src.split("?")[0]
            self.assertIn(f'"./{path}"', SW)

    def test_loader_rollout_is_versioned(self):
        self.assertIn('market-runtime-loader.js?v=1.4', INDEX)
        self.assertIn("version: '1.4'", LOADER)


if __name__ == "__main__":
    unittest.main(verbosity=2)
