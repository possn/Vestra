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

    def test_direct_success_does_not_call_worker(self):
        direct_ok = FakeResponse(200)
        module, factory = self.make_module([direct_ok])
        fallback.install(module, worker_url='https://worker.example')
        session = module.requests.Session()
        response = session.get('https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json')
        self.assertIs(response, direct_ok)
        self.assertEqual(len(factory.instances[0].calls), 1)
        self.assertIn('data.sec.gov', factory.instances[0].calls[0][0])

    def test_direct_403_retries_same_cik_via_worker(self):
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

    def test_probe_empty_user_agent_becomes_direct_block_signal(self):
        module, factory = self.make_module([FakeResponse(200)])
        with mock.patch.dict(os.environ, {'SEC_USER_AGENT': ''}, clear=False):
            fallback.install(module, worker_url='https://worker.example')
            self.assertEqual(os.environ.get('SEC_DIRECT_BLOCKED'), '1')
            self.assertEqual(os.environ.get('SEC_USER_AGENT'), fallback.DEFAULT_SEC_USER_AGENT)
            session = module.requests.Session()
            session.get('https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json')
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

    def test_install_is_idempotent(self):
        module, _ = self.make_module([FakeResponse(200)])
        first = fallback.install(module, worker_url='https://worker.example')
        second = fallback.install(module, worker_url='https://worker.example')
        self.assertIs(first, second)


if __name__ == '__main__':
    unittest.main(verbosity=2)
