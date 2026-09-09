import importlib.util
from datetime import date
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
DEPS_AVAILABLE = all(importlib.util.find_spec(name) is not None for name in ('requests', 'lxml'))
mod = None
if DEPS_AVAILABLE:
    spec = importlib.util.spec_from_file_location('enrich_macro_results', ROOT / 'scripts' / 'enrich_macro_results.py')
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
        return _Response(self.pages[url])


CPI_PAGE = '''<html><body>
<p>Transmission of material in this release is embargoed until 8:30 a.m. (ET) Friday, September 11, 2026</p>
<p>The Consumer Price Index for All Urban Consumers (CPI-U) increased 0.2 percent on a seasonally adjusted basis in August after increasing 0.1 percent in July. Over the last 12 months, the all items index increased 3.1 percent before seasonal adjustment.</p>
<p>The index for all items less food and energy rose 0.3 percent in August after rising 0.2 percent in July.</p>
<p>The all items index rose 3.1 percent for the 12 months ending August. The all items less food and energy index rose 2.7 percent over the year.</p>
</body></html>'''

PPI_PAGE = '''<html><body>
<p>Transmission of material in this release is embargoed until 8:30 a.m. (ET) Thursday, September 10, 2026</p>
<p>The Producer Price Index for final demand was unchanged in August, seasonally adjusted, the U.S. Bureau of Labor Statistics reported today. On an unadjusted basis, the index for final demand increased 4.7 percent for the 12 months ended in August.</p>
<p>Prices for final demand less foods, energy, and trade services rose 0.4 percent in August after inching up 0.1 percent in July. For the 12 months ended in August, the index for final demand less foods, energy, and trade services advanced 4.2 percent.</p>
</body></html>'''


@unittest.skipUnless(DEPS_AVAILABLE, 'macro result dependencies are installed only in the dedicated workflow')
class MacroResultTests(unittest.TestCase):
    def test_cpi_parser_extracts_named_headline_and_core_metrics(self):
        parsed = mod.parse_bls_release(CPI_PAGE, 'CPI EUA')
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed[0], date(2026, 9, 11))
        self.assertTrue(parsed[1].startswith('The Consumer Price Index for All Urban Consumers'))
        self.assertEqual(parsed[2], {
            'headline_mom_pct': 0.2,
            'headline_yoy_pct': 3.1,
            'core_mom_pct': 0.3,
            'core_yoy_pct': 2.7,
        })
        self.assertIsNone(mod.parse_bls_release('<p>No release marker</p>', 'CPI EUA'))
        self.assertIsNone(mod.parse_bls_release(CPI_PAGE, 'NFP EUA'))

    def test_ppi_parser_handles_unchanged_headline_and_named_core(self):
        parsed = mod.parse_bls_release(PPI_PAGE, 'PPI EUA')
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed[0], date(2026, 9, 10))
        self.assertEqual(parsed[2], {
            'headline_mom_pct': 0.0,
            'headline_yoy_pct': 4.7,
            'core_mom_pct': 0.4,
            'core_yoy_pct': 4.2,
        })

    def test_result_attaches_only_to_exact_event_date_and_never_generic_actual(self):
        cpi_url = mod.BLS_RELEASES['CPI EUA']['url']
        payload = {'events': [
            {'date':'2026-09-11','short_title':'CPI EUA','source':'bls'},
            {'date':'2026-08-12','short_title':'CPI EUA','source':'bls'},
        ]}
        stats = mod.enrich_bls_results(payload, _Session({cpi_url: CPI_PAGE}), today=date(2026, 9, 11))
        self.assertEqual(stats, {'matched': 1, 'structured': 1, 'fetched': 1})
        current, stale = payload['events']
        self.assertEqual(current['result_status'], 'official_release_summary')
        self.assertEqual(current['result_metric_schema'], 'bls_cpi_v1')
        self.assertEqual(current['result_metrics']['headline_mom_pct'], 0.2)
        self.assertEqual(current['source_url'], cpi_url)
        self.assertNotIn('actual', current, 'named official measures must not masquerade as a generic Actual')
        self.assertNotIn('result_summary', stale, 'a current release must never attach to an older event')

    def test_future_event_is_not_queried_or_marked_published(self):
        payload = {'events': [{'date':'2026-09-11','short_title':'CPI EUA','source':'bls'}]}
        session = _Session({})
        stats = mod.enrich_bls_results(payload, session, today=date(2026, 9, 10))
        self.assertEqual(stats, {'matched': 0, 'structured': 0, 'fetched': 0})
        self.assertEqual(session.calls, [])
        self.assertNotIn('result_status', payload['events'][0])

    def test_verified_structured_result_carries_forward_only_for_exact_identity(self):
        previous = {'events': [{
            'date':'2026-09-11','short_title':'CPI EUA','source':'bls',
            'result_status':'official_release_summary','result_summary':'verified',
            'result_released_at':'2026-09-11','source_url':mod.BLS_RELEASES['CPI EUA']['url'],
            'result_metric_schema':'bls_cpi_v1',
            'result_metrics':{'headline_mom_pct':0.2,'headline_yoy_pct':3.1},
        }]}
        payload = {'events': [
            {'date':'2026-09-11','short_title':'CPI EUA','source':'bls'},
            {'date':'2026-10-14','short_title':'CPI EUA','source':'bls'},
            {'date':'2026-09-11','short_title':'PPI EUA','source':'bls'},
        ]}
        carried = mod.carry_forward_verified_results(payload, previous)
        self.assertEqual(carried, 1)
        self.assertEqual(payload['events'][0]['result_summary'], 'verified')
        self.assertEqual(payload['events'][0]['result_metrics']['headline_mom_pct'], 0.2)
        self.assertNotIn('result_metrics', payload['events'][1])
        self.assertNotIn('result_metrics', payload['events'][2])

    def test_partial_metric_parse_stays_partial_instead_of_guessing(self):
        page = '''<html><body>
        <p>Transmission of material in this release is embargoed until 8:30 a.m. (ET) Friday, September 11, 2026</p>
        <p>The Consumer Price Index for All Urban Consumers (CPI-U) increased 0.2 percent in August.</p>
        </body></html>'''
        parsed = mod.parse_bls_release(page, 'CPI EUA')
        self.assertEqual(parsed[2], {'headline_mom_pct': 0.2})


class MacroResultStaticTests(unittest.TestCase):
    def test_contract_uses_only_official_bls_release_pages(self):
        source = (ROOT / 'scripts' / 'enrich_macro_results.py').read_text(encoding='utf-8')
        self.assertIn('https://www.bls.gov/news.release/cpi.nr0.htm', source)
        self.assertIn('https://www.bls.gov/news.release/ppi.nr0.htm', source)
        self.assertIn('no consensus inference and no generic Actual coercion', source)
        self.assertNotIn('fred.stlouisfed.org', source)


if __name__ == '__main__':
    unittest.main(verbosity=2)
