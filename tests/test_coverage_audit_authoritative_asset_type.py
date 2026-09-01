import pathlib
import sys
import types
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

# coverage_audit imports universe only for the deterministic ETF catalogue.
# Avoid importing yfinance/pandas in the lightweight architecture test image.
universe_stub = types.ModuleType("universe")
universe_stub.ETF_UNIVERSE = {"SPY": {"sector": "Broad Market", "region": "United States"}}
sys.modules.setdefault("universe", universe_stub)

import coverage_audit


class CoverageAuditAuthoritativeAssetTypeTests(unittest.TestCase):
    def test_catalog_etf_recovers_missing_reported_quote_type(self):
        row = {"ticker": "SPY", "quote_type": None}
        self.assertEqual(coverage_audit.normalized_quote_type(row), "")
        self.assertEqual(coverage_audit.authoritative_quote_type(row), "ETF")
        self.assertEqual(coverage_audit.identity_state(row), "non_equity")

    def test_unknown_missing_type_remains_unresolved(self):
        row = {"ticker": "UNKNOWN", "quote_type": None}
        self.assertEqual(coverage_audit.authoritative_quote_type(row), "")
        self.assertEqual(coverage_audit.identity_state(row), "unresolved")

    def test_explicit_type_wins_over_catalog_fallback(self):
        row = {"ticker": "SPY", "quote_type": "EQUITY"}
        self.assertEqual(coverage_audit.authoritative_quote_type(row), "EQUITY")
        self.assertEqual(coverage_audit.identity_state(row), "confirmed_equity")

    def test_catalog_etf_is_excluded_from_equity_rows(self):
        payload = {"stocks": [
            {"ticker": "SPY", "quote_type": None},
            {"ticker": "AAPL", "quote_type": "EQUITY"},
            {"ticker": "UNKNOWN", "quote_type": None},
        ]}
        tickers = [row["ticker"] for row in coverage_audit.equity_rows(payload)]
        self.assertEqual(tickers, ["AAPL", "UNKNOWN"])


if __name__ == "__main__":
    unittest.main()
