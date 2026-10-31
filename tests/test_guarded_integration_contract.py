"""Guarded auto-integration safety contract. No credentials are read or exposed."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/vestra-guarded-pr-integration.yml"


class GuardedIntegrationContract(unittest.TestCase):
    def test_opt_in_token_and_four_exact_head_gates(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        for expected in (
            "secrets.VESTRA_INTEGRATION_TOKEN",
            "vestra-auto-merge",
            "runtime-js-syntax.yml",
            "architecture-invariants.yml",
            "browser-e2e.yml",
            "webkit-iphone (1)",
            "webkit-iphone (2)",
            "fresh.head.sha!==head",
            "currentMain!==main",
            "latestCompare.behind_by!==0",
            "sha:head,merge_method:'squash'",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, source)


if __name__ == "__main__":
    unittest.main()
