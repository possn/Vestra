from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"


class OfficialRetrievalEquityContractTests(unittest.TestCase):
    def test_sec_enricher_uses_canonical_equity_candidate_contract(self):
        src = (SCRIPTS / "sec_enrich.py").read_text(encoding="utf-8")
        self.assertIn("from asset_types import is_equity_candidate", src)
        self.assertIn("not is_equity_candidate(getattr(m,'quote_type',None))", src)
        self.assertNotIn("getattr(m,'quote_type',None) in ('ETF','CRYPTO')", src)

    def test_esef_enricher_uses_canonical_equity_candidate_contract(self):
        src = (SCRIPTS / "esef_enrich_v416.py").read_text(encoding="utf-8")
        self.assertIn("from asset_types import is_equity_candidate", src)
        self.assertIn("not is_equity_candidate(getattr(m,'quote_type',None))", src)
        self.assertNotIn("getattr(m,'quote_type',None) in ('ETF','CRYPTO')", src)

    def test_capital_risk_uses_canonical_equity_candidate_contract(self):
        src = (SCRIPTS / "capital_risk.py").read_text(encoding="utf-8")
        self.assertIn("from asset_types import is_equity_candidate", src)
        self.assertIn("not is_equity_candidate(getattr(m, \"quote_type\", None))", src)
        self.assertNotIn('getattr(m, "quote_type", None) in ("ETF", "CRYPTO")', src)

    def test_canonical_contract_keeps_unknown_types_unresolved_candidates(self):
        src = (SCRIPTS / "asset_types.py").read_text(encoding="utf-8")
        self.assertIn("return not is_explicit_non_equity(value)", src)


if __name__ == "__main__":
    unittest.main(verbosity=2)
