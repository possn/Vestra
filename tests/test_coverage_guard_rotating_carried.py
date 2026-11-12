"""Coverage guard must detect the exact rotating-carried status from run.py."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import coverage_guard as guard


class RotatingCarriedCoverageGuardTests(unittest.TestCase):
    def check_row(self, row):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "stocks.json"
            target = Path(tmp) / "coverage_guard.json"
            source.write_text(json.dumps({"stocks": [row]}), encoding="utf-8")
            with patch.object(guard, "STOCKS_PATH", str(source)), patch.object(
                guard, "OUT_PATH", str(target)
            ):
                outcome = guard.main()
                report = json.loads(target.read_text(encoding="utf-8"))
        return outcome, report

    def test_active_carried_opportunity_is_rejected(self):
        row = {
            "ticker": "STALE", "quote_type": "EQUITY",
            "pipeline_status": "equity_carried_forward_rotating",
            "opportunity_score": 93, "opportunity_eligible": True,
            "scanner_tags": ["best_opportunities"],
            "low52_status": "opportunity", "recovery_status": "confirmed",
        }
        status, report = self.check_row(row)
        self.assertEqual(status, 1)
        self.assertGreaterEqual(
            report["violation_counts"].get("carried_row_has_active_opportunity_rank", 0), 1
        )
        self.assertGreaterEqual(report["violation_counts"].get("catalog_row_ranked", 0), 1)
        self.assertEqual(report["violation_counts"].get("carried_row_has_active_low52"), 1)
        self.assertEqual(report["violation_counts"].get("carried_row_has_positive_recovery"), 1)

    def test_postprocess_suppressed_carried_row_passes(self):
        row = {
            "ticker": "STALE", "quote_type": "EQUITY",
            "pipeline_status": "equity_carried_forward_rotating",
            "opportunity_score": None, "opportunity_eligible": False,
            "scanner_tags": [], "low52_status": "insufficient",
            "recovery_status": "insufficient",
        }
        status, report = self.check_row(row)
        self.assertEqual(status, 0)
        self.assertEqual(report["violation_counts"], {})


if __name__ == "__main__":
    unittest.main()
