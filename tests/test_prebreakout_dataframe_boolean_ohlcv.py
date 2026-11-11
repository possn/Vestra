"""Dataframe conversion must not launder Boolean OHLCV into 0/1 prices or volume."""
import importlib.util
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("prebreakout", ROOT / "scripts" / "refresh_prebreakout_scanner.py")
scanner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scanner)


class DataframeBooleanOHLCVTests(unittest.TestCase):
    class FakeFrame:
        empty = False

        def __init__(self, field, value):
            self.field = field
            self.value = value

        def iterrows(self):
            start = datetime(2026, 1, 1, tzinfo=timezone.utc)
            for i in range(230):
                row = {"Close": 100.0, "High": 101.0, "Low": 99.0, "Volume": 2000.0}
                if i == 114:
                    row[self.field] = self.value
                yield start + timedelta(days=i), row

    def test_boolean_fields_remain_invalid_after_dataframe_conversion(self):
        for field in ("Close", "High", "Low", "Volume"):
            for bad in (True, False):
                with self.subTest(field=field, value=bad):
                    bars = scanner.dataframe_bars(self.FakeFrame(field, bad))
                    self.assertEqual(len(bars), 230)
                    self.assertIsNone(bars[114][field.lower()])
                    self.assertFalse(scanner.evaluable_recheck(bars, date(2026, 8, 20)))
                    trace = {}
                    self.assertIsNone(scanner.scan_bars("BAD", bars, date(2026, 8, 20), audit=trace))
                    # Price fields are mandatory at parse time. Volume is
                    # checked at later evidence gates, so no first-gate claim.
                    if field != "Volume":
                        self.assertEqual(trace["first_rejection"], "invalid_ohlcv_or_date")

    def test_numpy_boolean_scalar_versions_fail_closed(self):
        # Model NumPy scalar identity without adding a CI dependency.
        def scalar_type(name):
            return type(name, (), {
                "__module__": "numpy",
                "__init__": lambda self, value: setattr(self, "value", value),
                "__float__": lambda self: float(self.value),
            })

        for cls in (scalar_type("bool_"), scalar_type("bool")):
            for field in ("Close", "High", "Low", "Volume"):
                for value in (True, False):
                    with self.subTest(type=cls.__name__, field=field, value=value):
                        bars = scanner.dataframe_bars(self.FakeFrame(field, cls(value)))
                        self.assertEqual(len(bars), 230)
                        self.assertIsNone(bars[114][field.lower()])
                        self.assertFalse(scanner.evaluable_recheck(bars, date(2026, 8, 20)))

    def test_valid_numeric_ohlcv_remains_evaluable(self):
        for field in ("Close", "High", "Low", "Volume"):
            bars = scanner.dataframe_bars(self.FakeFrame(field, 100.0 if field == "Close" else
                101.0 if field == "High" else 99.0 if field == "Low" else 2000.0))
            self.assertEqual(len(bars), 230)
            self.assertTrue(scanner.evaluable_recheck(bars, date(2026, 8, 20)))


if __name__ == "__main__":
    unittest.main()
