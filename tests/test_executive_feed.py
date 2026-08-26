from pathlib import Path
import json
import unittest

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class ExecutiveFeedTests(unittest.TestCase):
    def test_current_snapshot_keeps_trump_and_top_tens(self):
        data = json.loads(read("data/executives.json"))
        people = data.get("people") or []
        trades = data.get("trades") or []
        self.assertTrue(any(x.get("key") == "executive:donald-trump" for x in people))
        self.assertGreaterEqual(sum(1 for x in trades if x.get("type") == "buy"), 10)
        self.assertGreaterEqual(sum(1 for x in trades if x.get("type") == "sell"), 10)
        self.assertTrue(all(x.get("filing_url") for x in trades[:20]))

    def test_builder_uses_official_filings_and_safe_fallback(self):
        builder = read("scripts/build_executive_feed.py")
        self.assertIn("whitehouse.gov", builder)
        self.assertIn("extapps2.oge.gov", builder)
        self.assertIn("preserving previous valid snapshot", builder)
        self.assertIn("len(trades) < 20 or buys < 10 or sells < 10", builder)
        self.assertIn("unambiguous", builder)

    def test_white_house_split_table_layout_has_semantic_row_parser(self):
        builder = read("scripts/build_executive_feed.py")
        self.assertIn("LOGICAL_ROW_RE", builder)
        self.assertIn("def parse_logical_rows", builder)
        self.assertIn("ILLINOIS TOOL WKS", builder)
        self.assertIn("MCDONALDS CORP", builder)
        self.assertIn("MEDTRONIC", builder)

    def test_ocr_amount_ranges_are_normalized_before_publication(self):
        normalizer = read("scripts/normalize_executive_amounts.py")
        workflow = read(".github/workflows/update-executives.yml")
        self.assertIn("FLEX_RANGE", normalizer)
        self.assertIn("def normalize_trade", normalizer)
        self.assertIn("python scripts/normalize_executive_amounts.py", workflow)
        self.assertLess(
            workflow.index("python scripts/normalize_executive_amounts.py"),
            workflow.index("Validate executive snapshot"),
        )

    def test_scheduled_workflow_refreshes_and_validates_executive_feed(self):
        workflow = read(".github/workflows/update-executives.yml")
        congress_workflow = read(".github/workflows/update-politicians.yml")
        self.assertIn("python scripts/build_executive_feed.py", workflow)
        self.assertIn("data/executives.json", workflow)
        self.assertIn("executive:donald-trump", workflow)
        self.assertIn("top-10 buys unavailable", workflow)
        self.assertIn("top-10 sells unavailable", workflow)
        self.assertNotIn("build_executive_feed.py", congress_workflow)
        self.assertNotIn("data/executives.json", congress_workflow)

    def test_ui_keeps_global_individual_and_favourites_views(self):
        ui = read("politicians.js")
        self.assertIn("TOP 10 COMPRAS", ui)
        self.assertIn("TOP 10 VENDAS", ui)
        self.assertIn("function globalView()", ui)
        self.assertIn("function memberView(m)", ui)
        self.assertIn("vestra-politician-favourites-v2", ui)
        self.assertIn("data-politician-view=\"favourites\"", ui)


if __name__ == "__main__":
    unittest.main(verbosity=2)
