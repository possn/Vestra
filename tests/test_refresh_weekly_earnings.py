import importlib.util
from datetime import date, datetime, timezone
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('refresh_weekly_earnings', ROOT / 'scripts' / 'refresh_weekly_earnings.py')
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class FakeRow(dict):
    @property
    def index(self):
        return self.keys()


class FakeFrame:
    def __init__(self, rows):
        self.rows = rows
        self.empty = not rows

    def iterrows(self):
        return iter(self.rows)


class WeeklyEarningsRefreshTests(unittest.TestCase):
    def test_candidates_include_recent_and_near_term_equities_only(self):
        payload = {'stocks':[
            {'ticker':'ADBE','quote_type':'EQUITY','analyst_next_earnings_date':'2026-09-10'},
            {'ticker':'ORCL','quote_type':'EQUITY','analyst_next_earnings_date':'2026-09-15'},
            {'ticker':'OLD','quote_type':'EQUITY','analyst_next_earnings_date':'2026-08-01'},
            {'ticker':'ETF1','quote_type':'ETF','analyst_next_earnings_date':'2026-09-12'},
        ]}
        self.assertEqual(mod.candidate_tickers(payload, today=date(2026,9,12)), ['ADBE','ORCL'])

    def test_yahoo_surprise_percent_is_always_stored_as_fraction(self):
        earnings = FakeFrame([
            (datetime(2026, 9, 10, 20, 0, tzinfo=timezone.utc), FakeRow({
                'Reported EPS': 6.13,
                'EPS Estimate': 6.09,
                'Surprise(%)': 0.71,
            })),
        ])
        snapshot = mod.extract_snapshot(
            earnings,
            now=datetime(2026, 9, 12, 7, 0, tzinfo=timezone.utc),
        )
        self.assertEqual(snapshot['analyst_latest_earnings_date'], '2026-09-10')
        self.assertEqual(snapshot['analyst_latest_eps_actual'], 6.13)
        self.assertEqual(snapshot['analyst_latest_eps_estimate'], 6.09)
        self.assertAlmostEqual(snapshot['analyst_latest_eps_surprise_pct'], 0.0071)
        self.assertIsNone(snapshot['analyst_next_earnings_date'])

    def test_missing_yahoo_surprise_is_computed_as_fraction(self):
        earnings = FakeFrame([
            (datetime(2026, 9, 10, 20, 0, tzinfo=timezone.utc), FakeRow({
                'Reported EPS': 6.13,
                'EPS Estimate': 6.09,
            })),
        ])
        snapshot = mod.extract_snapshot(
            earnings,
            now=datetime(2026, 9, 12, 7, 0, tzinfo=timezone.utc),
        )
        self.assertAlmostEqual(snapshot['analyst_latest_eps_surprise_pct'], 6.13 / 6.09 - 1.0)

    def test_apply_snapshot_preserves_unrelated_startup_fields(self):
        row = {'ticker':'ADBE','name':'Adobe Inc.','score':81,'analyst_next_earnings_date':'2026-09-10'}
        changed = mod.apply_snapshot(row, {
            'analyst_next_earnings_date':None,
            'analyst_latest_earnings_date':'2026-09-10',
            'analyst_latest_eps_estimate':6.09,
            'analyst_latest_eps_actual':6.13,
            'analyst_latest_eps_surprise_pct':0.0071,
        })
        self.assertTrue(changed)
        self.assertEqual(row['name'], 'Adobe Inc.')
        self.assertEqual(row['score'], 81)
        self.assertEqual(row['analyst_latest_eps_actual'], 6.13)
        self.assertIsNone(row['analyst_next_earnings_date'])

    def test_pack_round_trip_keeps_reported_earnings_fields(self):
        payload = {'schema_version':1,'stocks':[
            {'ticker':'ADBE','name':'Adobe Inc.','analyst_latest_earnings_date':'2026-09-10','analyst_latest_eps_actual':6.13},
            {'ticker':'ORCL','name':'Oracle'},
        ]}
        packed = mod.pack_index_payload(payload)
        self.assertEqual(packed['layout'], 'field_rows_v1')
        fields = packed['fields']
        row = dict(zip(fields, packed['rows'][0]))
        self.assertEqual(row['ticker'], 'ADBE')
        self.assertEqual(row['analyst_latest_earnings_date'], '2026-09-10')
        self.assertEqual(row['analyst_latest_eps_actual'], 6.13)

    def test_result_contract_contains_all_dashboard_fields(self):
        expected = {
            'analyst_eps_next_q',
            'analyst_next_earnings_date',
            'analyst_latest_earnings_date',
            'analyst_latest_eps_estimate',
            'analyst_latest_eps_actual',
            'analyst_latest_eps_surprise_pct',
        }
        self.assertEqual(set(mod.RESULT_FIELDS), expected)


if __name__ == '__main__':
    unittest.main(verbosity=2)
