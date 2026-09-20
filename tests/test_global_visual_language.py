from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "index.html").read_text(encoding="utf-8")
STYLES = (ROOT / "styles.css").read_text(encoding="utf-8")


class GlobalVisualLanguageTests(unittest.TestCase):
    def test_stylesheet_rollout_is_versioned(self):
        self.assertIn('styles.css?v=20260920v4', INDEX)

    def test_dividends_and_analysis_have_compact_editorial_headers(self):
        self.assertIn('class="view-intro view-intro--dividends"', INDEX)
        self.assertIn('class="view-intro view-intro--analysis"', INDEX)
        self.assertIn('<h2>Dividendos</h2>', INDEX)
        self.assertIn('<h2>Análise</h2>', INDEX)

    def test_each_primary_view_has_its_own_restrained_accent(self):
        for view in (
            "viewDashboard", "viewAssets", "viewCashflow", "viewMarket",
            "viewDividends", "viewAnalysis", "viewSettings",
        ):
            self.assertIn(f"#{view}{{--view-accent:", STYLES)

    def test_visual_layer_does_not_change_fixed_navigation_or_sheets(self):
        start = STYLES.index("VESTRA v3.5")
        block = STYLES[start:]
        self.assertNotIn(".bottomnav{", block)
        self.assertNotIn(".market-sheet", block)
        self.assertNotIn("position:fixed", block)


if __name__ == "__main__":
    unittest.main(verbosity=2)
