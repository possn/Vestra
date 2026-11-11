"""Pre-breakout moving-average diagnostics distinguish observed rejection causes."""
import importlib.util
import unittest
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "prebreakout", ROOT / "scripts" / "refresh_prebreakout_scanner.py")
scanner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scanner)


class MovingAverageFailureAuditTests(unittest.TestCase):
    @staticmethod
    def flat_bars(today):
        return [{"date": (today - timedelta(days=219-i)).isoformat(),
                 "close": 100, "high": 101, "low": 99, "volume": 2000}
                for i in range(220)]

    def test_strict_flat_data_reports_overlapping_failure_reasons(self):
        today = date(2026, 11, 11)
        trace = {}
        result = scanner.scan_bars("FLAT", self.flat_bars(today), today,
                                   strict_quality=True, audit=trace)
        self.assertIsNone(result)
        self.assertEqual(trace["first_rejection"], "moving_average_structure")
        self.assertEqual(set(trace["moving_average_failed_checks"]), {
            "price_above_ma50", "ma50_above_ma150", "ma150_above_ma200",
            "ma50_rising_10", "ma150_rising_10", "ma200_rising_10"})

    def test_legacy_diagnostics_respect_legacy_gate(self):
        today = date(2026, 11, 11)
        trace = {}
        scanner.scan_bars("FLAT", self.flat_bars(today), today,
                          strict_quality=False, audit=trace)
        self.assertEqual(trace["first_rejection"], "moving_average_structure")
        self.assertEqual(set(trace["moving_average_failed_checks"]), {
            "price_above_ma150", "ma50_above_ma200",
            "ma50_rising_10", "ma150_rising_10", "ma200_rising_10"})

    def test_publication_labels_nonexclusive_scope(self):
        src = (ROOT / "scripts" / "refresh_prebreakout_scanner.py").read_text()
        self.assertIn('"moving_average_failure_audit":', src)
        self.assertIn("nonexclusive_failed_conditions_not_independent_gate_pass_rates", src)
        self.assertIn('"first_rejected_rows":gate_exclusions.get("moving_average_structure",0)', src)


if __name__ == "__main__":
    unittest.main()
