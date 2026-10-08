"""Vestra 2.0 readiness baseline contract.

This test keeps the rollout gates explicit while the redesign is staged.
"""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "docs" / "vestra-2-readiness-baseline.md"


class Vestra2ReadinessBaselineTests(unittest.TestCase):
    def test_readiness_document_tracks_critical_invariants(self):
        document = BASELINE.read_text(encoding="utf-8")
        for required in (
            "Broker-import identity and idempotency",
            "missing / stale price",
            "portfolio factor",
            "iPhone PWA",
            "Score",
            "Risk Gate",
            "reversible feature flag",
            "Runtime JavaScript syntax success",
            "Architecture invariants success",
            "Browser E2E including WebKit iPhone success",
            "expected_head_sha",
        ):
            with self.subTest(required=required):
                self.assertIn(required.casefold(), document.casefold())


if __name__ == "__main__":
    unittest.main()
