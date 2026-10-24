import importlib.util
from datetime import date, datetime, timezone
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
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
    def test_backfills_confirmed_historical_quarters_without_scheduled_only_dates(self):
        now = datetime(2026,10,13,tzinfo=timezone.utc)
        frame = FakeFrame([
            (datetime(2026,7,12,tzinfo=timezone.utc), FakeRow({"Reported EPS":1.5,"EPS Estimate":1.2,"Surprise(%)":25})),
            (datetime(2026,9,2,tzinfo=timezone.utc), FakeRow({"Reported EPS":2.0,"EPS Estimate":1.9})),
            (datetime(2026,11,2,tzinfo=timezone.utc), FakeRow({"EPS Estimate":2.4}))
        ])
        rows = mod.extract_reported_history("AAA", frame, now)
        self.assertEqual([r["analyst_latest_earnings_date"] for r in rows], ["2026-07-12", "2026-09-02"])
        self.assertEqual(rows[0]["analyst_latest_eps_surprise_pct"], .25)
        self.assertTrue(all(r["earnings_source"] == "yahoo:earnings_dates" for r in rows))

    def test_candidates_include_recent_and_near_term_equities_only(self):
        payload = {'stocks':[
            {'ticker':'ADBE','quote_type':'EQUITY','analyst_next_earnings_date':'2026-09-10'},
            {'ticker':'ORCL','quote_type':'EQUITY','analyst_next_earnings_date':'2026-09-15'},
            {'ticker':'OLD','quote_type':'EQUITY','analyst_next_earnings_date':'2026-08-01'},
            {'ticker':'ETF1','quote_type':'ETF','analyst_next_earnings_date':'2026-09-12'},
        ]}
        self.assertEqual(mod.candidate_tickers(payload, today=date(2026,9,12)), ['ADBE','ORCL','OLD'])

    def test_recent_reports_win_bounded_candidate_slots_over_alphabetical_tickers(self):
        payload = {"stocks": [
            *({"ticker": f"A{i:03d}", "quote_type": "EQUITY",
               "analyst_next_earnings_date": "2026-11-20"} for i in range(80)),
            {"ticker": "JPM", "quote_type": "EQUITY", "analyst_next_earnings_date": "2026-10-13"},
            {"ticker": "JNJ", "quote_type": "EQUITY", "analyst_next_earnings_date": "2026-10-13"},
            {"ticker": "GS", "quote_type": "EQUITY", "analyst_next_earnings_date": "2026-10-13"},
        ]}
        candidates = mod.candidate_tickers(payload, today=date(2026, 10, 17))
        self.assertEqual(candidates[:3], ["GS", "JNJ", "JPM"])
        self.assertEqual(len(candidates), 50)

    def test_stale_large_caps_are_checked_each_rotation_without_extra_requests(self):
        payload = {"stocks": [
            *({"ticker": f"D{i:03d}", "quote_type": "EQUITY",
               "analyst_next_earnings_date": "2026-10-18"} for i in range(65)),
            *({"ticker": f"U{i:03d}", "quote_type": "EQUITY",
               "market_cap": 10_000_000_000 - i} for i in range(90)),
            {"ticker": "JPM", "quote_type": "EQUITY", "market_cap": 600_000_000_000,
             "analyst_latest_earnings_date": "2026-07-14"},
            {"ticker": "JNJ", "quote_type": "EQUITY", "market_cap": 400_000_000_000,
             "analyst_latest_earnings_date": "2026-07-14"},
            {"ticker": "GS", "quote_type": "EQUITY", "market_cap": 150_000_000_000,
             "analyst_latest_earnings_date": "2026-07-14"},
        ]}
        for slot in (0, 1, 5, 7):
            selected = mod.candidate_tickers(payload, today=date(2026, 10, 17), rotation_slot=slot)
            self.assertEqual(len(selected), 80)
            self.assertEqual(set(selected[50:53]), {"JPM", "JNJ", "GS"})
            self.assertEqual(len(set(selected)), 80)
            self.assertEqual(len([ticker for ticker in selected if ticker.startswith("U")]), 27)

    def test_coverage_separates_dates_from_other_updates(self):
        payload = {"stocks": [
            {"ticker": "A", "quote_type": "EQUITY",
             "analyst_latest_earnings_date": "2026-10-05",
             "analyst_next_earnings_date": "2026-11-13"},
            {"ticker": "B", "quote_type": "EQUITY", "analyst_eps_next_q": 2.1},
            {"ticker": "F", "quote_type": "ETF", "analyst_next_earnings_date": "2026-10-19"}
        ]}
        self.assertEqual(mod.earnings_coverage(payload, today=date(2026, 10, 12)), {
            "listed": 2, "companies_with_any_date": 1,
            "past_90d_dates": 1, "next_90d_dates": 1
        })

    def test_missing_dates_get_bounded_discovery_slots(self):
        payload = {'stocks': [
            {'ticker': 'DATED', 'quote_type': 'EQUITY', 'analyst_next_earnings_date': '2026-10-15', 'market_cap': 1},
            {'ticker': 'UNDATED', 'quote_type': 'EQUITY', 'market_cap': 100000000000},
            {'ticker': 'STALE', 'quote_type': 'EQUITY', 'analyst_latest_earnings_date': '2025-01-01', 'market_cap': 60000000000},
            {'ticker': 'ETF1', 'quote_type': 'ETF', 'market_cap': 999999999999},
        ]}
        self.assertEqual(mod.candidate_tickers(payload, today=date(2026,10,12)),
                         ['DATED', 'STALE', 'UNDATED'])

    def test_discovery_retains_reserved_slots_in_busy_earnings_week(self):
        payload = {'stocks': [
            *({'ticker': f'D{i:03d}', 'quote_type': 'EQUITY', 'analyst_next_earnings_date': '2026-10-15'} for i in range(100)),
            *({'ticker': f'F{i:03d}', 'quote_type': 'EQUITY', 'market_cap': 100000000000-i} for i in range(100)),
        ]}
        candidates = mod.candidate_tickers(payload, today=date(2026,10,12))
        self.assertEqual(len(candidates), 80)
        self.assertEqual(len([x for x in candidates if x.startswith('D')]), 50)
        self.assertEqual(len([x for x in candidates if x.startswith('F')]), 30)

    def test_undated_discovery_rotates_across_days_without_exceeding_quota(self):
        payload = {'stocks': [
            *({'ticker': f'D{i:03d}', 'quote_type': 'EQUITY',
                'analyst_next_earnings_date': '2026-10-15'} for i in range(60)),
            *({'ticker': f'U{i:03d}', 'quote_type': 'EQUITY',
                'market_cap': 100000000000 - i} for i in range(95)),
        ]}
        first = mod.candidate_tickers(payload, today=date(2026, 10, 12))
        second = mod.candidate_tickers(payload, today=date(2026, 10, 13))
        self.assertEqual(first, mod.candidate_tickers(payload, today=date(2026, 10, 12)))
        self.assertEqual(len(first), 80)
        self.assertEqual(len(second), 80)
        first_undated = {x for x in first if x.startswith('U')}
        second_undated = {x for x in second if x.startswith('U')}
        self.assertEqual(len(first_undated), 30)
        self.assertEqual(len(second_undated), 30)
        self.assertFalse(first_undated & second_undated)
        all_discovered = set()
        for day in range(4):
            selection = mod.candidate_tickers(payload, today=date(2026, 10, 12 + day))
            all_discovered.update(x for x in selection if x.startswith('U'))
        self.assertEqual(len(all_discovered), 95)

    def test_intraday_slots_cover_unknown_dates_without_extra_calls(self):
        payload = {'stocks': [
            *({'ticker': f'D{i:03d}', 'quote_type': 'EQUITY',
                'analyst_next_earnings_date': '2026-10-15'} for i in range(60)),
            *({'ticker': f'U{i:03d}', 'quote_type': 'EQUITY',
                'market_cap': 100000000000 - i} for i in range(95)),
        ]}
        groups = []
        for slot in range(4):
            selected = mod.candidate_tickers(payload, today=date(2026, 10, 12),
                                             rotation_slot=slot)
            self.assertEqual(len(selected), 80)
            group = {ticker for ticker in selected if ticker.startswith('U')}
            self.assertEqual(len(group), 30)
            groups.append(group)
        self.assertEqual(len(set.union(*groups)), 95)
        self.assertFalse(groups[0] & groups[1])
        self.assertFalse(groups[1] & groups[2])
        self.assertEqual(
            mod.candidate_tickers(payload, today=date(2026, 10, 12), rotation_slot=0),
            mod.candidate_tickers(payload, today=date(2026, 10, 12), rotation_slot=0),
        )

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

    def test_refresh_exposes_multi_quarter_diagnostics_and_preserves_failure_visibility(self):
        script = (ROOT / 'scripts/refresh_weekly_earnings.py').read_text(encoding='utf-8')
        workflow = (ROOT / '.github/workflows/refresh-weekly-earnings.yml').read_text(encoding='utf-8')
        self.assertIn('reported_history_tickers', script)
        self.assertIn('multi_quarter_source_tickers', script)
        self.assertIn('archive_multi_quarter_tickers', script)
        self.assertIn('set -o pipefail', workflow)
        self.assertIn('earnings-refresh-report.jsonl', workflow)
        self.assertIn('actions/upload-artifact@v7', workflow)

    def test_status_is_persisted_with_refresh_and_staged_for_publish(self):
        script = (ROOT / 'scripts/refresh_weekly_earnings.py').read_text(encoding='utf-8')
        workflow = (ROOT / '.github/workflows/refresh-weekly-earnings.yml').read_text(encoding='utf-8')
        self.assertIn('DIAGNOSTICS = ROOT / "data" / "earnings-refresh-status.json"', script)
        self.assertIn('DIAGNOSTICS.write_text(json.dumps(status', script)
        self.assertIn('"generated_at": now_utc.isoformat()', script)
        self.assertIn('data/earnings-refresh-status.json', workflow)
        self.assertIn('"archive_multi_quarter_tickers":', script)

    def test_overdue_iphone_calendar_events_get_bounded_market_cap_priority(self):
        index = {"stocks": [
            {"ticker": "JPM", "quote_type": "EQUITY", "market_cap": 600e9,
             "analyst_next_earnings_date": "2026-10-13"},
            {"ticker": "JNJ", "quote_type": "EQUITY", "market_cap": 500e9,
             "analyst_next_earnings_date": "2026-10-13"},
            {"ticker": "GS", "quote_type": "EQUITY", "market_cap": 180e9,
             "analyst_next_earnings_date": "2026-10-13"},
            {"ticker": "OLD", "quote_type": "EQUITY", "market_cap": 900e9,
             "analyst_next_earnings_date": "2026-09-01"},
            {"ticker": "ETF1", "quote_type": "ETF", "market_cap": 900e9,
             "analyst_next_earnings_date": "2026-10-13"},
        ]}
        packed = mod.pack_index_payload(index)
        self.assertEqual(mod.overdue_calendar_tickers(packed, today=date(2026,10,17)),
                         ["JPM", "JNJ", "GS"])
        self.assertEqual(mod.overdue_calendar_tickers(packed, today=date(2026,10,17), max_slots=2),
                         ["JPM", "JNJ"])

    def test_over_budget_does_not_abort_archived_earnings_publication(self):
        script = (ROOT / 'scripts/refresh_weekly_earnings.py').read_text(encoding='utf-8')
        self.assertIn('startup_fits = len(encoded.encode("utf-8")) <= MAX_STARTUP_BYTES', script)
        self.assertIn('if startup_fits:', script)
        self.assertIn('archive = save_archive([*rows, *discovered_history]', script)
        self.assertIn('"startup_updated": startup_fits', script)
        self.assertNotIn('raise RuntimeError("weekly earnings refresh would exceed startup payload budget")', script)

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
