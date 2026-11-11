"""Pre-breakout market evidence never converts Boolean OHLCV into prices."""
import importlib.util
import unittest
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "prebreakout", ROOT / "scripts" / "refresh_prebreakout_scanner.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class PrebreakoutBooleanMarketDataTests(unittest.TestCase):
    def test_boolean_price_or_volume_rejected_before_structure(self):
        today = date(2026, 11, 11)
        good = [
            {"date": (today - timedelta(days=219-i)).isoformat(),
             "close": 100.0, "high": 101.0, "low": 99.0, "volume": 2000.0}
            for i in range(220)
        ]
        for field in ("close", "high", "low", "volume"):
            for invalid in (True, False):
                with self.subTest(field=field, invalid=invalid):
                    history = [dict(bar) for bar in good]
                    history[111][field] = invalid
                    audit = {}
                    self.assertIsNone(module.scan_bars(
                        "BAD", history, today, audit=audit))
                    self.assertEqual(
                        audit["first_rejection"], "invalid_ohlcv_or_date")

    def test_valid_numeric_history_keeps_existing_gate(self):
        today = date(2026, 11, 11)
        history = [
            {"date": (today - timedelta(days=219-i)).isoformat(),
             "close": 100.0, "high": 101.0, "low": 99.0, "volume": 2000.0}
            for i in range(220)
        ]
        audit = {}
        self.assertIsNone(module.scan_bars("FLAT", history, today, audit=audit))
        self.assertEqual(audit["first_rejection"], "moving_average_structure")


if __name__ == "__main__":
    unittest.main()
