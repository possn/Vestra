import importlib.util
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("smallcap",ROOT/"research/prebreakout/smallcap_universe_inventory.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class SmallCapInventoryTests(unittest.TestCase):
    def test_cohorts_are_deduplicated_and_live_floor_unchanged(self):
        rows=[
            {"ticker":"MICRO","market_cap":100_000_000,"quote_type":"EQUITY"},
            {"ticker":"MICRO","market_cap":110_000_000,"quote_type":"EQUITY"},
            {"ticker":"SMALL","market_cap":700_000_000,"quote_type":"EQUITY"},
            {"ticker":"LIMIT","market_cap":2_000_000_000,"quote_type":"EQUITY"},
            {"ticker":"ETF","market_cap":800_000_000,"quote_type":"ETF"},
            {"ticker":"TINY","market_cap":90_000_000,"quote_type":"EQUITY"},
            {"ticker":"LARGE","market_cap":2_000_000_001,"quote_type":"EQUITY"},
            {"ticker":"UNKNOWN","market_cap":None,"quote_type":"EQUITY"}]
        out=mod.inventory(rows)
        self.assertEqual(out["tickers"],["LIMIT","MICRO","SMALL"])
        self.assertEqual(out["under_live_scanner_cap_floor"],1)
        self.assertEqual(out["overlap_with_live_cap_universe"],2)
        self.assertEqual(out["distinct_tickers"],3)
        self.assertEqual(out["status"],"universe_inventory_only_not_ohlcv_verified")
        self.assertTrue(out["no_predictive_edge_claim"])

    def test_existing_market_scanner_keeps_its_cap_and_liquidity_gates(self):
        script=(ROOT/"scripts/refresh_prebreakout_scanner.py").read_text()
        self.assertIn("cap<500_000_000",script)
        self.assertIn("usd_turnover<5_000_000",script)
        html=(ROOT/"index.html").read_text()
        self.assertIn("<strong>Breakout Lab</strong>",html)
        self.assertIn("data-market-tool=\"scanner\"",html)
        self.assertIn("small caps em avaliação experimental",html)

if __name__=="__main__":
    unittest.main()
