from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class MarketDataRebuildTriggerTests(unittest.TestCase):
    def test_market_data_workflow_watches_explicit_rebuild_marker(self):
        workflow = (ROOT / ".github" / "workflows" / "update-market-data.yml").read_text(encoding="utf-8")
        self.assertIn("'.github/triggers/market-data-rebuild.txt'", workflow)
        self.assertIn("python postprocess_market.py", workflow)
        self.assertIn("python build_market_shards.py", workflow)

    def test_current_rebuild_marker_targets_latest_opportunity_context(self):
        marker = (ROOT / ".github" / "triggers" / "market-data-rebuild.txt").read_text(encoding="utf-8").lower()
        for token in (
            "market regime",
            "binary-event risk",
            "revision freshness",
            "valuation breadth",
            "etf rotation consensus",
        ):
            self.assertIn(token, marker)


if __name__ == "__main__":
    unittest.main(verbosity=2)
