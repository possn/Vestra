"""Observed coverage must reject Boolean or malformed OHLCV just as scan_bars does."""
import importlib.util
import unittest
from datetime import date, timedelta
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location(
    "prebreakout", ROOT/"scripts"/"refresh_prebreakout_scanner.py")
scanner=importlib.util.module_from_spec(spec)
spec.loader.exec_module(scanner)


class VerifiedCoverageMarketEvidenceTests(unittest.TestCase):
    @staticmethod
    def history():
        today=date(2026,11,11)
        return today, [
            {"date":(today-timedelta(days=219-i)).isoformat(),
             "close":100.0,"high":101.0,"low":99.0,"volume":2000.0}
            for i in range(220)
        ]

    def test_verified_coverage_rejects_boolean_fields(self):
        today,good=self.history()
        self.assertTrue(scanner.evaluable_recheck(good,today))
        for field in ("close","high","low","volume"):
            for bad in (True,False):
                with self.subTest(field=field,bad=bad):
                    bars=[dict(row) for row in good]
                    bars[111][field]=bad
                    self.assertFalse(scanner.evaluable_recheck(bars,today))

    def test_verified_coverage_rejects_malformed_bar_records(self):
        today,good=self.history()
        for bad in (None,True,"oops",42,["bad"]):
            with self.subTest(record=repr(bad)):
                bars=list(good)
                bars[111]=bad
                self.assertFalse(scanner.evaluable_recheck(bars,today))

    def test_verified_coverage_rejects_missing_data_without_inventing_bars(self):
        today,good=self.history()
        bars=[dict(row) for row in good]
        bars[111].pop("volume")
        self.assertFalse(scanner.evaluable_recheck(bars,today))


if __name__=="__main__":
    unittest.main()
