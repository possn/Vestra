from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

APP = (ROOT / "app.js").read_text(encoding="utf-8")
INDEX = (ROOT / "index.html").read_text(encoding="utf-8")


class PortfolioPositionsProgressiveTests(unittest.TestCase):
    def test_positions_use_progressive_disclosure(self):
        self.assertIn("let itemsView = 'top5';", APP)
        self.assertIn("itemsView === 'top20' ? 20 : 5", APP)
        self.assertIn("Ver top 20", APP)
        self.assertIn("Ver todas (", APP)
        self.assertIn("Mostrar top 5", APP)
        self.assertIn('onclick="cycleItemsView()"', INDEX)

    def test_search_and_class_filter_are_not_truncated(self):
        self.assertIn("const isSearching = q.length > 0 || cfilter.length > 0;", APP)
        self.assertIn("const shown = isSearching ? src : src.slice(0, itemLimit);", APP)


if __name__ == "__main__":
    unittest.main(verbosity=2)
