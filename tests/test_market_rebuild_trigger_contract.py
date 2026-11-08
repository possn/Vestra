"""Contract for evidence-gated explicit market-data rebuild after SEC identity changes."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CanonicalMarketRebuildTriggerTests(unittest.TestCase):
    def test_marker_is_a_real_canonical_market_workflow_trigger(self):
        marker = ROOT / ".github/triggers/market-data-rebuild.txt"
        workflow = (ROOT / ".github/workflows/update-market-data.yml").read_text(encoding="utf-8")
        content = marker.read_text(encoding="utf-8")
        self.assertIn("PR #1802 issuer-CIK Form 4 provenance guard", content)
        self.assertIn("publish issuer-identity audit report following PR #1808", content)
        self.assertIn("python insider_identity_audit.py", workflow)
        self.assertIn("'.github/triggers/market-data-rebuild.txt'", workflow)
        self.assertIn("python run_market_pipeline.py", workflow)
        self.assertIn("python normalize_market_provenance.py", workflow)
        self.assertIn("python coverage_guard.py", workflow)
        self.assertIn("if: steps.coverage_guard.outcome == 'success' && steps.publish_window.outputs.defer != 'true'", workflow)
        self.assertIn("bash scripts/publish_with_retry.sh origin main", workflow)


if __name__ == "__main__":
    unittest.main()
