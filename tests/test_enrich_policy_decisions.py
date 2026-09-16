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
    def __init__(self, text, status=200): self.text, self.status_code = text, status
    def raise_for_status(self):
        if self.status_code >= 400: raise RuntimeError(f'HTTP {self.status_code}')


class _Session:
    def __init__(self, pages): self.pages, self.calls = pages, []
    def get(self, url, **kwargs):
        self.calls.append(url)
        value = self.pages[url]
        return value if isinstance(value, _Response) else _Response(value)


ECB_INDEX_PAGE = '''<html><body>
<a href="/press/pr/date/2026/html/ecb.mp260723~29f24d99bc.en.html">23 July 2026</a>
<a href="/press/pr/date/2026/html/ecb.mp260910~abcdef1234.en.html">10 September 2026</a>
</body></html>'''
ECB_RELEASE_URL = 'https://www.ecb.europa.eu/press/pr/date/2026/html/ecb.mp260910~abcdef1234.en.html'
ECB_RELEASE_PAGE = '''<html><body><p>The Governing Council today decided to keep the three key ECB interest rates unchanged.</p>
<p>The interest rates on the deposit facility, the main refinancing operations and the marginal lending facility will remain unchanged at 2.25%, 2.40% and 2.65% respectively.</p></body></html>'''
FED_RELEASE_URL = 'https://www.federalreserve.gov/newsevents/pressreleases/monetary20260916a.htm'
FED_INDEX_PAGE = f'''<html><body><a href="/newsevents/pressreleases/monetary20260916a.htm">FOMC statement</a></body></html>'''
FED_RELEASE_PAGE = '''<html><body><p>The Committee decided to lower the target range for the federal funds rate to 4.75 to 5 percent.</p></body></html>'''


