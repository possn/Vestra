from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.js").read_text(encoding="utf-8")
INDEX = (ROOT / "index.html").read_text(encoding="utf-8")


class PortfolioProgressiveListTests(unittest.TestCase):
    def test_positions_render_progressively(self):
        self.assertIn("PORTFOLIO_ITEMS_INITIAL = 10", APP)
        self.assertIn("PORTFOLIO_ITEMS_PAGE = 25", APP)
        self.assertIn("src.slice(0, Math.min(itemsVisibleLimit, src.length))", APP)
        self.assertIn("function togglePortfolioItems()", APP)
        self.assertIn("itemsVisibleLimit + PORTFOLIO_ITEMS_PAGE", APP)

    def test_search_and_filters_keep_full_result_visibility(self):
        self.assertIn("const shown = isSearching ? src :", APP)

    def test_portfolio_toggle_uses_progressive_handler(self):
        self.assertIn('onclick="togglePortfolioItems()"', INDEX)
        self.assertNotIn("itemsExpanded=!itemsExpanded", INDEX)


if __name__ == "__main__":
    unittest.main(verbosity=2)
