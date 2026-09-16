import importlib.util
from datetime import date
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
DEPS_AVAILABLE = all(importlib.util.find_spec(name) is not None for name in ('requests', 'lxml'))
mod = None
if DEPS_AVAILABLE:
    spec = importlib.util.spec_from_file_location('enrich_policy_decisions', ROOT / 'scripts' / 'enrich_policy_decisions.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)


class _Response:
    def __init__(self, text, status=200):
        self.text = text
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f'HTTP {self.status_code}')


class _Session:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append(url)
        if url not in self.pages:
            return _Response('', 404)
        value = self.pages[url]
        if isinstance(value, tuple):
            return _Response(value[0], value[1])
        return _Response(value)


ECB_INDEX_PAGE = '''<html><body>
<a href="/press/pr/date/2026/html/ecb.mp260723~29f24d99bc.en.html">23 July 2026</a>
<a href="/press/pr/date/2026/html/ecb.mp260910~abcdef1234.en.html">10 September 2026</a>
</body></html>'''
ECB_RELEASE_URL = 'https://www.ecb.europa.eu/press/pr/date/2026/html/ecb.mp260910~abcdef1234.en.html'
ECB_RELEASE_PAGE = '''<html><body>
<p>The Governing Council today decided to keep the three key ECB interest rates unchanged.</p>
<p>The interest rates on the deposit facility, the main refinancing operations and the marginal lending facility will remain unchanged at 2.25%, 2.40% and 2.65% respectively.</p>
</body></html>'''
FED_RELEASE_URL = 'https://www.federalreserve.gov/newsevents/pressreleases/monetary20260916a.htm'
FED_RELEASE_PAGE = '''<html><body>
<p>The Federal Open Market Committee approved the following statement.</p>
<p>The Committee decided to raise the target range for the federal funds rate to 3-3/4 to 4 percent, in support of the Federal Reserve's dual mandate.</p>
</body></html>'''
FED_HOLD_PAGE = '''<html><body>
<p>The Committee decided to maintain the target range for the federal funds rate at 3-1/2 to 3-3/4 percent.</p>
</body></html>'''


