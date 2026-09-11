import importlib.util
from datetime import date
from pathlib import Path
import unittest
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
DEPS_AVAILABLE = importlib.util.find_spec('requests') is not None
mod = None
if DEPS_AVAILABLE:
    spec = importlib.util.spec_from_file_location('enrich_macro_results_fred', ROOT / 'scripts' / 'enrich_macro_results_fred.py')
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
    def __init__(self, series_values, status=200):
        self.series_values = series_values
        self.status = status
        self.calls = []
    def get(self, url, **kwargs):
        params = kwargs.get('params') or {}
        self.calls.append((url, params))
        series_id = params.get('id')
        values = self.series_values.get(series_id)
        if values is None:
            return _Response('', 404)
        rows = ['observation_date,' + series_id]
        rows.extend(f'{day},{value}' for day, value in values)
        return _Response('\n'.join(rows) + '\n', self.status)


def cpi_values():
    return {
        'CPIAUCSL': [('2025-08-01',320.0),('2026-07-01',332.813),('2026-08-01',334.131)],
        'CPIAUCNS': [('2025-08-01',323.150),('2026-08-01',334.137)],
        'CPILFESL': [('2025-08-01',328.0),('2026-07-01',336.789),('2026-08-01',337.799)],
        'CPILFENS': [('2025-08-01',329.891),('2026-08-01',337.808)],
    }


def ppi_values():
    return {
        'PPIFIS': [('2025-08-01',150.0),('2026-07-01',156.784),('2026-08-01',157.411)],
        'PPIFID': [('2025-08-01',149.0),('2026-08-01',157.046)],
        'WPSFD49116': [('2025-08-01',137.0),('2026-07-01',143.013),('2026-08-01',143.406)],
        'WPUFD49116': [('2025-08-01',136.916),('2026-08-01',143.337)],
    }


@unittest.skipUnless(DEPS_AVAILABLE, 'requests installed in macro workflow')
class FredBlsFallbackTests(unittest.TestCase):
    def test_cpi_named_metrics_are_calculated_from_sa_and_nsa_series(self):
        session = _Session(cpi_values())
        fetched = mod.fetch_metrics(session, 'CPI EUA', date(2026,9,11))
        self.assertIsNotNone(fetched)
        metrics, summary, diagnostics = fetched
        self.assertEqual(metrics, {
            'headline_mom_pct':0.4,
            'headline_yoy_pct':3.4,
            'core_mom_pct':0.3,
            'core_yoy_pct':2.4,
        })
        self.assertIn('August 2026', summary)
        self.assertIn('U.S. BLS data via FRED', summary)
        self.assertEqual(len(session.calls), 4)
        self.assertTrue(all('http=200:ok' in item for item in diagnostics))

    def test_ppi_named_metrics_are_calculated_from_fred_bls_mirror(self):
        session = _Session(ppi_values())
        fetched = mod.fetch_metrics(session, 'PPI EUA', date(2026,9,10))
        self.assertIsNotNone(fetched)
        metrics, summary, _ = fetched
        self.assertEqual(metrics, {
            'headline_mom_pct':0.4,
            'headline_yoy_pct':5.4,
            'core_mom_pct':0.3,
            'core_yoy_pct':4.7,
        })
        self.assertIn('+5.4% YoY', summary)

    def test_fallback_attaches_result_without_generic_actual(self):
        payload = {'events':[{'date':'2026-09-11','short_title':'CPI EUA','source':'bls'}]}
        stats = mod.enrich_fred_fallback(payload, _Session(cpi_values()), today=date(2026,9,11))
        self.assertEqual(stats, {'attempted':1,'matched':1,'failures':[]})
        event = payload['events'][0]
        self.assertEqual(event['result_status'], 'official_release_summary')
        self.assertEqual(event['result_metric_schema'], 'bls_cpi_v1')
        self.assertEqual(event['result_transport'], 'fred_bls_mirror')
        self.assertEqual(event['source_url'], 'https://www.bls.gov/news.release/cpi.nr0.htm')
        self.assertNotIn('actual', event)

    def test_existing_verified_result_is_not_overwritten(self):
        payload = {'events':[{
            'date':'2026-09-10','short_title':'PPI EUA','source':'bls',
            'result_status':'official_release_summary','result_summary':'verified',
            'result_metrics':{'headline_mom_pct':0.4},
        }]}
        session = _Session(ppi_values())
        stats = mod.enrich_fred_fallback(payload, session, today=date(2026,9,11))
        self.assertEqual(stats, {'attempted':0,'matched':0,'failures':[]})
        self.assertEqual(session.calls, [])
        self.assertEqual(payload['events'][0]['result_summary'], 'verified')

    def test_future_event_is_not_queried(self):
        payload = {'events':[{'date':'2026-10-14','short_title':'CPI EUA','source':'bls'}]}
        session = _Session(cpi_values())
        stats = mod.enrich_fred_fallback(payload, session, today=date(2026,9,11))
        self.assertEqual(stats, {'attempted':0,'matched':0,'failures':[]})
        self.assertEqual(session.calls, [])

    def test_missing_required_series_fails_closed(self):
        values = cpi_values()
        del values['CPILFENS']
        payload = {'events':[{'date':'2026-09-11','short_title':'CPI EUA','source':'bls'}]}
        stats = mod.enrich_fred_fallback(payload, _Session(values), today=date(2026,9,11))
        self.assertEqual(stats['matched'], 0)
        self.assertNotIn('result_status', payload['events'][0])


class FredBlsFallbackStaticTests(unittest.TestCase):
    def test_transport_is_fred_and_source_series_are_bls_backed(self):
        source = (ROOT / 'scripts' / 'enrich_macro_results_fred.py').read_text(encoding='utf-8')
        self.assertIn('https://fred.stlouisfed.org/graph/fredgraph.csv', source)
        for series_id in ('CPIAUCSL','CPIAUCNS','CPILFESL','CPILFENS','PPIFIS','PPIFID','WPSFD49116','WPUFD49116'):
            self.assertIn(series_id, source)
        self.assertIn('Federal Reserve Bank of St. Louis', source)
        self.assertIn('no consensus inference and no generic Actual coercion', source)
        self.assertIn('VESTRA_REQUIRE_FRED_BLS_MATCH', source)


if __name__ == '__main__':
    unittest.main(verbosity=2)
