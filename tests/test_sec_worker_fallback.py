import os
import sys
import types
import unittest
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(__file__))
SCRIPTS = os.path.join(ROOT, 'scripts')
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

import sec_worker_fallback as fallback


class FakeResponse:
    def __init__(self, status_code=200, payload=None, json_error=None):
        self.status_code = status_code
        self.ok = 200 <= status_code < 300
        self.payload = {} if payload is None else payload
        self.json_error = json_error

    def json(self):
        if self.json_error is not None:
            raise self.json_error
        return self.payload


class FakeInnerSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.headers = {}

    def get(self, url, timeout=20, **kwargs):
        self.calls.append((str(url), kwargs))
        if not self.responses:
            raise AssertionError('unexpected request')
        value = self.responses.pop(0)
        if isinstance(value, Exception):
            raise value
        return value


class SessionFactory:
    def __init__(self, responses):
        self.responses = responses
        self.instances = []

    def __call__(self, *args, **kwargs):
        session = FakeInnerSession(self.responses)
        self.instances.append(session)
        return session


class CaptureLog:
    def __init__(self):
        self.info_messages = []
        self.warning_messages = []

    def info(self, *args, **kwargs):
        self.info_messages.append(args)

    def warning(self, *args, **kwargs):
        self.warning_messages.append(args)

    def debug(self, *args, **kwargs):
        pass


