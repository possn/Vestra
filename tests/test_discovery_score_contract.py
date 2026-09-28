import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("opportunity_rank", ROOT / "scripts" / "opportunity_rank.py")
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


def row(confidence=70, risk_gate="clear"):
    prices = [100 + i * 0.15 for i in range(90)]
    return {
        "ticker": "TEST",
        "quote_type": "EQUITY",
        "score": 72,
        "confidence_score": confidence,
        "data_coverage_pct": 82,
        "critical_metric_coverage_pct": 80,
        "score_reliability": "robust",
        "risk_gate": risk_gate,
        "price_history_1y": [{"close": p} for p in prices],
        "moat_score": 68,
        "capital_allocation_intelligence_score": 65,
        "qarp_score": 71,
        "value_trap_risk_score": 25,
        "sector_native_score": 67,
        "low52_opportunity_score": 60,
        "recovery_score": 64,
        "valuation_score": 62,
        "fair_value_upside_pct": 24,
        "margin_of_safety_pct": 8,
        "valuation_signal": "undervalued",
        "valuation_confidence": "medium",
        "analyst_price_target_upside_pct": 18,
        "analyst_eps_revisions_up_30d": 4,
        "analyst_eps_revisions_down_30d": 1,
        "estimate_momentum_score": 68,
        "estimate_signal": "improving",
        "recovery_status": "recovering",
        "thesis_direction": "up",
    }


