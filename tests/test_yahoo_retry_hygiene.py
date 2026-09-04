import os
import sys
import types
import unittest

ROOT = os.path.dirname(os.path.dirname(__file__))
SCRIPTS = os.path.join(ROOT, 'scripts')
if SCRIPTS not in sys.path:
    sys.path.insert(0, SCRIPTS)

import yahoo_retry_hygiene as hygiene


class Row:
    def __init__(self, ticker, error=None):
        self.ticker = ticker
        self.error = error


class YahooRetryHygieneTests(unittest.TestCase):
    def make_module(self, scripted):
        calls = []
        queue = list(scripted)

        def fetch_many(tickers, pause=0.0, workers_override=None, retries=3):
            calls.append({
                'tickers': list(tickers),
                'pause': pause,
                'workers_override': workers_override,
                'retries': retries,
            })
            if not queue:
                raise AssertionError('unexpected fetch_many call')
            return queue.pop(0)

        log = types.SimpleNamespace(info=lambda *a, **k: None, warning=lambda *a, **k: None)
        return types.SimpleNamespace(fetch_many=fetch_many, log=log), calls

    def test_hard_error_classifier_is_narrow(self):
        self.assertTrue(hygiene.is_hard_symbol_error('possibly delisted; no timezone found'))
        self.assertTrue(hygiene.is_hard_symbol_error('404 Client Error: Not Found'))
        self.assertTrue(hygiene.is_hard_symbol_error('No price data found, symbol may be delisted'))
        self.assertFalse(hygiene.is_hard_symbol_error('Too Many Requests. Rate limited.'))
        self.assertFalse(hygiene.is_hard_symbol_error('Read timed out'))
        self.assertFalse(hygiene.is_hard_symbol_error('temporary connection reset'))

    def test_hard_failure_is_not_retried_in_same_run(self):
        module, calls = self.make_module([[Row('BAD', 'possibly delisted; no timezone found')]])
        wrapped = hygiene.install(module, sleeper=lambda _: None)
        rows = wrapped(['BAD'], retries=3)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]['retries'], 0)
        self.assertEqual(rows[0].ticker, 'BAD')
        self.assertIsNotNone(rows[0].error)

    def test_transient_failure_is_retried_and_can_recover(self):
        module, calls = self.make_module([
            [Row('AAPL', 'Too Many Requests. Rate limited.')],
            [Row('AAPL', None)],
        ])
        sleeps = []
        wrapped = hygiene.install(module, sleeper=sleeps.append)
        rows = wrapped(['AAPL'], retries=2)
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[1]['tickers'], ['AAPL'])
        self.assertEqual(calls[1]['workers_override'], 1)
        self.assertEqual(calls[1]['retries'], 0)
        self.assertEqual(sleeps, [6])
        self.assertIsNone(rows[0].error)

    def test_mixed_batch_retries_only_transient_names(self):
        module, calls = self.make_module([
            [Row('BAD', '404 Client Error: Not Found'), Row('MSFT', 'Read timed out'), Row('AAPL', None)],
            [Row('MSFT', None)],
        ])
        wrapped = hygiene.install(module, sleeper=lambda _: None)
        rows = wrapped(['BAD', 'MSFT', 'AAPL'], retries=2)
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[1]['tickers'], ['MSFT'])
        by_ticker = {row.ticker: row for row in rows}
        self.assertIsNotNone(by_ticker['BAD'].error)
        self.assertIsNone(by_ticker['MSFT'].error)
        self.assertIsNone(by_ticker['AAPL'].error)

    def test_policy_is_not_persistent_across_runs(self):
        module1, calls1 = self.make_module([[Row('BAD', 'possibly delisted')]])
        hygiene.install(module1, sleeper=lambda _: None)(['BAD'], retries=3)
        self.assertEqual(len(calls1), 1)

        module2, calls2 = self.make_module([[Row('BAD', None)]])
        hygiene.install(module2, sleeper=lambda _: None)(['BAD'], retries=3)
        self.assertEqual(len(calls2), 1)
        self.assertEqual(calls2[0]['tickers'], ['BAD'])

    def test_install_is_idempotent(self):
        module, _ = self.make_module([[Row('AAPL', None)]])
        first = hygiene.install(module, sleeper=lambda _: None)
        second = hygiene.install(module, sleeper=lambda _: None)
        self.assertIs(first, second)


if __name__ == '__main__':
    unittest.main(verbosity=2)
