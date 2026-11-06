"""Offline tests: vendor candidates are never promoted into verified cash."""
import datetime as dt
import json
import tempfile
import unittest
from pathlib import Path

from scripts.discovery_dividend_candidates import (
    merge_candidates, normalise_candidates, scan, select_for_scan,
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
