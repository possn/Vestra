#!/usr/bin/env python3
"""Deterministic contract tests; synthetic rows are NOT empirical validation."""
import unittest
from ohlcv_observation_audit import audit_ohlcv_rows

CAL = ["2025-01-02", "2025-01-03", "2025-01-06"]
ROW = {"symbol": "TEST", "session": "2025-01-02", "open": "10",
       "high": "12", "low": "9", "close": "11", "volume": "100"}

def run(rows, **kwargs):
    return audit_ohlcv_rows(rows, reference_sessions=CAL, evaluation_date="2025-01-06", **kwargs)

class ObservationAuditTests(unittest.TestCase):
    def test_valid_observation(self):
        result = run([dict(ROW)])
        self.assertTrue(result["admitted"])
        self.assertEqual(result["rows"], 1)
        self.assertEqual(result["symbols"], 1)

    def test_empty_data_rejected(self):
        self.assertIn("empty_rows", run([])["failures"])

    def test_duplicate_symbol_session_rejected(self):
        self.assertIn("duplicate_symbol_session", run([dict(ROW), dict(ROW)])["failures"])

    def test_inverted_ohlc_rejected(self):
        row = dict(ROW, high="10")
        self.assertIn("inconsistent_ohlc", run([row])["failures"])

    def test_negative_volume_rejected(self):
        self.assertIn("invalid_price_or_volume", run([dict(ROW, volume="-2")])["failures"])

    def test_nonfinite_price_rejected(self):
        self.assertIn("invalid_numeric", run([dict(ROW, close="NaN")])["failures"])

    def test_outside_calendar_rejected(self):
        self.assertIn("session_outside_calendar", run([dict(ROW, session="2025-01-04")])["failures"])

    def test_future_session_rejected(self):
        self.assertIn("future_session", run([dict(ROW, session="2025-01-07")])["failures"])

    def test_missing_calendar_rejected(self):
        result = audit_ohlcv_rows([ROW], reference_sessions=None)
        self.assertFalse(result["admitted"])

    def test_unordered_calendar_rejected(self):
        result = audit_ohlcv_rows([ROW], reference_sessions=list(reversed(CAL)))
        self.assertIn("invalid_reference_sessions", result["failures"])

    def test_nonmonotonic_symbol_rejected(self):
        row = dict(ROW, session="2025-01-03")
        self.assertIn("nonmonotonic_symbol_sessions", run([row, ROW])["failures"])

    def test_different_symbols_same_session_allowed(self):
        self.assertTrue(run([ROW, dict(ROW, symbol="OTHER")])["admitted"])

if __name__ == "__main__":
    unittest.main()
