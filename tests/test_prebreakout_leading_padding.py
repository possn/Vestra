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
    def test_full_null_batch_suffix_removed_without_imputing_prices(self):
        observed=rows()
        cleaned,dropped=scanner.trim_trailing_provider_padding(
            [*observed,empty("2026-11-11"),empty("2026-11-12")])
        self.assertEqual(dropped,2)
        self.assertEqual(cleaned,observed)
        audit={}
        scanner.scan_bars("NO_PIVOT",cleaned,date(2026,11,12),audit=audit)
        self.assertNotEqual(audit["first_rejection"],"invalid_ohlcv_or_date")

    def test_interior_null_or_partial_suffix_remains_fatal(self):
        observed=rows()
        observed[80]=empty(observed[80]["date"])
        cleaned,dropped=scanner.trim_trailing_provider_padding(
            [*observed,empty("2026-11-11")])
        self.assertEqual(dropped,1)
        audit={}
        scanner.scan_bars("GAP",cleaned,date(2026,11,12),audit=audit)
        self.assertEqual(audit["first_rejection"],"invalid_ohlcv_or_date")
        partial=empty("2026-11-11");partial["volume"]=1000
        self.assertEqual(scanner.trim_trailing_provider_padding([*rows(),partial])[1],0)

    def test_all_empty_or_invalid_trailing_dates_not_cleaned(self):
        only_empty=[empty("2026-11-10"),empty("2026-11-11")]
        self.assertEqual(scanner.trim_trailing_provider_padding(only_empty),(only_empty,0))
        invalid=empty("bad-date")
        self.assertEqual(scanner.trim_trailing_provider_padding([*rows(),invalid])[1],0)

    def test_stale_history_stays_stale_after_suffix_removal(self):
        older=rows()
        cleaned,_=scanner.trim_trailing_provider_padding(
            [*older,empty("2026-11-11")])
        audit={}
        scanner.scan_bars("STALE",cleaned,date(2026,12,1),audit=audit)
        self.assertEqual(audit["first_rejection"],"stale_or_future_daily_session")

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

    def test_interior_gap_diagnostic_counts_without_mutating_history(self):
        observed = rows()
        observed[40] = empty("2026-01-05")  # Monday; calendar not evidence of a session
        observed[41] = empty("2026-01-06")
        observed[110] = empty("2026-02-07")  # Saturday, deliberately synthetic
        original = [dict(row) for row in observed]
        audit = scanner.interior_all_null_gap_diagnostic(observed)
        self.assertEqual(audit["gap_runs"], 2)
        self.assertEqual(audit["gap_rows"], 3)
        self.assertEqual(audit["single_day_runs"], 1)
        self.assertEqual(audit["multi_day_runs"], 1)
        self.assertEqual(audit["max_run_rows"], 2)
        self.assertEqual(audit["weekday_rows"], 2)
        self.assertEqual(audit["weekend_rows"], 1)
        self.assertEqual(observed, original)
        trace = {}
        self.assertIsNone(scanner.scan_bars("GAPPED", observed, date(2026, 11, 12), audit=trace))
        self.assertEqual(trace["first_rejection"], "invalid_ohlcv_or_date")

    def test_prefix_and_trailing_gaps_not_reported_as_interior(self):
        raw = [empty("2025-01-01"), *rows(), empty("2026-11-11")]
        audit = scanner.interior_all_null_gap_diagnostic(raw)
        self.assertEqual(audit["gap_rows"], 0)
        self.assertEqual(audit["gap_runs"], 0)
        self.assertEqual(scanner.interior_all_null_gap_diagnostic([])["gap_rows"], 0)

    def test_partial_bar_does_not_count_as_all_null_gap(self):
        observed = rows()
        observed[100] = dict(observed[100], close=None)
        audit = scanner.interior_all_null_gap_diagnostic(observed)
        self.assertEqual(audit["gap_rows"], 0)
        trace = {}
        self.assertIsNone(scanner.scan_bars("PARTIAL", observed, date(2026, 11, 12), audit=trace))
        self.assertEqual(trace["first_rejection"], "invalid_ohlcv_or_date")

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
