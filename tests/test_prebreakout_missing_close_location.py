"""Observe first invalid Close without repairing an OHLCV history."""
import importlib.util
import unittest
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "prebreakout_missing_close", ROOT / "scripts" / "refresh_prebreakout_scanner.py")
scanner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scanner)


class MissingClosePositionTests(unittest.TestCase):
    def setUp(self):
        start = date(2025, 10, 1)
        self.bars = [
            {"date": (start + timedelta(days=i)).isoformat(),
             "close": 100.0, "high": 101.0, "low": 99.0, "volume": 1000.0}
            for i in range(230)
        ]

    def test_aggregate_diagnostic_distinguishes_union_padding(self):
        for ix, expected in [(0, "leading"), (115, "interior"), (229, "trailing")]:
            for pattern, high, low in [
                ("all_ohlc_missing", None, None),
                ("close_only_missing", 101.0, 99.0),
                ("partial_ohlc_missing", None, 99.0)
            ]:
                with self.subTest(ix=ix, pattern=pattern):
                    bars = [dict(bar) for bar in self.bars]
                    bars[ix].update(close=None, high=high, low=low)
                    audit = {}
                    self.assertIsNone(scanner.scan_bars("PAD", bars, date(2026, 5, 20), audit=audit))
                    self.assertEqual(audit["first_rejection"], "invalid_ohlcv_or_date")
                    self.assertEqual(audit["invalid_ohlcv_detail"], "invalid_or_missing_close")
                    self.assertEqual(audit["missing_close_bar_location"], expected)
                    self.assertEqual(audit["missing_close_pattern"], pattern)
                    self.assertEqual(len(bars), 230)
                    self.assertIsNone(bars[ix]["close"])

    def test_invalid_nonnull_close_is_separate(self):
        bars = [dict(bar) for bar in self.bars]
        bars[0]["close"] = "not a price"
        audit = {}
        scanner.scan_bars("BAD", bars, date(2026, 5, 20), audit=audit)
        self.assertEqual(audit["missing_close_pattern"], "invalid_nonnull_close")


if __name__ == "__main__":
    unittest.main()
