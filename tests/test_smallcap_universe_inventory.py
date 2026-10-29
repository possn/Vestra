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

    def test_ohlcv_coverage_is_distinct_from_universe_membership(self):
        group=mod.inventory([
            {"ticker":"A","market_cap":120_000_000,"quote_type":"EQUITY"},
            {"ticker":"B","market_cap":250_000_000,"quote_type":"EQUITY"},
            {"ticker":"C","market_cap":800_000_000,"quote_type":"EQUITY"}])
        report=mod.coverage_diagnostic(group,[
            {"ticker":"A","evaluable":False},
            {"ticker":"A","evaluable":True},
            {"ticker":"B","evaluable":False},
            {"ticker":"EXTERNAL","evaluable":True}])
        self.assertEqual(report["universe_count"],3)
        self.assertEqual(report["evaluable_ohlcv"],1)
        self.assertEqual(report["observed_incomplete"],1)
        self.assertEqual(report["not_observed"],1)
        self.assertEqual(report["coverage_pct"],33.33)
        self.assertTrue(report["not_breakout_candidates"])

    def test_research_queue_rotates_without_claiming_provider_coverage(self):
        sample={"tickers":["D","A","B","C"]}
        self.assertEqual(mod.research_rotation(sample,0,2)["planned"],["A","B"])
        self.assertEqual(mod.research_rotation(sample,1,2)["planned"],["C","D"])
        self.assertEqual(mod.research_rotation(sample,2,2)["planned"],["A","B"])
        self.assertEqual(mod.research_rotation(sample,0,2)["status"],"planned_not_downloaded")
        self.assertTrue(mod.research_rotation(sample,0,2)["no_ohlcv_claim"])
        with self.assertRaises(ValueError):
            mod.research_rotation(sample,-1,2)
        with self.assertRaises(ValueError):
            mod.research_rotation(sample,0,0)

    def test_existing_market_scanner_keeps_its_cap_and_liquidity_gates(self):
        script=(ROOT/"scripts/refresh_prebreakout_scanner.py").read_text()
        self.assertIn("cap<500_000_000",script)
        self.assertIn("usd_turnover<5_000_000",script)
        html=(ROOT/"index.html").read_text()
        self.assertIn("<strong>Breakout Lab</strong>",html)
        self.assertIn("data-market-tool=\"scanner\"",html)
        self.assertIn("market-breakout-lab-tab",html)
        self.assertIn("aria-label=\"Abrir Breakout Lab\"",html)

if __name__=="__main__":
    unittest.main()
