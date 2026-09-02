from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import asset_types


class ExplicitAssetTypeContractTests(unittest.TestCase):
    def test_explicit_non_equity_set_is_complete(self):
        self.assertEqual(
            asset_types.NON_EQUITY_TYPES,
            frozenset({"ETF", "CRYPTO", "MUTUALFUND", "FUND"}),
        )
        for value in ("ETF", "crypto", " MutualFund ", "fund"):
            self.assertTrue(asset_types.is_explicit_non_equity(value), value)

    def test_unknown_identity_remains_candidate_not_asserted_non_equity(self):
        for value in (None, "", "UNKNOWN", "EQUITY"):
            self.assertFalse(asset_types.is_explicit_non_equity(value), value)
            self.assertTrue(asset_types.is_equity_candidate(value), value)

    def test_both_statement_retrievers_use_canonical_contract(self):
        for name in ("gap_retrieval.py", "quarterly_gap_retrieval.py"):
            source = (SCRIPTS / name).read_text(encoding="utf-8")
            self.assertIn("from asset_types import is_explicit_non_equity", source, name)
            self.assertIn("is_explicit_non_equity(getattr(m", source, name)
            self.assertNotIn('in ("ETF", "CRYPTO")', source, name)
            self.assertNotIn('in ("ETF","CRYPTO")', source, name)


if __name__ == "__main__":
    unittest.main(verbosity=2)
