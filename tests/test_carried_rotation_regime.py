"""Old carried returns cannot determine current regime or rotation."""
import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location(
    "postprocess_market_carried_regime", ROOT / "scripts" / "postprocess_market.py")
market = importlib.util.module_from_spec(spec)
spec.loader.exec_module(market)


class CarriedMarketEvidenceTests(unittest.TestCase):
    def test_rotating_carried_equities_cannot_create_market_regime(self):
        old = [{"ticker": f"STALE{i}", "quote_type": "EQUITY",
                "pipeline_status": "equity_carried_forward_rotating",
                "market_return_5d_pct": -8.0, "market_return_20d_pct": -18.0}
               for i in range(40)]
        context = market._market_regime_context(old)
        self.assertEqual(context["regime"], "unavailable")
        self.assertEqual(context["evidence_count"], 0)

    def test_old_carried_equities_do_not_overrule_fresh_equity_breadth(self):
        current = [{"ticker": f"NOW{i}", "quote_type": "EQUITY",
                    "pipeline_status": "fresh", "market_return_5d_pct": 1.2,
                    "market_return_20d_pct": 5.5} for i in range(32)]
        old = [{"ticker": f"OLD{i}", "quote_type": "EQUITY",
                "pipeline_status": "equity_carried_forward_rotating",
                "market_return_5d_pct": -9.0, "market_return_20d_pct": -20.0}
               for i in range(100)]
        context = market._market_regime_context(current + old)
        self.assertEqual(context["source"], "equity_breadth")
        self.assertEqual(context["regime"], "supportive")
        self.assertEqual(context["evidence_count"], 32)

    def test_carried_benchmarks_do_not_invent_fresh_broad_regime(self):
        benchmarks = [{"ticker": ticker, "quote_type": "ETF",
                       "pipeline_status": "catalog_carried_forward",
                       "market_return_5d_pct": -10.0, "market_return_20d_pct": -20.0}
                      for ticker in market.MARKET_REGIME_BENCHMARKS]
        self.assertEqual(market._market_regime_context(benchmarks)["regime"], "unavailable")

    def test_rotating_carried_sectors_cannot_create_weekly_rotation(self):
        old = [{"ticker": f"OLDS{i}", "quote_type": "EQUITY",
                "industry": "Semiconductors",
                "pipeline_status": "equity_carried_forward_rotating",
                "market_return_5d_pct": 15.0} for i in range(6)]
        self.assertNotIn("Semicondutores", market._rotation_context(old))

    def test_only_fresh_members_count_for_weekly_rotation(self):
        current = [{"ticker": f"NOWS{i}", "quote_type": "EQUITY",
                    "industry": "Semiconductors", "pipeline_status": "fresh",
                    "market_return_5d_pct": -3.0} for i in range(4)]
        old = [{"ticker": f"OLDS{i}", "quote_type": "EQUITY",
                "industry": "Semiconductors",
                "pipeline_status": "equity_carried_forward_rotating",
                "market_return_5d_pct": 15.0} for i in range(8)]
        context = market._rotation_context(current + old)["Semicondutores"]
        self.assertEqual(context["signal"], "strong_outflow")
        self.assertEqual(context["member_count"], 4)

    def test_stale_etf_cannot_confirm_sector_flow(self):
        current = [{"ticker": f"CHIP{i}", "quote_type": "EQUITY",
                    "industry": "Semiconductors", "pipeline_status": "fresh",
                    "market_return_5d_pct": 3.0} for i in range(4)]
        old_etf = {"ticker": "SMH", "quote_type": "ETF",
                   "pipeline_status": "catalog_carried_forward",
                   "fund_return_1w_pct": 8.0, "fund_flow_1w_usd": 1_000_000_000}
        context = market._rotation_context(current + [old_etf])["Semicondutores"]
        self.assertEqual(context["signal"], "strong_inflow")
        self.assertIsNone(context["etf_confirmed"])
        self.assertEqual(context["etf_evidence_count"], 0)


if __name__ == "__main__":
    unittest.main()
