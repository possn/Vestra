"""Cumulative prospective evidence must never be wiped by corrupt input."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import opportunity_forward_validation as tracker


class StrictHistoryTests(unittest.TestCase):
    def test_explicit_valid_empty_initial_ledger_is_accepted(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "history.json"
            path.write_text(json.dumps({
                "schema_version": 1, "snapshots": [], "outcomes": []
            }), encoding="utf-8")
            result = tracker.load_validation_history(path)
            self.assertEqual(result["schema_version"], 1)
            self.assertEqual(result["outcomes"], [])

    def test_missing_or_invalid_ledger_fails_closed(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "history.json"
            with self.assertRaisesRegex(ValueError, "unavailable"):
                tracker.load_validation_history(path)
            for content in ("", "{broken-json", "null", "[]",
                            '{"schema_version":2,"snapshots":[],"outcomes":[]}',
                            '{"schema_version":1,"snapshots":{},"outcomes":[]}',
                            '{"schema_version":1,"snapshots":[],"outcomes":{}}'):
                path.write_text(content, encoding="utf-8")
                with self.subTest(content=content):
                    with self.assertRaises(ValueError):
                        tracker.load_validation_history(path)

    def test_main_does_not_modify_corrupt_existing_history(self):
        with tempfile.TemporaryDirectory() as root:
            history = Path(root) / "history.json"
            report = Path(root) / "report.json"
            history.write_text('{"schema_version":1,"snapshots":{}}', encoding="utf-8")
            original = history.read_bytes()
            with (mock.patch.object(tracker, "HISTORY", history),
                  mock.patch.object(tracker, "REPORT", report),
                  mock.patch.object(tracker, "current_rows", return_value={"AAA": {"current_price": 1}}),
                  mock.patch.object(tracker, "outcome_price_rows", return_value={"AAA": {"current_price": 1}})):
                with self.assertRaisesRegex(ValueError, "schema"):
                    tracker.main()
            self.assertEqual(history.read_bytes(), original)
            self.assertFalse(report.exists())

    def test_main_does_not_modify_history_if_market_feed_unavailable(self):
        with tempfile.TemporaryDirectory() as root:
            history = Path(root) / "history.json"
            report = Path(root) / "report.json"
            history.write_text(json.dumps({
                "schema_version": 1,
                "snapshots": [{"date": "2026-11-01",
                               "observations": {"AAA": {"opportunity_score": 60, "price": 1}}}],
                "outcomes": [{"cohort_date": "2026-10-01", "ticker": "AAA",
                              "horizon_days": 28, "return_pct": 5}],
            }), encoding="utf-8")
            original = history.read_bytes()
            with (mock.patch.object(tracker, "HISTORY", history),
                  mock.patch.object(tracker, "REPORT", report),
                  mock.patch.object(tracker, "current_rows", return_value={}),
                  mock.patch.object(tracker, "outcome_price_rows", return_value={})):
                with self.assertRaisesRegex(ValueError, "No usable"):
                    tracker.main()
            self.assertEqual(history.read_bytes(), original)
            self.assertFalse(report.exists())


if __name__ == "__main__":
    unittest.main()
