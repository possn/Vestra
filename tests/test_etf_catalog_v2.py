from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class EtfCatalogV2Tests(unittest.TestCase):
    def test_compact_etf_evidence_and_full_catalogue_are_first_class(self):
        intel = (ROOT / "market-etf-intelligence.js").read_text(encoding="utf-8")
        market = (ROOT / "market.js").read_text(encoding="utf-8")
        shards = (ROOT / "scripts" / "build_market_shards.py").read_text(encoding="utf-8")
        loader = (ROOT / "market-static-universe.js").read_text(encoding="utf-8")
        self.assertIn("fund_top10_weight_pct", intel)
        self.assertIn('"fund_total_assets"', shards)
        self.assertIn('out["fund_top10_weight_pct"]', shards)
        self.assertIn("['all','Todos os ETFs',/.+/i]", market)
        self.assertIn("data-market-fund-more", market)
        self.assertIn("M.fundLimit+=100", market)
        self.assertIn("n(b.etf_score)", market)
        self.assertIn("market-etf-intelligence.js?v=1.2", loader)

if __name__ == "__main__":
    unittest.main(verbosity=2)
