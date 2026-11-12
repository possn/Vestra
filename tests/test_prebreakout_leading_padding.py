"""Bounded Yahoo multi-ticker outer-join padding must not corrupt OHLCV windows."""
import importlib.util
import unittest
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "prebreakout_leading_padding", ROOT / "scripts" / "refresh_prebreakout_scanner.py")
scanner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scanner)


def rows(count=240):
    day = date(2026, 11, 11)
    return [
        {"date": (day - timedelta(days=count - i)).isoformat(),
         "close": 80.0 + i * .1, "high": 81.0 + i * .1,
         "low": 79.0 + i * .1, "volume": 1000}
        for i in range(count)
    ]


def empty(day):
    return {"date": day, "close": None, "high": None, "low": None, "volume": None}


class LeadingPaddingTests(unittest.TestCase):
    def test_absent_prefix_dates_only_are_trimmed(self):
        observed = rows()
        raw = [empty("2025-01-01"), empty("2025-01-02"), *observed]
        cleaned, dropped = scanner.trim_leading_provider_padding(raw)
        self.assertEqual(dropped, 2)
        self.assertEqual(cleaned, observed)
        self.assertEqual(len(cleaned), 240)

    def test_interior_invalid_bar_remains_and_scan_fails_closed(self):
        observed = rows()
        observed[120] = empty(observed[120]["date"])
        cleaned, dropped = scanner.trim_leading_provider_padding(
            [empty("2025-01-01"), *observed])
        self.assertEqual(dropped, 1)
        self.assertEqual(len(cleaned), 240)
        audit = {}
        self.assertIsNone(scanner.scan_bars("GAPPED", cleaned, date(2026, 11, 12), audit=audit))
        self.assertEqual(audit["invalid_ohlcv_detail"], "invalid_or_missing_close")
        self.assertEqual(audit["missing_close_bar_location"], "interior")

    def test_partial_prefix_and_invalid_dates_must_not_be_trimmed(self):
        partial = empty("2025-01-01")
        partial["volume"] = 1000
        for first in (partial, empty("not-a-date"), {"date": "2025-01-01"}):
            with self.subTest(first=first):
                raw = [first, *rows()]
                cleaned, dropped = scanner.trim_leading_provider_padding(raw)
                self.assertEqual(dropped, 0)
                self.assertEqual(cleaned, raw)

    def test_trailing_null_bar_stays_unusable(self):
        raw = [*rows(), empty("2026-11-11")]
        cleaned, dropped = scanner.trim_leading_provider_padding(raw)
        self.assertEqual(dropped, 0)
        self.assertEqual(cleaned, raw)
        audit = {}
        self.assertIsNone(scanner.scan_bars("TRAIL", cleaned, date(2026, 11, 12), audit=audit))
        self.assertEqual(audit["invalid_ohlcv_detail"], "invalid_or_missing_close")
        self.assertEqual(audit["missing_close_bar_location"], "trailing")

    def test_all_null_frame_is_not_marked_as_ohlcv(self):
        cleaned, dropped = scanner.trim_leading_provider_padding(
            [empty("2025-01-01"), empty("2025-01-02")])
        self.assertEqual(cleaned, [])
        self.assertEqual(dropped, 2)

    def test_prefix_recovery_does_not_relax_structural_gates(self):
        observed = rows()
        cleaned, dropped = scanner.trim_leading_provider_padding([empty("2025-01-01"), *observed])
        self.assertEqual(dropped, 1)
        audit = {}
        scanner.scan_bars("BASE", cleaned, date(2026, 11, 12), audit=audit)
        self.assertNotEqual(audit["first_rejection"], "invalid_ohlcv_or_date")
        self.assertNotEqual(audit["first_rejection"], "passed_structural_gates")


if __name__ == "__main__":
    unittest.main()
