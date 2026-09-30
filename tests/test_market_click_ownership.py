from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MARKET = (ROOT / "market.js").read_text(encoding="utf-8")


class MarketClickOwnershipTests(unittest.TestCase):
    def test_market_clicks_are_scoped_to_market_surfaces(self):
        self.assertEqual(MARKET.count("document.addEventListener('click'"), 0)
        self.assertIn("const marketEventRoots=[$m('viewMarket'),$m('marketSheet')].filter(Boolean);", MARKET)
        self.assertIn("addMarketSurfaceListener('click'", MARKET)

    def test_search_and_filter_events_are_scoped_to_market_view(self):
        self.assertIn("const marketView=$m('viewMarket');", MARKET)
        for event in ("change", "input", "focusin", "focusout"):
            self.assertIn(f"marketView?.addEventListener('{event}'", MARKET)
            self.assertNotIn(f"document.addEventListener('{event}'", MARKET)

    def test_operational_actions_stay_on_canonical_click_owner(self):
        for marker in (
            "function handleDecisionClick(e)",
            "function handleResearchQueueClick(e)",
            "function handleCheckpointClick(e)",
            "function handleActionMapClick(e)",
            "handleDecisionClick(e);",
            "handleResearchQueueClick(e);",
            "handleCheckpointClick(e);",
            "handleActionMapClick(e);",
        ):
            self.assertIn(marker, MARKET)

    def test_operational_semantics_are_preserved(self):
        for selector in (
            "[data-decision-jump]",
            "[data-queue-status]",
            "[data-checkpoint-save]",
            "[data-action-filter]",
        ):
            self.assertIn(selector, MARKET)
        self.assertIn("setResearchQueueState(", MARKET)
        self.assertIn("saveResearchCheckpoint(", MARKET)
        self.assertIn("applyActionMapFilter(", MARKET)


if __name__ == "__main__":
    unittest.main(verbosity=2)
