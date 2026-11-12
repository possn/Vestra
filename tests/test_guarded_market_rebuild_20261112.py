"""The explicit market rebuild must keep the canonical evidence guards."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class GuardedMarketRebuildContract(unittest.TestCase):
    def test_marker_requests_a_new_evidence_gated_run(self):
        marker = (ROOT / ".github/triggers/market-data-rebuild.txt").read_text(encoding="utf-8")
        self.assertIn("2026-11-12 — canonical rebuild after PR #1897", marker)

    def test_market_pipeline_guard_and_publish_filters_unchanged(self):
        workflow = (ROOT / ".github/workflows/update-market-data.yml").read_text(encoding="utf-8")
        self.assertIn(".github/triggers/market-data-rebuild.txt", workflow)
        self.assertIn("coverage_guard.outcome == 'success'", workflow)
        self.assertIn("steps.publish_window.outputs.defer != 'true'", workflow)
        self.assertIn("python opportunity_forward_validation.py", workflow)
        self.assertIn("bash scripts/publish_with_retry.sh origin main", workflow)


if __name__ == "__main__":
    unittest.main()
