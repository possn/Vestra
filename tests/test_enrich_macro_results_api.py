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
    def __init__(self, payload=None, status=200, get_payloads=None, get_status=200):
        self.payload = payload or {}
        self.status = status
        self.get_payloads = get_payloads or {}
        self.get_status = get_status
        self.calls = []
    def post(self, url, **kwargs):
        self.calls.append(('POST', url, kwargs))
        return _Response(self.payload, self.status)
    def get(self, url, **kwargs):
        self.calls.append(('GET', url, kwargs))
        series_id = url.rstrip('/').split('/')[-1]
        return _Response(self.get_payloads.get(series_id, {}), self.get_status)


def _series(series_id, values):
    rows = []
    for year, month, value in values:
        rows.append({'year':str(year), 'period':f'M{month:02d}', 'periodName':'x', 'value':str(value), 'footnotes':[{}]})
    return {'seriesID': series_id, 'data': rows}


def _payload_for_series(series):
    return {'status':'REQUEST_SUCCEEDED','message':[],'Results':{'series':[series]}}


def ppi_series():
    return [
        _series('WPSFD4', [(2026,8,100.4),(2026,7,100.0)]),
        _series('WPUFD4', [(2026,8,105.4),(2025,8,100.0)]),
        _series('WPSFD49116', [(2026,8,100.3),(2026,7,100.0)]),
        _series('WPUFD49116', [(2026,8,104.7),(2025,8,100.0)]),
    ]


def cpi_series():
    return [
        _series('CUSR0000SA0', [(2026,8,100.4),(2026,7,100.0)]),
        _series('CUUR0000SA0', [(2026,8,103.4),(2025,8,100.0)]),
        _series('CUSR0000SA0L1E', [(2026,8,100.3),(2026,7,100.0)]),
        _series('CUUR0000SA0L1E', [(2026,8,102.4),(2025,8,100.0)]),
    ]


def ppi_payload():
    return {'status':'REQUEST_SUCCEEDED','message':[],'Results':{'series':ppi_series()}}


def cpi_payload():
    return {'status':'REQUEST_SUCCEEDED','message':[],'Results':{'series':cpi_series()}}


def get_payloads(series_rows):
    return {row['seriesID']:_payload_for_series(row) for row in series_rows}


@unittest.skipUnless(DEPS_AVAILABLE, 'requests installed in macro workflow')
class MacroApiFallbackTests(unittest.TestCase):
    def test_ppi_api_metrics_match_named_release_measures(self):
        session = _Session(ppi_payload())
        fetched = mod.fetch_metrics(session, 'PPI EUA', date(2026,9,10))
        self.assertIsNotNone(fetched)
        metrics, summary, transport, diagnostics = fetched
        self.assertEqual(metrics, {
            'headline_mom_pct':0.4,
            'headline_yoy_pct':5.4,
            'core_mom_pct':0.3,
            'core_yoy_pct':4.7,
        })
        self.assertIn('August 2026', summary)
        self.assertIn('+5.4% YoY', summary)
        self.assertEqual(transport, 'post')
        self.assertIn('post_http=200:ok', diagnostics)
        self.assertEqual(session.calls[0][0], 'POST')
        self.assertEqual(session.calls[0][1], mod.API_URL)
        sent = session.calls[0][2]['json']['seriesid']
        self.assertEqual(sent, ['WPSFD4','WPUFD4','WPSFD49116','WPUFD49116'])

    def test_multi_series_post_failure_falls_back_to_official_single_series_gets(self):
        failed_post = {'status':'REQUEST_FAILED','message':['temporary multi-series failure'],'Results':{}}
        session = _Session(failed_post, get_payloads=get_payloads(ppi_series()))
        fetched = mod.fetch_metrics(session, 'PPI EUA', date(2026,9,10))
        self.assertIsNotNone(fetched)
        metrics, _, transport, diagnostics = fetched
        self.assertEqual(transport, 'get')
        self.assertEqual(metrics['headline_yoy_pct'], 5.4)
        self.assertEqual(len([call for call in session.calls if call[0] == 'GET']), 4)
        self.assertTrue(any('post_api_status=REQUEST_FAILED' in value for value in diagnostics))
        self.assertTrue(any('get_WPSFD4_http=200:ok' in value for value in diagnostics))

    def test_cpi_fallback_attaches_structured_result_when_release_fetch_failed(self):
        payload = {'events':[{'date':'2026-09-11','short_title':'CPI EUA','source':'bls'}]}
        stats = mod.enrich_api_fallback(payload, _Session(cpi_payload()), today=date(2026,9,11))
        self.assertEqual(stats['attempted'], 1)
        self.assertEqual(stats['matched'], 1)
        self.assertEqual(stats['transports']['post'], 1)
        self.assertEqual(stats['failures'], [])
        event = payload['events'][0]
        self.assertEqual(event['result_status'], 'official_release_summary')
        self.assertEqual(event['result_metric_schema'], 'bls_cpi_v1')
        self.assertEqual(event['result_metrics'], {
            'headline_mom_pct':0.4,
            'headline_yoy_pct':3.4,
            'core_mom_pct':0.3,
            'core_yoy_pct':2.4,
        })
        self.assertEqual(event['result_transport'], 'bls_public_api_post')
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
        self.assertEqual(stats['attempted'], 0)
        self.assertEqual(stats['matched'], 0)
        self.assertEqual(session.calls, [])
        self.assertEqual(payload['events'][0]['result_summary'], 'verified release')

    def test_future_event_is_not_queried(self):
        payload = {'events':[{'date':'2026-10-14','short_title':'CPI EUA','source':'bls'}]}
        session = _Session(cpi_payload())
        stats = mod.enrich_api_fallback(payload, session, today=date(2026,9,11))
        self.assertEqual(stats['attempted'], 0)
        self.assertEqual(stats['matched'], 0)
        self.assertEqual(session.calls, [])

    def test_incomplete_api_data_fails_closed_and_reports_diagnostic(self):
        rows = cpi_series()[:-1]
        body = {'status':'REQUEST_SUCCEEDED','message':[],'Results':{'series':rows}}
        session = _Session(body, get_payloads=get_payloads(rows))
        payload = {'events':[{'date':'2026-09-11','short_title':'CPI EUA','source':'bls'}]}
        stats = mod.enrich_api_fallback(payload, session, today=date(2026,9,11))
        self.assertEqual(stats['attempted'], 1)
        self.assertEqual(stats['matched'], 0)
        self.assertTrue(stats['failures'])
        self.assertNotIn('result_status', payload['events'][0])


class MacroApiFallbackStaticTests(unittest.TestCase):
    def test_uses_only_official_bls_api_and_named_series(self):
        source = (ROOT / 'scripts' / 'enrich_macro_results_api.py').read_text(encoding='utf-8')
        self.assertIn('https://api.bls.gov/publicAPI/v2/timeseries/data/', source)
        for series_id in ('CUSR0000SA0','CUUR0000SA0','CUSR0000SA0L1E','CUUR0000SA0L1E','WPSFD4','WPUFD4','WPSFD49116','WPUFD49116'):
            self.assertIn(series_id, source)
        self.assertIn('VESTRA_REQUIRE_BLS_API_MATCH', source)
        self.assertIn('no consensus inference and no generic Actual coercion', source)
        self.assertNotIn('fred.stlouisfed.org', source)


if __name__ == '__main__':
    unittest.main(verbosity=2)
