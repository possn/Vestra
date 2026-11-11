"""Malformed pre-breakout bars must abstain without raising out of scan_bars."""
import importlib.util
import unittest
from datetime import date
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("prebreakout",ROOT/"scripts/refresh_prebreakout_scanner.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class MalformedOHLCVBarTests(unittest.TestCase):
    def test_nonmapping_bars_fail_closed_with_observed_reason(self):
        today=date(2026,11,11)
        valid={"date":"2026-11-10","close":100,"high":101,"low":99,"volume":1000}
        for malformed in (None, 42, "bad", ["bad"], True):
            with self.subTest(bar=repr(malformed)):
                audit={}
                self.assertIsNone(mod.scan_bars("BAD", [valid,malformed], today, audit=audit))
                self.assertEqual(audit["first_rejection"], "invalid_ohlcv_or_date")

    def test_valid_mapping_is_not_rejected_as_invalid_type(self):
        trace={}
        bars=[{"date":"2026-11-10","close":100,"high":101,"low":99,"volume":1000}]
        self.assertIsNone(mod.scan_bars("SHORT",bars,date(2026,11,11),audit=trace))
        self.assertEqual(trace["first_rejection"],"insufficient_daily_sessions")


if __name__=="__main__":
    unittest.main()
