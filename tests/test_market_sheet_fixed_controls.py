from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class MarketSheetFixedControlsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.controls = (ROOT / "market-dossier-controls.js").read_text(encoding="utf-8")
        cls.css = (ROOT / "market-dossier-controls.css").read_text(encoding="utf-8")
        cls.tools = (ROOT / "market-analysis-tools-runtime.js").read_text(encoding="utf-8")

    def test_open_market_sheet_keeps_close_portal_even_without_ticker(self):
        self.assertIn("const visible = Boolean(sheet && !sheet.hidden);", self.controls)
        self.assertIn("portal.classList.toggle('market-dossier-action-portal--tool', visible && !ticker);", self.controls)
        self.assertNotIn("Boolean(sheet && !sheet.hidden && ticker)", self.controls)

    def test_watch_star_only_appears_when_ticker_has_watch_target(self):
        self.assertIn("const hasWatchTarget = Boolean(ticker && original);", self.controls)
        self.assertIn("watch.classList.toggle('is-unavailable', !hasWatchTarget);", self.controls)
        self.assertIn(".market-watch--portal.is-unavailable{display:none!important}", self.css)

    def test_tool_runtime_syncs_fixed_portal_on_open_and_close(self):
        self.assertGreaterEqual(
            self.tools.count("window.VestraMarketDossierControls?.syncPortal?.(sheet);"),
            2,
        )

    def test_mobile_tool_portal_has_single_close_slot(self):
        self.assertIn(".market-dossier-action-portal--tool{grid-template-columns:44px!important}", self.css)
        self.assertIn("position:fixed!important", self.css)
        self.assertIn("right:max(calc(env(safe-area-inset-right,0px) + 14px),14px)!important", self.css)


if __name__ == "__main__":
    unittest.main(verbosity=2)
