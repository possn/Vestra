"""Offline tests: vendor candidates are never promoted into verified cash."""
import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path

from scripts.discovery_dividend_candidates import (
    merge_candidates, normalise_candidates, scan, select_for_scan,
    quote_currency_provenance, provenance_coverage,
)
from scripts.discovery_dividend_evidence import load_verified_ledger


class CandidateTests(unittest.TestCase):
    def test_rotation_is_bounded_and_deterministic(self):
        snapshots = [{"date": "2026-10-01", "observations": {
            f"T{i}": {"opportunity_score": i, "currency": "USD"}
            for i in range(30)
        }}]
        date = dt.date(2026, 11, 5)
        a = select_for_scan(snapshots, date, batch_size=4)
        self.assertEqual(a, select_for_scan(snapshots, date, batch_size=4))
        self.assertEqual(len(a), 4)
        self.assertEqual(len(set(t[0] for t in a)), 4)

    def test_no_payment_date_or_false_verified_status(self):
        day = dt.date(2026, 11, 5)
        # The normaliser accepts .items(); no optional pandas dependency in CI.
        series = {
            dt.datetime(2026, 10, 12): 0.1,
            dt.datetime(2026, 12, 12): 0.2,
        }
        rows = normalise_candidates("AAA", "USD", series, checked_at=day)
        self.assertEqual(len(rows), 1)
        self.assertIsNone(rows[0]["payment_date"])
        self.assertIsNone(rows[0]["issuer_source_url"])
        self.assertEqual(rows[0]["status"], "pending_issuer_verification")
        self.assertEqual(rows[0]["source_vendor"], "Yahoo Finance")

    def test_idempotent_merge_and_reject_pretend_confirmation(self):
        candidate = normalise_candidates(
            "AAA", "USD",
            {dt.datetime(2026, 10, 12): 0.2},
            checked_at=dt.date(2026, 11, 5),
        )[0]
        existing = {"schema_version": 1, "candidates": [candidate]}
        self.assertEqual(len(merge_candidates(existing, [candidate])), 1)
        with self.assertRaisesRegex(ValueError, "cannot contain confirmed"):
            merge_candidates(existing, [{**candidate, "status": "confirmed"}])

    def test_scanner_reports_vendor_failure_as_failure_not_zero_cash(self):
        history = {"snapshots": [{"date": "2026-11-01", "observations": {
            "AAA": {"opportunity_score": 70, "currency": "USD"}
        }}]}
        def unavailable(_):
            raise TimeoutError("vendor unavailable")
        report = scan(history, {"schema_version": 1, "candidates": []},
                      dt.date(2026, 11, 5), unavailable)
        self.assertEqual(len(report["failed_tickers"]), 1)
        self.assertEqual(report["candidates"], [])
        self.assertEqual(report["status"], "candidates_only_unverified")

    def test_complete_outage_is_explicit_and_preserves_existing_candidates(self):
        history = {"snapshots": [{"date": "2026-11-01", "observations": {
            "AAA": {"opportunity_score": 70, "currency": "USD"},
            "BBB": {"opportunity_score": 65, "currency": "USD"},
        }}]}
        old = normalise_candidates("OLD", "USD", {
            dt.datetime(2026, 10, 12): 0.2
        }, checked_at=dt.date(2026, 11, 5))[0]
        def offline(_):
            raise TimeoutError("provider offline")
        result = scan(history, {"schema_version": 1, "candidates": [old]},
                      dt.date(2026, 11, 6), offline)
        self.assertEqual(result["collection_status"], "source_unavailable")
        self.assertEqual(result["successful_tickers"], [])
        self.assertEqual(len(result["failed_tickers"]), 2)
        self.assertEqual(result["candidates"], [old])

    def test_empty_verified_history_is_not_a_successful_scan(self):
        result = scan({"snapshots": []}, {"schema_version": 1, "candidates": []},
                      dt.date(2026, 11, 6), lambda ticker: {})
        self.assertEqual(result["collection_status"], "no_targets")
        self.assertEqual(result["successful_tickers"], [])

    def test_partial_failure_is_visible_and_eligible_for_publication(self):
        history = {"snapshots": [{"date": "2026-11-01", "observations": {
            "AAA": {"opportunity_score": 70, "currency": "USD"},
            "BBB": {"opportunity_score": 65, "currency": "USD"},
        }}]}
        def fetch(ticker):
            if ticker == "BBB":
                raise TimeoutError()
            return {dt.datetime(2026, 10, 12): 0.2}
        result = scan(history, {"schema_version": 1, "candidates": []},
                      dt.date(2026, 11, 6), fetch)
        self.assertEqual(result["collection_status"], "partial_failure")
        self.assertEqual(result["successful_tickers"], ["AAA"])
        self.assertEqual(len(result["failed_tickers"]), 1)

    def test_uk_pence_quote_is_not_silently_treated_as_cash_dividend_unit(self):
        self.assertEqual(quote_currency_provenance("GBp")["quote_unit"], "minor")
        self.assertEqual(quote_currency_provenance("GBX")["quote_unit_factor"], 100)
        self.assertEqual(quote_currency_provenance("GBP")["quote_unit"], "major")
        candidate = normalise_candidates(
            "BBY.L", "", {dt.datetime(2026, 10, 29): 4.7},
            checked_at=dt.date(2026, 11, 6), vendor_quote_currency="GBp"
        )[0]
        self.assertIsNone(candidate["currency_hint"])
        self.assertEqual(candidate["vendor_quote_currency_raw"], "GBp")
        self.assertEqual(candidate["vendor_quote_currency"], "GBP")
        self.assertEqual(candidate["vendor_quote_unit"], "minor")
        self.assertEqual(candidate["vendor_quote_unit_factor"], 100)
        self.assertEqual(candidate["amount_per_share"], 4.7)
        self.assertEqual(candidate["dividend_amount_unit"], "unverified")

    def test_quote_currency_is_recorded_but_dividend_currency_stays_unknown(self):
        history = {"snapshots": [{"date": "2026-11-01", "observations": {
            "BAC": {"opportunity_score": 80, "currency": ""}
        }}]}
        report = scan(history, {"schema_version": 1, "candidates": []},
                      dt.date(2026, 11, 6),
                      lambda _: ({dt.datetime(2026, 9, 4): 0.32}, "USD"))
        dividend = report["candidates"][0]
        self.assertIsNone(dividend["currency_hint"])
        self.assertEqual(dividend["vendor_quote_currency"], "USD")
        self.assertEqual(dividend["vendor_quote_unit"], "major")
        self.assertEqual(dividend["dividend_amount_unit"], "unverified")
        self.assertEqual(report["collection_status"], "complete")

    def test_repeat_scan_enriches_missing_quote_provenance_without_duplicate(self):
        original = normalise_candidates(
            "BBY.L", "", {dt.datetime(2026, 10, 29): 4.7},
            checked_at=dt.date(2026, 11, 6)
        )[0]
        newer = normalise_candidates(
            "BBY.L", "", {dt.datetime(2026, 10, 29): 4.7},
            checked_at=dt.date(2026, 11, 7), vendor_quote_currency="GBp"
        )[0]
        combined = merge_candidates(
            {"schema_version": 1, "candidates": [original]}, [newer]
        )
        self.assertEqual(len(combined), 1)
        self.assertEqual(combined[0]["first_seen_at"], "2026-11-06")
        self.assertEqual(combined[0]["vendor_quote_unit"], "minor")
        self.assertIsNone(combined[0]["currency_hint"])

    def test_quote_coverage_discloses_retained_and_selected_cohorts(self):
        old = normalise_candidates(
            "OLD", "", {dt.datetime(2025, 10, 12): 0.2},
            checked_at=dt.date(2026, 11, 6)
        )[0]
        gbp = normalise_candidates(
            "BBY.L", "", {dt.datetime(2026, 10, 29): 4.7},
            checked_at=dt.date(2026, 11, 6), vendor_quote_currency="GBp"
        )[0]
        usd = normalise_candidates(
            "BAC", "", {dt.datetime(2026, 9, 4): 0.32},
            checked_at=dt.date(2026, 11, 6), vendor_quote_currency="USD"
        )[0]
        result = provenance_coverage([old, gbp, usd], ["BAC", "BBY.L"])
        all_stats = result["all_candidates"]
        selected = result["selected_ticker_candidates"]
        self.assertEqual(all_stats["candidate_count"], 3)
        self.assertEqual(all_stats["quote_denomination_coverage_pct"], 66.67)
        self.assertEqual(all_stats["quote_denomination_unknown"], 1)
        self.assertEqual(selected["quote_denomination_coverage_pct"], 100)
        self.assertEqual(selected["minor_quote_unit_count"], 1)
        self.assertEqual(selected["cash_dividend_currency_verified"], 0)
        self.assertEqual(selected["cash_dividend_unit_unverified"], 2)
        self.assertEqual(result["selected_ticker_count"], 2)

    def test_empty_coverage_is_unknown_not_fabricated_zero(self):
        stats = provenance_coverage([], [])["all_candidates"]
        self.assertIsNone(stats["quote_denomination_coverage_pct"])
        self.assertEqual(stats["candidate_count"], 0)

    def test_scan_report_has_quote_coverage_but_no_cash_confirmation(self):
        history = {"snapshots": [{"date": "2026-11-01", "observations": {
            "BAC": {"opportunity_score": 75, "currency": ""}
        }}]}
        report = scan(history, {"schema_version": 1, "candidates": []},
                      dt.date(2026, 11, 6),
                      lambda _: ({dt.datetime(2026, 9, 4): 0.32}, "USD"))
        stats = report["quote_provenance_coverage"]["all_candidates"]
        self.assertEqual(stats["quote_denomination_coverage_pct"], 100)
        self.assertEqual(stats["cash_dividend_currency_verified"], 0)
        self.assertEqual(report["candidates"][0]["status"],
                         "pending_issuer_verification")

    def test_ledger_missing_is_optional_but_corruption_is_fatal(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "verified_dividend_events.json"
            self.assertIsNone(load_verified_ledger(path))
            path.write_text("{not-json", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Corrupt verified"):
                load_verified_ledger(path)
            path.write_text("null", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "cannot be null"):
                load_verified_ledger(path)
            path.write_text(json.dumps({"schema_version": 1, "events": []}))
            self.assertEqual(load_verified_ledger(path)["events"], [])


if __name__ == "__main__":
    unittest.main()
