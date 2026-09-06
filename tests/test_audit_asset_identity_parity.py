import pathlib
import sys
import types
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

# Keep the architecture image dependency-free while exercising the exact ETF
# catalogue fallback used in production.
universe_stub = types.ModuleType("universe")
universe_stub.ETF_UNIVERSE = {"SPY": {"region": "United States"}}
sys.modules["universe"] = universe_stub

import coverage_audit
import coverage_guard
import provenance_audit


class AuditAssetIdentityParityTests(unittest.TestCase):
    def setUp(self):
        coverage_audit._CATALOG_ETF_TICKERS = None

    def test_catalog_etf_missing_provider_type_is_non_equity_everywhere(self):
        row = {"ticker": "SPY", "quote_type": None}
        payload = {"stocks": [row]}
        self.assertEqual(coverage_audit.authoritative_quote_type(row), "ETF")
        self.assertEqual(coverage_audit.equity_rows(payload), [])
        self.assertEqual(provenance_audit.equity_rows(payload), [])
        self.assertFalse(coverage_guard._equity(row))

    def test_unknown_missing_type_remains_candidate_everywhere(self):
        row = {"ticker": "UNKNOWN", "quote_type": None}
        payload = {"stocks": [row]}
        self.assertEqual(coverage_audit.authoritative_quote_type(row), "")
        self.assertEqual(coverage_audit.equity_rows(payload), [row])
        self.assertEqual(provenance_audit.equity_rows(payload), [row])
        self.assertTrue(coverage_guard._equity(row))

    def test_explicit_provider_type_still_wins(self):
        row = {"ticker": "SPY", "quote_type": "EQUITY"}
        payload = {"stocks": [row]}
        self.assertEqual(coverage_audit.authoritative_quote_type(row), "EQUITY")
        self.assertEqual(coverage_audit.equity_rows(payload), [row])
        self.assertEqual(provenance_audit.equity_rows(payload), [row])
        self.assertTrue(coverage_guard._equity(row))


if __name__ == "__main__":
    unittest.main(verbosity=2)
