import importlib.util
from datetime import date
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
DEPS_AVAILABLE = importlib.util.find_spec('requests') is not None
mod = None
if DEPS_AVAILABLE:
    spec = importlib.util.spec_from_file_location('enrich_macro_results_api', ROOT / 'scripts' / 'enrich_macro_results_api.py')
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)


class _Response:
    def __init__(self, payload, status=200):
        self.payload = payload
        self.status_code = status
    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f'HTTP {self.status_code}')
    def json(self):
        return self.payload


class _Session:
    def __init__(self, payload=None, status=200):
        self.payload = payload or {}
        self.status = status
        self.calls = []
    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return _Response(self.payload, self.status)


def _series(series_id, values):
    rows = []
    for year, month, value in values:
        rows.append({'year':str(year), 'period':f'M{month:02d}', 'periodName':'x', 'value':str(value), 'footnotes':[{}]})
    return {'seriesID': series_id, 'data': rows}


def ppi_payload():
    return {
        'status':'REQUEST_SUCCEEDED',
        'message':[],
        'Results': {'series': [
            _series('WPSFD4', [(2026,8,100.4),(2026,7,100.0)]),
            _series('WPUFD4', [(2026,8,105.4),(2025,8,100.0)]),
            _series('WPSFD49116', [(2026,8,100.3),(2026,7,100.0)]),
            _series('WPUFD49116', [(2026,8,104.7),(2025,8,100.0)]),
        ]}
    }


def cpi_payload():
    return {
        'status':'REQUEST_SUCCEEDED',
        'message':[],
        'Results': {'series': [
            _series('CUSR0000SA0', [(2026,8,100.4),(2026,7,100.0)]),
            _series('CUUR0000SA0', [(2026,8,103.4),(2025,8,100.0)]),
            _series('CUSR0000SA0L1E', [(2026,8,100.3),(2026,7,100.0)]),
            _series('CUUR0000SA0L1E', [(2026,8,102.4),(2025,8,100.0)]),
        ]}
    }


@unittest.skipUnless(DEPS_AVAILABLE, 'requests installed in macro workflow')
class MacroApiFallbackTests(unittest.TestCase):
    def test_ppi_api_metrics_match_named_release_measures(self):
        session = _Session(ppi_payload())
        fetched = mod.fetch_metrics(session, 'PPI EUA', date(2026,9,10))
        self.assertIsNotNone(fetched)
        metrics, summary = fetched
        self.assertEqual(metrics, {
            'headline_mom_pct':0.4,
            'headline_yoy_pct':5.4,
            'core_mom_pct':0.3,
            'core_yoy_pct':4.7,
        })
        self.assertIn('August 2026', summary)
        self.assertIn('+5.4% YoY', summary)
        self.assertEqual(session.calls[0][0], mod.API_URL)
        sent = session.calls[0][1]['json']['seriesid']
        self.assertEqual(sent, ['WPSFD4','WPUFD4','WPSFD49116','WPUFD49116'])

    def test_cpi_fallback_attaches_structured_result_when_release_fetch_failed(self):
        payload = {'events':[{'date':'2026-09-11','short_title':'CPI EUA','source':'bls'}]}
        stats = mod.enrich_api_fallback(payload, _Session(cpi_payload()), today=date(2026,9,11))
        self.assertEqual(stats, {'attempted':1,'matched':1})
        event = payload['events'][0]
        self.assertEqual(event['result_status'], 'official_release_summary')
        self.assertEqual(event['result_metric_schema'], 'bls_cpi_v1')
        self.assertEqual(event['result_metrics'], {
            'headline_mom_pct':0.4,
            'headline_yoy_pct':3.4,
            'core_mom_pct':0.3,
            'core_yoy_pct':2.4,
        })
        self.assertEqual(event['result_transport'], 'bls_public_api')
        self.assertEqual(event['source_url'], 'https://www.bls.gov/news.release/cpi.nr0.htm')
        self.assertNotIn('actual', event)

    def test_existing_verified_release_is_never_overwritten(self):
        payload = {'events':[{
            'date':'2026-09-10','short_title':'PPI EUA','source':'bls',
            'result_status':'official_release_summary',
            'result_summary':'verified release',
            'result_metrics':{'headline_mom_pct':0.4},
        }]}
        session = _Session(ppi_payload())
        stats = mod.enrich_api_fallback(payload, session, today=date(2026,9,11))
        self.assertEqual(stats, {'attempted':0,'matched':0})
        self.assertEqual(session.calls, [])
        self.assertEqual(payload['events'][0]['result_summary'], 'verified release')

    def test_future_event_is_not_queried(self):
        payload = {'events':[{'date':'2026-10-14','short_title':'CPI EUA','source':'bls'}]}
        session = _Session(cpi_payload())
        stats = mod.enrich_api_fallback(payload, session, today=date(2026,9,11))
        self.assertEqual(stats, {'attempted':0,'matched':0})
        self.assertEqual(session.calls, [])

    def test_incomplete_api_data_fails_closed(self):
        body = cpi_payload()
        body['Results']['series'] = body['Results']['series'][:-1]
        payload = {'events':[{'date':'2026-09-11','short_title':'CPI EUA','source':'bls'}]}
        stats = mod.enrich_api_fallback(payload, _Session(body), today=date(2026,9,11))
        self.assertEqual(stats, {'attempted':1,'matched':0})
        self.assertNotIn('result_status', payload['events'][0])


class MacroApiFallbackStaticTests(unittest.TestCase):
    def test_uses_only_official_bls_api_and_named_series(self):
        source = (ROOT / 'scripts' / 'enrich_macro_results_api.py').read_text(encoding='utf-8')
        self.assertIn('https://api.bls.gov/publicAPI/v2/timeseries/data/', source)
        for series_id in ('CUSR0000SA0','CUUR0000SA0','CUSR0000SA0L1E','CUUR0000SA0L1E','WPSFD4','WPUFD4','WPSFD49116','WPUFD49116'):
            self.assertIn(series_id, source)
        self.assertIn('no consensus inference and no generic Actual coercion', source)
        self.assertNotIn('fred.stlouisfed.org', source)


if __name__ == '__main__':
    unittest.main(verbosity=2)