@unittest.skipUnless(DEPS_AVAILABLE, 'macro result dependencies are installed only in the dedicated workflow')
class PolicyDecisionTests(unittest.TestCase):
    def test_multiday_central_bank_events_move_to_decision_day(self):
        payload = {'events': [
            {'date':'2026-09-09','date_end':'2026-09-10','short_title':'BCE','source':'ecb','title':'old'},
            {'date':'2026-09-15','date_end':'2026-09-16','short_title':'FOMC','source':'fed','title':'old'},
            {'date':'2026-09-11','short_title':'CPI EUA','source':'bls'},
        ]}
        self.assertEqual(mod.normalize_decision_days(payload), 2)
        ecb, fed, cpi = payload['events']
        self.assertEqual(ecb['meeting_start'], '2026-09-09'); self.assertEqual(ecb['date'], '2026-09-10')
        self.assertNotIn('date_end', ecb); self.assertEqual(ecb['time_local'], '14:15 CET')
        self.assertIn('decisão de política monetária', ecb['title'])
        self.assertEqual(fed['date'], '2026-09-16'); self.assertEqual(fed['time_local'], '2:00 PM ET')
        self.assertEqual(cpi['date'], '2026-09-11')

    def test_exact_ecb_release_url_is_selected_by_decision_date(self):
        self.assertEqual(mod.find_ecb_release_url(ECB_INDEX_PAGE, date(2026, 9, 10)), ECB_RELEASE_URL)
        self.assertEqual(mod.find_ecb_release_url(ECB_INDEX_PAGE, date(2026, 6, 11)), '')

    def test_ecb_parser_extracts_three_named_rates(self):
        summary, metrics = mod.parse_ecb_release(ECB_RELEASE_PAGE)
        self.assertIn('Taxa de depósito 2.25%', summary)
        self.assertEqual(metrics, {'deposit_facility_pct':2.25,'main_refinancing_pct':2.40,'marginal_lending_pct':2.65})

    def test_ecb_result_attaches_only_to_exact_decision_date(self):
        payload = {'events': [{'date':'2026-09-10','short_title':'BCE','source':'ecb'},{'date':'2026-07-23','short_title':'BCE','source':'ecb'}]}
        session = _Session({mod.ECB_INDEX: ECB_INDEX_PAGE, ECB_RELEASE_URL: ECB_RELEASE_PAGE})
        stats = mod.enrich_ecb_results(payload, session, today=date(2026, 9, 10))
        self.assertEqual(stats['matched'], 1)
        self.assertEqual(payload['events'][0]['result_metric_schema'], 'ecb_rates_v1')
        self.assertEqual(payload['events'][0]['result_metrics']['deposit_facility_pct'], 2.25)
        self.assertNotIn('result_metrics', payload['events'][1])

    def test_future_ecb_decision_is_not_fetched(self):
        payload = {'events': [{'date':'2026-10-29','short_title':'BCE','source':'ecb'}]}
        session = _Session({})
        self.assertEqual(mod.enrich_ecb_results(payload, session, today=date(2026, 9, 10)), {'matched':0,'fetched_index':0,'fetched_releases':0})
        self.assertEqual(session.calls, [])

    def test_verified_ecb_rates_carry_forward_only_for_same_decision(self):
        previous = {'events': [{'date':'2026-09-10','short_title':'BCE','source':'ecb','result_status':'official_release_summary','result_summary':'verified','result_released_at':'2026-09-10','source_url':ECB_RELEASE_URL,'result_metric_schema':'ecb_rates_v1','result_metrics':{'deposit_facility_pct':2.25}}]}
        payload = {'events': [{'date':'2026-09-10','short_title':'BCE','source':'ecb'},{'date':'2026-10-29','short_title':'BCE','source':'ecb'}]}
        self.assertEqual(mod.carry_forward_ecb_results(payload, previous), 1)
        self.assertEqual(payload['events'][0]['result_metrics']['deposit_facility_pct'], 2.25)
        self.assertNotIn('result_metrics', payload['events'][1])

    def test_fed_release_url_is_discovered_or_deterministic_for_decision_date(self):
        self.assertEqual(mod.find_fed_release_url(FED_INDEX_PAGE, date(2026, 9, 16)), FED_RELEASE_URL)
        self.assertEqual(mod.find_fed_release_url('', date(2026, 9, 16)), FED_RELEASE_URL)

    def test_fed_parser_extracts_target_range(self):
        summary, metrics = mod.parse_fed_release(FED_RELEASE_PAGE)
        self.assertIn('4.75%–5.00%', summary)
        self.assertEqual(metrics, {'target_lower_pct': 4.75, 'target_upper_pct': 5.0})

    def test_fed_result_attaches_to_fomc_decision(self):
        payload = {'events': [{'date':'2026-09-16','short_title':'FOMC','source':'fed'}]}
        session = _Session({mod.FED_INDEX: FED_INDEX_PAGE, FED_RELEASE_URL: FED_RELEASE_PAGE})
        stats = mod.enrich_fed_results(payload, session, today=date(2026, 9, 16))
        self.assertEqual(stats['matched'], 1)
        event = payload['events'][0]
        self.assertEqual(event['result_status'], 'official_release_summary')
        self.assertEqual(event['result_metric_schema'], 'fed_funds_target_v1')
        self.assertEqual(event['result_metrics'], {'target_lower_pct': 4.75, 'target_upper_pct': 5.0})
        self.assertEqual(event['source_url'], FED_RELEASE_URL)

    def test_verified_fed_result_carries_forward_for_same_decision(self):
        previous = {'events': [{'date':'2026-09-16','short_title':'FOMC','source':'fed','result_status':'official_release_summary','result_summary':'verified','result_released_at':'2026-09-16','source_url':FED_RELEASE_URL,'result_metric_schema':'fed_funds_target_v1','result_metrics':{'target_lower_pct':4.75,'target_upper_pct':5.0}}]}
        payload = {'events': [{'date':'2026-09-16','short_title':'FOMC','source':'fed'}]}
        self.assertEqual(mod.carry_forward_fed_results(payload, previous), 1)
        self.assertEqual(payload['events'][0]['result_metrics']['target_upper_pct'], 5.0)


if __name__ == '__main__':
    unittest.main(verbosity=2)
