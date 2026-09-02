import pathlib
import sys
import types
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

universe_stub = types.ModuleType("universe")
universe_stub.ETF_UNIVERSE = {"SPY": {"sector": "Broad Market", "region": "United States"}}
sys.modules.setdefault("universe", universe_stub)

import coverage_audit


class CoverageAuditRuntimeIdentityParityTests(unittest.TestCase):
    def test_known_asset_override_recovers_exact_identity(self):
        row = {"ticker": "SPYL.DE", "quote_type": None}
        self.assertEqual(coverage_audit.authoritative_quote_type(row), "ETF")
        self.assertEqual(coverage_audit.authoritative_identity_evidence(row), "known_asset_identity")
        self.assertEqual(coverage_audit.identity_state(row), "non_equity")

    def test_ticker_successor_recovers_exact_equity_identity(self):
        row = {"ticker": "BITF", "quote_type": None}
        self.assertEqual(coverage_audit.authoritative_quote_type(row), "EQUITY")
        self.assertEqual(coverage_audit.authoritative_identity_evidence(row), "ticker_successor")
        self.assertEqual(coverage_audit.identity_state(row), "confirmed_equity")

    def test_unknown_missing_type_remains_unresolved(self):
        row = {"ticker": "UNKNOWN", "quote_type": None}
        self.assertEqual(coverage_audit.authoritative_quote_type(row), "")
        self.assertEqual(coverage_audit.authoritative_identity_evidence(row), "")
        self.assertEqual(coverage_audit.identity_state(row), "unresolved")

    def test_explicit_current_type_wins_over_override(self):
        row = {"ticker": "SPYL.DE", "quote_type": "EQUITY"}
        self.assertEqual(coverage_audit.authoritative_quote_type(row), "EQUITY")
        self.assertEqual(coverage_audit.identity_state(row), "confirmed_equity")


if __name__ == "__main__":
    unittest.main()