class DiscoveryScoreContractTests(unittest.TestCase):
    def test_higher_confidence_does_not_buy_ranking_points_after_gate(self):
        low = MOD.assess(row(confidence=60))
        high = MOD.assess(row(confidence=95))
        self.assertTrue(low["opportunity_eligible"])
        self.assertTrue(high["opportunity_eligible"])
        self.assertEqual(low["opportunity_score_raw"], high["opportunity_score_raw"])

    def test_missing_optional_signal_does_not_renormalise_remaining_winners(self):
        complete = MOD.assess(row())
        sparse_row = row()
        sparse_row["moat_score"] = None
        sparse = MOD.assess(sparse_row)
        self.assertTrue(sparse["opportunity_eligible"])
        self.assertLess(sparse["opportunity_ranking_weight_coverage_pct"], complete["opportunity_ranking_weight_coverage_pct"])
        self.assertLess(sparse["opportunity_score_raw"], complete["opportunity_score_raw"])

    def test_sparse_discovery_evidence_is_explicitly_capped(self):
        sparse_row = row()
        for key in ("moat_score", "sector_native_score", "low52_opportunity_score", "recovery_score", "valuation_score"):
            sparse_row[key] = None
        sparse = MOD.assess(sparse_row)
        self.assertTrue(sparse["opportunity_eligible"])
        self.assertLess(sparse["opportunity_ranking_weight_coverage_pct"], 75)
        self.assertGreaterEqual(sparse["opportunity_structural_signal_count"], 2)
        self.assertLessEqual(sparse["opportunity_score"], 64)
        self.assertTrue(any("Discovery" in cap["reason"] for cap in sparse["opportunity_caps"]))

    def test_discovery_exposes_three_explainable_sleeves(self):
        out = MOD.assess(row())
        self.assertEqual(set(out["opportunity_sleeves"]), {"strength", "asymmetry", "inflection"})
        self.assertEqual(set(out["opportunity_sleeve_coverage_pct"]), {"strength", "asymmetry", "inflection"})
        self.assertTrue(all(0 <= value <= 100 for value in out["opportunity_sleeves"].values()))

    def test_correlated_strength_proxies_cannot_dominate_whole_discovery_score(self):
        base = row()
        weak = dict(base)
        weak.update({"score": 40, "moat_score": 40, "capital_allocation_intelligence_score": 40, "sector_native_score": 40})
        strong = dict(base)
        strong.update({"score": 100, "moat_score": 100, "capital_allocation_intelligence_score": 100, "sector_native_score": 100})
        weak_out, strong_out = MOD.assess(weak), MOD.assess(strong)
        self.assertEqual(weak_out["opportunity_sleeves"]["asymmetry"], strong_out["opportunity_sleeves"]["asymmetry"])
        self.assertEqual(weak_out["opportunity_sleeves"]["inflection"], strong_out["opportunity_sleeves"]["inflection"])
        # Strength is intentionally only 36% of the final Discovery composition.
        self.assertLess(strong_out["opportunity_score_raw"] - weak_out["opportunity_score_raw"], 25)

    def test_inflection_can_outrank_slightly_higher_structural_score(self):
        early = row()
        mature = row()
        early["score"] = 70
        mature["score"] = 75
        # A falling/late setup should not win Discovery merely via a higher Vestra Score.
        mature["price_history_1y"] = [{"close": 100 + i * 0.9} for i in range(90)]
        early_out, mature_out = MOD.assess(early), MOD.assess(mature)
        self.assertGreater(early_out["opportunity_sleeves"]["inflection"], mature_out["opportunity_sleeves"]["inflection"])
        self.assertGreater(early_out["opportunity_score"], mature_out["opportunity_score"])

    def test_confidence_still_gates_insufficient_evidence(self):
        out = MOD.assess(row(confidence=49))
        self.assertFalse(out["opportunity_eligible"])
        self.assertIsNone(out["opportunity_score"])
        self.assertIn("Confiança", out["opportunity_suppressed_reason"])

    def test_risk_gate_constrains_discovery_instead_of_rewarding_it(self):
        clear = MOD.assess(row(risk_gate="clear"))
        severe = MOD.assess(row(risk_gate="severe"))
        self.assertEqual(clear["opportunity_score_raw"], severe["opportunity_score_raw"])
        self.assertLessEqual(severe["opportunity_score"], 35)
        self.assertTrue(any(cap["reason"] == "Risk Gate severe" for cap in severe["opportunity_caps"]))

    def test_top_opportunity_requires_credible_upside_support(self):
        supported = MOD.assess(row())
        unsupported_row = row()
        for key in (
            "fair_value_upside_pct", "margin_of_safety_pct", "valuation_signal",
            "valuation_confidence", "analyst_price_target_upside_pct",
        ):
            unsupported_row[key] = None
        unsupported = MOD.assess(unsupported_row)
        self.assertEqual(supported["opportunity_upside_support"], "strong")
        self.assertEqual(unsupported["opportunity_upside_support"], "unavailable")
        self.assertLessEqual(unsupported["opportunity_score"], 64)
        self.assertTrue(any("Upside fundamental" in cap["reason"] for cap in unsupported["opportunity_caps"]))

    def test_moderate_upside_can_be_strong_but_not_high_priority(self):
        candidate = row()
        candidate.update({
            "fair_value_upside_pct": 12,
            "margin_of_safety_pct": -3,
            "analyst_price_target_upside_pct": None,
            "analyst_eps_revisions_up_30d": 0,
            "analyst_eps_revisions_down_30d": 0,
        })
        out = MOD.assess(candidate)
        self.assertEqual(out["opportunity_upside_support"], "moderate")
        self.assertLessEqual(out["opportunity_score"], 77)

    def test_negative_internal_valuation_blocks_quality_timing_false_positive(self):
        candidate = row()
        candidate.update({
            "score": 95,
            "moat_score": 95,
            "capital_allocation_intelligence_score": 95,
            "fair_value_upside_pct": -8,
            "margin_of_safety_pct": -20,
            "valuation_signal": "overvalued",
            "valuation_confidence": "high",
        })
        out = MOD.assess(candidate)
        self.assertEqual(out["opportunity_upside_support"], "negative")
        self.assertLessEqual(out["opportunity_score"], 49)
        self.assertTrue(any(cap["reason"] == "Upside fundamental não confirmado" for cap in out["opportunity_caps"]))

    def test_analyst_target_cannot_replace_missing_internal_valuation(self):
        candidate = row()
        candidate.update({
            "fair_value_upside_pct": None,
            "margin_of_safety_pct": None,
            "valuation_signal": "insufficient",
            "valuation_confidence": "low",
            "analyst_price_target_upside_pct": 45,
        })
        out = MOD.assess(candidate)
        self.assertEqual(out["opportunity_upside_support"], "unavailable")
        self.assertLessEqual(out["opportunity_score"], 64)

    def test_upside_support_survives_compact_pipeline_and_stale_rows_clear_it(self):
        post = (ROOT / "scripts" / "postprocess_market.py").read_text(encoding="utf-8")
        shards = (ROOT / "scripts" / "build_market_shards.py").read_text(encoding="utf-8")
        self.assertIn('"opportunity_upside_support"', post)
        self.assertIn('"opportunity_upside_reasons"', post)
        self.assertIn('"opportunity_upside_support"', shards)
        self.assertIn('"opportunity_upside_reasons"', shards)


if __name__ == "__main__":
    unittest.main(verbosity=2)
