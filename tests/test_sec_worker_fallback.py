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
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self.ok = 200 <= status_code < 300
        self.payload = payload or {}


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


class SecWorkerFallbackTests(unittest.TestCase):
    def make_module(self, responses):
        factory = SessionFactory(responses)
        module = types.SimpleNamespace(
            requests=types.SimpleNamespace(Session=factory),
            log=types.SimpleNamespace(warning=lambda *a, **k: None, debug=lambda *a, **k: None),
        )
        return module, factory

    def tearDown(self):
        os.environ.pop('SEC_DIRECT_BLOCKED', None)
        os.environ.pop('SEC_USER_AGENT', None)

    def test_worker_url_extracts_exact_cik(self):
        direct = 'https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json'
        self.assertEqual(
            fallback._worker_url(direct, 'https://worker.example'),
            'https://worker.example/sec/companyfacts?cik=320193',
        )
        self.assertIsNone(fallback._worker_url('https://www.sec.gov/files/company_tickers.json', 'https://worker.example'))

    def test_direct_success_does_not_call_worker_and_is_counted(self):
        direct_ok = FakeResponse(200)
        module, factory = self.make_module([direct_ok])
        fallback.install(module, worker_url='https://worker.example')
        session = module.requests.Session()
        response = session.get('https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json')
        self.assertIs(response, direct_ok)
        self.assertEqual(len(factory.instances[0].calls), 1)
        self.assertIn('data.sec.gov', factory.instances[0].calls[0][0])
        self.assertEqual(session._vestra_transport_diag['companyfacts_direct_attempts'], 1)
        self.assertEqual(session._vestra_transport_diag['companyfacts_direct_success'], 1)
        self.assertEqual(session._vestra_transport_diag['companyfacts_direct_status'], {'200': 1})
        self.assertEqual(session._vestra_transport_diag['companyfacts_worker_attempts'], 0)

    def test_direct_403_retries_same_cik_via_worker_and_counts_both_legs(self):
        blocked = FakeResponse(403)
        worker_ok = FakeResponse(200)
        module, factory = self.make_module([blocked, worker_ok])
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

    def test_worker_502_is_counted_and_direct_failure_is_returned(self):
        blocked = FakeResponse(403)
        worker_bad = FakeResponse(502)
        module, _ = self.make_module([blocked, worker_bad])
        fallback.install(module, worker_url='https://worker.example')
        session = module.requests.Session()
        response = session.get('https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json')
        self.assertIs(response, blocked)
        diag = session._vestra_transport_diag
        self.assertEqual(diag['companyfacts_direct_status'], {'403': 1})
        self.assertEqual(diag['companyfacts_worker_attempts'], 1)
        self.assertEqual(diag['companyfacts_worker_status'], {'502': 1})
        self.assertEqual(diag['companyfacts_worker_success'], 0)

    def test_direct_exception_then_worker_success_is_counted(self):
        worker_ok = FakeResponse(200)
        module, _ = self.make_module([RuntimeError('network down'), worker_ok])
        fallback.install(module, worker_url='https://worker.example')
        session = module.requests.Session()
        response = session.get('https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json')
        self.assertIs(response, worker_ok)
        diag = session._vestra_transport_diag
        self.assertEqual(diag['companyfacts_direct_attempts'], 1)
        self.assertEqual(diag['companyfacts_direct_exceptions'], 1)
        self.assertEqual(diag['companyfacts_worker_success'], 1)

    def test_probe_empty_user_agent_becomes_direct_block_signal(self):
        module, factory = self.make_module([FakeResponse(200)])
        with mock.patch.dict(os.environ, {'SEC_USER_AGENT': ''}, clear=False):
            fallback.install(module, worker_url='https://worker.example')
            self.assertEqual(os.environ.get('SEC_DIRECT_BLOCKED'), '1')
            self.assertEqual(os.environ.get('SEC_USER_AGENT'), fallback.DEFAULT_SEC_USER_AGENT)
            session = module.requests.Session()
            session.get('https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json')
            self.assertTrue(session._vestra_transport_diag['direct_blocked_mode'])
            self.assertEqual(session._vestra_transport_diag['companyfacts_direct_attempts'], 0)
            self.assertEqual(session._vestra_transport_diag['companyfacts_worker_success'], 1)
        calls = [url for url, _ in factory.instances[0].calls]
        self.assertEqual(calls, ['https://worker.example/sec/companyfacts?cik=320193'])

    def test_non_companyfacts_requests_are_never_proxied(self):
        original = FakeResponse(403)
        module, factory = self.make_module([original])
        fallback.install(module, worker_url='https://worker.example')
        session = module.requests.Session()
        response = session.get('https://www.sec.gov/files/company_tickers.json')
        self.assertIs(response, original)
        self.assertEqual(len(factory.instances[0].calls), 1)
        self.assertEqual(session._vestra_transport_diag['companyfacts_direct_attempts'], 0)

    def test_install_is_idempotent(self):
        module, _ = self.make_module([FakeResponse(200)])
        first = fallback.install(module, worker_url='https://worker.example')
        second = fallback.install(module, worker_url='https://worker.example')
        self.assertIs(first, second)


if __name__ == '__main__':
    unittest.main(verbosity=2)