@unittest.skipUnless(DEPS_AVAILABLE, 'macro result dependencies are installed only in the dedicated workflow')
class PolicyDecisionTests(unittest.TestCase):
    def test_multiday_central_bank_events_move_to_decision_day(self):
        payload = {'events': [
            {'date':'2026-09-09','date_end':'2026-09-10','short_title':'BCE','source':'ecb','title':'old'},
            {'date':'2026-09-15','date_end':'2026-09-16','short_title':'FOMC','source':'fed','title':'old'},
            {'date':'2026-09-11','short_title':'CPI EUA','source':'bls'},
        ]}
        changed = mod.normalize_decision_days(payload)
        self.assertEqual(changed, 2)
        ecb, fed, cpi = payload['events']
        self.assertEqual(ecb['meeting_start'], '2026-09-09')
        self.assertEqual(ecb['date'], '2026-09-10')
        self.assertNotIn('date_end', ecb)
        self.assertEqual(ecb['time_local'], '14:15 CET')
        self.assertIn('decisão de política monetária', ecb['title'])
        self.assertEqual(fed['date'], '2026-09-16')
        self.assertEqual(fed['time_local'], '2:00 PM ET')
        self.assertEqual(cpi['date'], '2026-09-11')

    def test_exact_ecb_release_url_is_selected_by_decision_date(self):
        self.assertEqual(mod.find_ecb_release_url(ECB_INDEX_PAGE, date(2026, 9, 10)), ECB_RELEASE_URL)
        self.assertEqual(mod.find_ecb_release_url(ECB_INDEX_PAGE, date(2026, 6, 11)), '')

    def test_ecb_parser_extracts_three_named_rates(self):
        parsed = mod.parse_ecb_release(ECB_RELEASE_PAGE)
        self.assertIsNotNone(parsed)
        summary, metrics = parsed
        self.assertIn('Taxa de depósito 2.25%', summary)
        self.assertEqual(metrics, {
            'deposit_facility_pct': 2.25,
            'main_refinancing_pct': 2.40,
            'marginal_lending_pct': 2.65,
        })

    def test_ecb_result_attaches_only_to_exact_decision_date(self):
        payload = {'events': [
            {'date':'2026-09-10','short_title':'BCE','source':'ecb'},
            {'date':'2026-07-23','short_title':'BCE','source':'ecb'},
        ]}
        session = _Session({mod.ECB_INDEX: ECB_INDEX_PAGE, ECB_RELEASE_URL: ECB_RELEASE_PAGE})
        stats = mod.enrich_ecb_results(payload, session, today=date(2026, 9, 10))
        self.assertEqual(stats['matched'], 1)
        current, old = payload['events']
        self.assertEqual(current['result_metric_schema'], 'ecb_rates_v1')
        self.assertEqual(current['result_metrics']['deposit_facility_pct'], 2.25)
        self.assertEqual(current['source_url'], ECB_RELEASE_URL)
        self.assertNotIn('result_metrics', old)

    def test_future_ecb_decision_is_not_fetched(self):
        payload = {'events': [{'date':'2026-10-29','short_title':'BCE','source':'ecb'}]}
        session = _Session({})
        stats = mod.enrich_ecb_results(payload, session, today=date(2026, 9, 10))
        self.assertEqual(stats, {'matched':0,'fetched_index':0,'fetched_releases':0})
        self.assertEqual(session.calls, [])

    def test_verified_ecb_rates_carry_forward_only_for_same_decision(self):
        previous = {'events': [{
            'date':'2026-09-10','short_title':'BCE','source':'ecb',
            'result_status':'official_release_summary','result_summary':'verified',
            'result_released_at':'2026-09-10','source_url':ECB_RELEASE_URL,
            'result_metric_schema':'ecb_rates_v1',
            'result_metrics':{'deposit_facility_pct':2.25},
        }]}
        payload = {'events': [
            {'date':'2026-09-10','short_title':'BCE','source':'ecb'},
            {'date':'2026-10-29','short_title':'BCE','source':'ecb'},
        ]}
        carried = mod.carry_forward_ecb_results(payload, previous)
        self.assertEqual(carried, 1)
        self.assertEqual(payload['events'][0]['result_metrics']['deposit_facility_pct'], 2.25)
        self.assertNotIn('result_metrics', payload['events'][1])

    def test_fed_parser_extracts_target_range_and_action(self):
        summary, metrics = mod.parse_fed_release(FED_RELEASE_PAGE)
        self.assertEqual(metrics, {'target_lower_pct': 3.75, 'target_upper_pct': 4.0})
        self.assertIn('aumentou', summary)
        self.assertIn('3.75%–4.00%', summary)
        hold_summary, hold_metrics = mod.parse_fed_release(FED_HOLD_PAGE)
        self.assertEqual(hold_metrics, {'target_lower_pct': 3.5, 'target_upper_pct': 3.75})
        self.assertIn('manteve', hold_summary)

    def test_fed_result_uses_exact_decision_day_statement(self):
        payload = {'events': [
            {'date':'2026-09-16','short_title':'FOMC','source':'fed'},
            {'date':'2026-10-28','short_title':'FOMC','source':'fed'},
        ]}
        session = _Session({FED_RELEASE_URL: FED_RELEASE_PAGE})
        stats = mod.enrich_fed_results(payload, session, today=date(2026, 9, 16))
        self.assertEqual(stats['matched'], 1)
        self.assertEqual(stats['attempted'], 1)
        current, future = payload['events']
        self.assertEqual(current['source_url'], FED_RELEASE_URL)
        self.assertEqual(current['result_metric_schema'], 'fed_funds_target_v1')
        self.assertEqual(current['result_metrics']['target_lower_pct'], 3.75)
        self.assertEqual(current['result_status'], 'official_release_summary')
        self.assertNotIn('result_metrics', future)

    def test_fed_404_is_fail_closed_until_statement_exists(self):
        payload = {'events': [{'date':'2026-09-16','short_title':'FOMC','source':'fed'}]}
        session = _Session({})
        stats = mod.enrich_fed_results(payload, session, today=date(2026, 9, 16))
        self.assertEqual(stats['matched'], 0)
        self.assertEqual(stats['attempted'], 1)
        self.assertNotIn('result_status', payload['events'][0])

    def test_verified_fed_result_carries_forward(self):
        previous = {'events': [{
            'date':'2026-09-16','short_title':'FOMC','source':'fed',
            'result_status':'official_release_summary','result_summary':'verified',
            'result_released_at':'2026-09-16','source_url':FED_RELEASE_URL,
            'result_metric_schema':'fed_funds_target_v1',
            'result_metrics':{'target_lower_pct':3.75,'target_upper_pct':4.0},
        }]}
        payload = {'events': [{'date':'2026-09-16','short_title':'FOMC','source':'fed'}]}
        self.assertEqual(mod.carry_forward_fed_results(payload, previous), 1)
        self.assertEqual(payload['events'][0]['result_metrics']['target_upper_pct'], 4.0)


if __name__ == '__main__':
    unittest.main(verbosity=2)