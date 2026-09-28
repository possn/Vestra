import importlib.util
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location("postprocess_market", SCRIPTS / "postprocess_market.py")
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


def prices(r5=0.0, r20=0.0):
    base = 100.0
    values = [base] * 21
    values[-6] = base / (1.0 + r5 / 100.0) if r5 != -100 else base
    values[0] = base / (1.0 + r20 / 100.0) if r20 != -100 else base
    values[-1] = base
    return [{"close": x} for x in values]


class MarketRegimeContextTests(unittest.TestCase):
    def test_broad_benchmarks_take_precedence_when_available(self):
        rows = []
        for ticker in ("ACWI", "SPY", "QQQ", "IWM", "EFA", "EEM"):
            rows.append({
                "ticker": ticker,
                "quote_type": "ETF",
                "price_history_1y": prices(r5=1.0, r20=5.0),
            })
        ctx = MOD._market_regime_context(rows)
        self.assertEqual(ctx["source"], "broad_benchmarks")
        self.assertEqual(ctx["regime"], "supportive")
        self.assertEqual(ctx["evidence_count"], 6)

    def test_severe_adverse_benchmark_regime_is_detected(self):
        rows = []
        for i, ticker in enumerate(("ACWI", "SPY", "QQQ", "IWM", "EFA", "EEM")):
            rows.append({
                "ticker": ticker,
                "quote_type": "ETF",
                "price_history_1y": prices(r5=-5.0, r20=-10.0 if i < 5 else 2.0),
            })
        ctx = MOD._market_regime_context(rows)
        self.assertEqual(ctx["regime"], "severe_adverse")
        self.assertLessEqual(ctx["breadth_20d_pct"], 30)

    def test_equity_breadth_is_only_a_fallback(self):
        rows = []
        for i in range(35):
            rows.append({
                "ticker": f"E{i}",
                "quote_type": "EQUITY",
                "pipeline_status": "fresh",
                "price_history_1y": prices(r5=-1.0, r20=-5.0 if i < 25 else 2.0),
            })
        ctx = MOD._market_regime_context(rows)
        self.assertEqual(ctx["source"], "equity_breadth")
        self.assertEqual(ctx["regime"], "adverse")

    def test_insufficient_market_evidence_stays_unavailable(self):
        ctx = MOD._market_regime_context([])
        self.assertEqual(ctx["regime"], "unavailable")
        self.assertEqual(ctx["evidence_count"], 0)


    def _semiconductor_rows(self, etf_return=None, etf_flow=None):
        rows = [
            {
                "ticker": f"CHIP{i}",
                "quote_type": "EQUITY",
                "industry": "Semiconductors",
                "opportunity_return_5d_pct": 3.0 + i * 0.1,
            }
            for i in range(4)
        ]
        rows.append({
            "ticker": "SMH",
            "quote_type": "ETF",
            "fund_return_1w_pct": etf_return,
            "fund_flow_1w_usd": etf_flow,
        })
        return rows

    def test_rotation_etf_confirmation_requires_available_evidence_consensus(self):
        ctx = MOD._rotation_context(self._semiconductor_rows(etf_return=2.0, etf_flow=150_000_000))
        semi = ctx["Semicondutores"]
        self.assertEqual(semi["signal"], "strong_inflow")
        self.assertIs(semi["etf_confirmed"], True)
        self.assertEqual(semi["etf_evidence_count"], 2)

    def test_rotation_etf_conflict_is_not_confirmed(self):
        ctx = MOD._rotation_context(self._semiconductor_rows(etf_return=2.0, etf_flow=-150_000_000))
        semi = ctx["Semicondutores"]
        self.assertIs(semi["etf_confirmed"], False)
        self.assertEqual(semi["etf_evidence_count"], 2)

    def test_rotation_etf_neutral_or_missing_evidence_stays_unknown(self):
        ctx = MOD._rotation_context(self._semiconductor_rows(etf_return=0.0, etf_flow=None))
        semi = ctx["Semicondutores"]
        self.assertIsNone(semi["etf_confirmed"])
        self.assertEqual(semi["etf_evidence_count"], 0)



if __name__ == "__main__":
    unittest.main(verbosity=2)
