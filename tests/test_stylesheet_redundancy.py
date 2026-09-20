from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class StylesheetRedundancyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.styles = (ROOT / "styles.css").read_text(encoding="utf-8")
        cls.market = (ROOT / "market.css").read_text(encoding="utf-8")
        cls.index = (ROOT / "index.html").read_text(encoding="utf-8")

    def test_shared_ghost_hover_rule_has_one_owner(self):
        rule = ".btn--ghost:hover { background: var(--card2); border-color: var(--vio); color: var(--vio); }"
        self.assertEqual(self.styles.count(rule), 1)

    def test_market_scrollbar_and_hidden_sheet_rules_are_not_duplicated(self):
        self.assertEqual(self.market.count(".market-chipbar::-webkit-scrollbar"), 1)
        self.assertEqual(self.market.count("#marketSheet[hidden]{display:none!important}"), 1)

    def test_clean_stylesheet_generation_is_explicit(self):
        self.assertIn("styles.css?v=20260920v4", self.index)
        self.assertIn("market.css?v=20260920v2", self.index)


if __name__ == "__main__":
    unittest.main(verbosity=2)
