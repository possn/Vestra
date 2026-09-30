from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MARKET = (ROOT / "market.js").read_text(encoding="utf-8")


class MarketClickOwnershipTests(unittest.TestCase):
    def test_market_has_one_document_click_owner(self):
        self.assertEqual(MARKET.count("document.addEventListener('click'"), 1)

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
