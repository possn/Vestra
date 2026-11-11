"""Small-cap research must not treat Boolean OHLCV as observed prices."""
import importlib.util
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "smallcap_ohlcv_collector",
    ROOT / "research" / "prebreakout" / "smallcap_ohlcv_collector.py")
collector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(collector)


class SmallcapBooleanMarketEvidenceTests(unittest.TestCase):
    def test_boolean_price_or_volume_is_invalid_ohlcv(self):
        class Frame:
            empty = False
            def __init__(self, field, value):
                self.field, self.value = field, value

            def iterrows(self):
                start = datetime(2025, 11, 1, tzinfo=timezone.utc)
                for n in range(250):
                    row = {"Open": 10.0, "High": 11.0, "Low": 9.0,
                           "Close": 10.0, "Volume": 600000.0}
                    if n == 80:
                        row[self.field] = self.value
                    yield start + timedelta(days=n), row

        checked_at = datetime(2026, 7, 10, tzinfo=timezone.utc)
        for field in ("Open", "High", "Low", "Close", "Volume"):
            for value in (True, False):
                with self.subTest(field=field, value=value):
                    result = collector.inspect(
                        "TEST", Frame(field, value), "USD", checked_at)
                    self.assertEqual(result["status"], "invalid_ohlcv")

    def test_valid_market_history_retains_research_contract(self):
        class Frame:
            empty = False
            def iterrows(self):
                start = datetime(2025, 11, 1, tzinfo=timezone.utc)
                for n in range(250):
                    yield start + timedelta(days=n), {
                        "Open": 10.0, "High": 11.0, "Low": 9.0,
                        "Close": 10.0, "Volume": 600000.0}

        checked_at = datetime(2026, 7, 10, tzinfo=timezone.utc)
        result = collector.inspect("TEST", Frame(), "USD", checked_at)
        self.assertEqual(result["status"], "evaluable_ohlcv")
        self.assertEqual(result["bars"], 250)
        self.assertEqual(result["verified_prebreakout_setup"], None)


if __name__ == "__main__":
    unittest.main()
