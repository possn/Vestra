import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

SPEC = importlib.util.spec_from_file_location("vestra_score_peer_shadow", SCRIPTS / "score_peer_shadow.py")
mod = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(mod)


def tech_row(i):
    return {
        "ticker": f"T{i}",
        "score_model": "growth_tech",
        "score": 50,
        "score_raw": 50,
        "market_cap": 1000,
        "fcf_yield": 0.01 * (i + 1),
        "forward_pe": 20,
        "roe": 0.1,
        "roa": 0.05,
        "profit_margin": 0.1,
        "operating_margin": 0.15,
        "gross_margin": 0.5,
        "revenue_growth": 0.2,
        "earnings_growth": 0.2,
        "earnings_quarterly_growth": 0.2,
        "current_ratio": 2,
        "quick_ratio": 1.5,
        "debt_to_equity": 0.5,
        "net_cash": 100,
        "interest_coverage": 8,
        "operating_cash_flow": 100,
        "beta": 1,
        "revenue_yoy_acceleration_pp": 1,
        "net_margin_yoy_change_pp": 1,
        "eps_yoy_acceleration_pp": 1,
        "cash_conversion_ratio": 1,
        "accrual_ratio": 0,
        "fcf_margin": 0.1,
        "diluted_shares_yoy": 0,
        "roce_proxy": 0.15,
    }


class ScorePeerShadowModelTests(unittest.TestCase):
    def test_growth_tech_fcf_yield_keeps_higher_is_better_direction(self):
        peers = [tech_row(i) for i in range(20)]
        row = peers[-1]
        ctx = mod.ShadowContext(row, peers, peers)
        _, dims = mod.growth_tech_shadow(ctx)
        # Forward P/E is tied and therefore contributes 0 after inversion.
        # The highest plausible FCF yield must contribute 100, leaving valuation at 50.
        self.assertAlmostEqual(dims["Valuation"], 50.0)

    def test_biotech_native_peer_pillars_are_preserved_exactly(self):
        row = {
            "ticker": "BIO",
            "score_model": "biotech",
            "score_dimensions": {
                "Cash Runway": 83.0,
                "Net Cash": 72.0,
                "Dilution Discipline": 64.0,
                "Operating Quality": 58.0,
            },
            "revenue_growth": 0.2,
            "earnings_growth": 0.1,
            "earnings_quarterly_growth": 0.15,
            "beta": 1.0,
        }
        peers = []
        for i in range(20):
            peer = dict(row)
            peer["ticker"] = f"B{i}"
            peer["revenue_growth"] = 0.01 * i
            peer["earnings_growth"] = 0.01 * i
            peer["earnings_quarterly_growth"] = 0.01 * i
            peer["beta"] = 0.8 + i * 0.02
            peers.append(peer)
        peers[-1] = row
        ctx = mod.ShadowContext(row, peers, peers)
        _, dims = mod.biotech_shadow(ctx)
        self.assertEqual(dims["Cash Runway"], 83.0)
        self.assertEqual(dims["Net Cash"], 72.0)
        self.assertEqual(dims["Dilution Discipline"], 64.0)
        self.assertEqual(dims["Operating Quality"], 58.0)
        native_scopes = [x for x in ctx.scopes if x["scope"] == "production_peer_native"]
        self.assertEqual(len(native_scopes), 4)

    def test_structural_candidate_uses_existing_risk_cap(self):
        self.assertEqual(mod.apply_cap(82, {"score_cap": 59}), 59)
        self.assertEqual(mod.apply_cap(42, {"score_cap": 59}), 42)

    def test_build_shadow_covers_all_specialist_models_without_touching_general(self):
        rows = []
        for model in mod.SPECIALIST_MODELS:
            row = {
                "ticker": model.upper(),
                "quote_type": "EQUITY",
                "pipeline_status": "equity_live",
                "score_model": model,
                "score_raw": 50,
                "score": 50,
                "score_dimensions": {},
            }
            if model == "biotech":
                row["score_dimensions"] = {
                    "Cash Runway": 50, "Net Cash": 50,
                    "Dilution Discipline": 50, "Operating Quality": 50,
                }
            rows.append(row)
        rows.append({
            "ticker": "GENERAL", "quote_type": "EQUITY", "pipeline_status": "equity_live",
            "score_model": "general", "score_raw": 50, "score": 50,
        })
        _, _, summaries = mod.build_shadow(rows)
        self.assertEqual(set(summaries), set(mod.SPECIALIST_MODELS))
        self.assertNotIn("general", summaries)


if __name__ == "__main__":
    unittest.main(verbosity=2)
