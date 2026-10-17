from datetime import date
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from earnings_archive import archive_rows


class EarningsArchiveTests(unittest.TestCase):
    def test_retains_previous_quarters_and_deduplicates(self):
        old = {"events": [{"kind": "earnings", "ticker": "AAA", "date": "2026-07-12",
                             "analyst_latest_eps_actual": 1.4, "source": "yahoo"}]}
        latest = [{"ticker": "AAA", "name": "Alpha", "analyst_latest_earnings_date": "2026-10-10",
                   "analyst_latest_eps_actual": 1.8}]
        result = archive_rows(old, latest, date(2026, 10, 13))
        self.assertEqual([e["date"] for e in result["events"]], ["2026-07-12", "2026-10-10"])
        again = archive_rows(result, latest, date(2026, 10, 13))
        self.assertEqual(len(again["events"]), 2)

    def test_multi_quarter_backfill_keeps_provider_provenance(self):
        rows = [
            {'ticker':'ABC', 'name':'ABC', 'analyst_latest_earnings_date':'2026-07-10', 'analyst_latest_eps_actual':1.1, 'earnings_source':'yahoo:earnings_dates'},
            {'ticker':'ABC', 'name':'ABC', 'analyst_latest_earnings_date':'2026-10-10', 'analyst_latest_eps_actual':1.2, 'earnings_source':'yahoo:earnings_dates'},
        ]
        events = archive_rows({}, rows, date(2026, 10, 13))['events']
        self.assertEqual(len(events), 2)
        self.assertEqual([x['date'] for x in events], ['2026-07-10','2026-10-10'])
        self.assertTrue(all(x['source']=='yahoo:earnings_dates' for x in events))

    def test_no_future_predictions_or_undated_results(self):
        rows = [
            {"ticker": "AAA", "analyst_latest_earnings_date": "2026-11-01"},
            {"ticker": "BBB", "analyst_latest_earnings_date": "wrong"},
            {"ticker": "CCC", "analyst_latest_earnings_date": "2023-01-01"},
        ]
        self.assertEqual(archive_rows({}, rows, date(2026, 10, 13))["events"], [])

    def test_official_value_precedence(self):
        old = {"events": [{"kind": "earnings", "ticker": "AAA", "date": "2026-10-13", "source": "official:issuer", "analyst_latest_eps_actual": 0.09}]}
        latest = [{"ticker": "AAA", "analyst_latest_earnings_date": "2026-10-13", "analyst_latest_eps_actual": 2.59, "earnings_source": "yahoo:earnings_dates"}]
        event = archive_rows(old, latest, date(2026, 10, 17))["events"][0]
        self.assertEqual(event["analyst_latest_eps_actual"], 0.09)

    def test_preserves_verified_eps_if_new_snapshot_missing_eps(self):
        prior = {"events": [{"kind": "earnings", "ticker": "A", "date": "2026-10-01",
                              "analyst_latest_eps_actual": 2.1, "source": "yahoo"}]}
        new = [{"ticker": "A", "analyst_latest_earnings_date": "2026-10-01"}]
        event = archive_rows(prior, new, date(2026, 10, 13))["events"][0]
        self.assertEqual(event["analyst_latest_eps_actual"], 2.1)
        self.assertEqual(event["source"], "yahoo")


if __name__ == "__main__":
    unittest.main()