class SecWorkerFallbackTests(unittest.TestCase):
    def make_module(self, responses, enrich=None):
        factory = SessionFactory(responses)
        logger = CaptureLog()
        module = types.SimpleNamespace(
            requests=types.SimpleNamespace(Session=factory),
            log=logger,
        )
        if enrich is not None:
            module.enrich = enrich
        return module, factory, logger

    def tearDown(self):
        os.environ.pop('SEC_DIRECT_BLOCKED', None)
        os.environ.pop('SEC_COMPANYFACTS_BLOCKED', None)
        os.environ.pop('SEC_USER_AGENT', None)

    def test_worker_url_extracts_exact_cik(self):
        direct = 'https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json'
        self.assertEqual(
            fallback._worker_url(direct, 'https://worker.example'),
            'https://worker.example/sec/companyfacts?cik=320193',
        )
        self.assertIsNone(fallback._worker_url('https://www.sec.gov/files/company_tickers.json', 'https://worker.example'))

    def test_direct_success_does_not_call_worker_and_is_counted(self):
        direct_ok = FakeResponse(200, {'facts': {'us-gaap': {}}})
        module, factory, _ = self.make_module([direct_ok])
        fallback.install(module, worker_url='https://worker.example')
        session = module.requests.Session()
        response = session.get('https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json')
        self.assertIs(response, direct_ok)
        self.assertEqual(len(factory.instances[0].calls), 1)
        self.assertIn('data.sec.gov', factory.instances[0].calls[0][0])
        diag = session._vestra_transport_diag
        self.assertEqual(diag['companyfacts_direct_attempts'], 1)
        self.assertEqual(diag['companyfacts_direct_success'], 1)
        self.assertEqual(diag['companyfacts_direct_status'], {'200': 1})
        self.assertEqual(diag['companyfacts_direct_payload'], {'valid_facts': 1})
        self.assertEqual(diag['companyfacts_worker_attempts'], 0)

    def test_direct_403_retries_same_cik_via_worker_and_counts_both_legs(self):
        blocked = FakeResponse(403)
        worker_ok = FakeResponse(200, {'facts': {'us-gaap': {}}})
        module, factory, _ = self.make_module([blocked, worker_ok])
        fallback.install(module, worker_url='https://worker.example')
        session = module.requests.Session()
        response = session.get('https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json')
        self.assertIs(response, worker_ok)
        calls = [url for url, _ in factory.instances[0].calls]
        self.assertEqual(calls, [
            'https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json',
            'https://worker.example/sec/companyfacts?cik=320193',
        ])
        diag = session._vestra_transport_diag
        self.assertEqual(diag['companyfacts_direct_status'], {'403': 1})
        self.assertEqual(diag['companyfacts_worker_status'], {'200': 1})
        self.assertEqual(diag['companyfacts_worker_success'], 1)
        self.assertEqual(diag['companyfacts_worker_payload'], {'valid_facts': 1})

    def test_worker_502_is_counted_and_direct_failure_is_returned(self):
        blocked = FakeResponse(403)
        worker_bad = FakeResponse(502)
        module, _, _ = self.make_module([blocked, worker_bad])
        fallback.install(module, worker_url='https://worker.example')
        session = module.requests.Session()
        response = session.get('https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json')
        self.assertIs(response, blocked)
        diag = session._vestra_transport_diag
        self.assertEqual(diag['companyfacts_direct_status'], {'403': 1})
        self.assertEqual(diag['companyfacts_worker_attempts'], 1)
        self.assertEqual(diag['companyfacts_worker_status'], {'502': 1})
        self.assertEqual(diag['companyfacts_worker_success'], 0)
        self.assertEqual(diag['companyfacts_worker_payload'], {})

    def test_worker_200_missing_facts_is_visible_without_changing_response(self):
        blocked = FakeResponse(403)
        worker_ok_but_bad_payload = FakeResponse(200, {'error': 'unexpected'})
        module, _, _ = self.make_module([blocked, worker_ok_but_bad_payload])
        fallback.install(module, worker_url='https://worker.example')
        session = module.requests.Session()
        response = session.get('https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json')
        self.assertIs(response, worker_ok_but_bad_payload)
        self.assertEqual(response.json(), {'error': 'unexpected'})
        self.assertEqual(session._vestra_transport_diag['companyfacts_worker_payload'], {'missing_facts': 1})

    def test_worker_200_json_error_is_visible(self):
        blocked = FakeResponse(403)
        worker_bad_json = FakeResponse(200, json_error=ValueError('bad json'))
        module, _, _ = self.make_module([blocked, worker_bad_json])
        fallback.install(module, worker_url='https://worker.example')
        session = module.requests.Session()
        session.get('https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json')
        self.assertEqual(session._vestra_transport_diag['companyfacts_worker_payload'], {'json_error': 1})

    def test_direct_exception_then_worker_success_is_counted(self):
        worker_ok = FakeResponse(200, {'facts': {'us-gaap': {}}})
        module, _, _ = self.make_module([RuntimeError('network down'), worker_ok])
        fallback.install(module, worker_url='https://worker.example')
        session = module.requests.Session()
        response = session.get('https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json')
        self.assertIs(response, worker_ok)
        diag = session._vestra_transport_diag
        self.assertEqual(diag['companyfacts_direct_attempts'], 1)
        self.assertEqual(diag['companyfacts_direct_exceptions'], 1)
        self.assertEqual(diag['companyfacts_worker_success'], 1)

    def test_probe_empty_user_agent_disables_companyfacts_transport(self):
        module, factory, _ = self.make_module([])
        with mock.patch.dict(os.environ, {'SEC_USER_AGENT': ''}, clear=False):
            fallback.install(module, worker_url='https://worker.example')
            self.assertEqual(os.environ.get('SEC_DIRECT_BLOCKED'), '1')
            self.assertEqual(os.environ.get('SEC_COMPANYFACTS_BLOCKED'), '1')
            self.assertEqual(os.environ.get('SEC_USER_AGENT'), '')
            session = module.requests.Session()
            diag = session._vestra_transport_diag
            self.assertTrue(diag['direct_blocked_mode'])
            self.assertTrue(diag['probe_blocked_mode'])
            self.assertEqual(diag['companyfacts_direct_attempts'], 0)
            self.assertEqual(diag['companyfacts_worker_attempts'], 0)
            self.assertEqual(diag['companyfacts_worker_success'], 0)
        self.assertEqual(factory.instances[0].calls, [])

    def test_non_companyfacts_requests_are_never_proxied(self):
        original = FakeResponse(403)
        module, factory, _ = self.make_module([original])
        fallback.install(module, worker_url='https://worker.example')
        session = module.requests.Session()
        response = session.get('https://www.sec.gov/files/company_tickers.json')
        self.assertIs(response, original)
        self.assertEqual(len(factory.instances[0].calls), 1)
        self.assertEqual(session._vestra_transport_diag['companyfacts_direct_attempts'], 0)

    def test_enrich_wrapper_reports_transport_and_enriched_count(self):
        def original_enrich(rows, *args, **kwargs):
            session = module.requests.Session()
            session.get('https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json')
            rows[0].sec_edgar_enriched = True
            return rows

        row = types.SimpleNamespace(sec_edgar_enriched=False)
        module, _, logger = self.make_module(
            [FakeResponse(200, {'facts': {'us-gaap': {}}})],
            enrich=original_enrich,
        )
        fallback.install(module, worker_url='https://worker.example')
        result = module.enrich([row])
        self.assertIs(result[0], row)
        messages = [args for args in logger.info_messages if args and args[0] == 'SEC enrichment runtime diagnostics %s']
        self.assertEqual(len(messages), 1)
        self.assertIn('"newly_enriched_rows":1', messages[0][1])
        self.assertIn('"companyfacts_direct_success":1', messages[0][1])
        self.assertIn('"valid_facts":1', messages[0][1])

    def test_install_is_idempotent(self):
        module, _, _ = self.make_module([FakeResponse(200)])
        first = fallback.install(module, worker_url='https://worker.example')
        second = fallback.install(module, worker_url='https://worker.example')
        self.assertIs(first, second)


if __name__ == '__main__':
    unittest.main(verbosity=2)
