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
    def __init__(self, ticker, error=None, **kwargs):
        self.ticker = ticker
        self.error = error
        for key, value in kwargs.items():
            setattr(self, key, value)


class Coordinator:
    def __init__(self, strike=0, last_incident_at=None, quiet_reset_seconds=120):
        self.strike = strike
        self.last_incident_at = last_incident_at
        self.quiet_reset_seconds = quiet_reset_seconds

    def snapshot(self):
        state = {'strike': self.strike}
        if self.last_incident_at is not None:
            state['last_incident_at'] = self.last_incident_at
        return state


class YahooRetryHygieneTests(unittest.TestCase):
    def make_module(self, scripted, *, strike=0, coordinator=None):
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
        module = types.SimpleNamespace(
            fetch_many=fetch_many,
            log=log,
            _rate_limit_coordinator=coordinator or Coordinator(strike),
        )
        return module, calls

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

    def test_price_only_row_after_throttle_gets_one_recovery_attempt(self):
        sparse = Row('MSFT', None, current_price=500.0)
        improved = Row('MSFT', None, current_price=501.0, market_cap=3_000_000_000_000, sector='Technology')
        module, calls = self.make_module([[sparse], [improved]], strike=1)
        wrapped = hygiene.install(module, sleeper=lambda _: None)
        rows = wrapped(['MSFT'], retries=3)
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[1]['tickers'], ['MSFT'])
        self.assertIs(rows[0], improved)
        self.assertEqual(rows[0].sector, 'Technology')

    def test_price_only_row_is_not_retried_without_recorded_throttle(self):
        sparse = Row('MSFT', None, current_price=500.0)
        module, calls = self.make_module([[sparse]], strike=0)
        wrapped = hygiene.install(module, sleeper=lambda _: None)
        rows = wrapped(['MSFT'], retries=3)
        self.assertEqual(len(calls), 1)
        self.assertIs(rows[0], sparse)

    def test_stale_throttle_does_not_poison_later_batch(self):
        sparse = Row('MSFT', None, current_price=500.0)
        stale = Coordinator(strike=3, last_incident_at=1.0, quiet_reset_seconds=120)
        module, calls = self.make_module([[sparse]], coordinator=stale)
        wrapped = hygiene.install(module, sleeper=lambda _: None)
        rows = wrapped(['MSFT'], retries=3)
        self.assertEqual(len(calls), 1)
        self.assertIs(rows[0], sparse)

    def test_failed_price_only_retry_preserves_usable_fallback(self):
        sparse = Row('MSFT', None, current_price=500.0)
        retry_error = Row('MSFT', 'Too Many Requests. Rate limited.')
        module, calls = self.make_module([[sparse], [retry_error]], strike=1)
        wrapped = hygiene.install(module, sleeper=lambda _: None)
        rows = wrapped(['MSFT'], retries=3)
        self.assertEqual(len(calls), 2)
        self.assertIs(rows[0], sparse)
        self.assertEqual(rows[0].current_price, 500.0)
        self.assertIsNone(rows[0].error)

    def test_etf_price_only_shape_is_not_treated_as_equity_degradation(self):
        etf = Row('SPY', None, current_price=600.0, quote_type='ETF')
        module, calls = self.make_module([[etf]], strike=1)
        wrapped = hygiene.install(module, sleeper=lambda _: None)
        rows = wrapped(['SPY'], retries=3)
        self.assertEqual(len(calls), 1)
        self.assertIs(rows[0], etf)

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
