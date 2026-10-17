"""Ensure the deliberate market rebuild uses the guarded canonical workflow."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class CanonicalRebuildTriggerTests(unittest.TestCase):
    def test_trigger_declares_post_merge_biotech_and_earnings_rebuild(self):
        trigger = (ROOT / ".github/triggers/market-data-rebuild.txt").read_text(encoding="utf-8")
        self.assertIn("2026-10-17 — rebuild canonical market after #1327", trigger)
        self.assertIn("#1328 earnings confirmed EPS recovery", trigger)

    def test_retry_records_startup_budget_root_cause(self):
        trigger = (ROOT / ".github/triggers/market-data-rebuild.txt").read_text(encoding="utf-8")
        self.assertIn("#1330 trims columnar startup float tails", trigger)
        self.assertIn("exceeded startup budget by 9777 bytes", trigger)

    def test_market_workflow_publishes_only_after_coverage_guard(self):
        text = (ROOT / ".github/workflows/update-market-data.yml").read_text(encoding="utf-8")
        self.assertIn("'.github/triggers/market-data-rebuild.txt'", text)
        self.assertIn("steps.coverage_guard.outcome == 'success'", text)
        self.assertIn("scripts/defer_main_publish_if_code_pr.py", text)


if __name__ == "__main__":
    unittest.main()
