import datetime as dt
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "opportunity_forward_validation", ROOT / "scripts" / "opportunity_forward_validation.py"
)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


def observation(score=80, support="strong", label="Prioridade alta", price=100):
    return {
        "price": price,
        "opportunity_score": score,
        "opportunity_score_raw": score + 2,
        "opportunity_label": label,
        "opportunity_upside_support": support,
        "opportunity_timing_score": 70,
        "fair_value_upside_pct": 25,
        "margin_of_safety_pct": 10,
        "sector": "Technology",
        "score_model": "general",
        "risk_gate": "clear",
    }


class OpportunityForwardValidationTests(unittest.TestCase):
    def test_materialised_outcome_is_persistent_and_not_duplicated(self):
        today = dt.date(2026, 8, 30)
        snapshots = [{"date": "2026-08-02", "observations": {"AAA": observation()}}]
        rows = {"AAA": {"current_price": 112}}
        outcomes = []
        self.assertEqual(MOD.materialise_outcomes(today, snapshots, rows, outcomes), 1)
        self.assertEqual(MOD.materialise_outcomes(today, snapshots, rows, outcomes), 0)
        self.assertAlmostEqual(outcomes[0]["return_pct"], 12.0)
        self.assertEqual(outcomes[0]["opportunity_upside_support"], "strong")

    def test_late_horizon_is_not_backfilled(self):
        today = dt.date(2026, 8, 30)
        snapshots = [{"date": "2026-07-01", "observations": {"AAA": observation()}}]
        outcomes = []
        MOD.materialise_outcomes(today, snapshots, {"AAA": {"current_price": 130}}, outcomes)
        self.assertEqual(outcomes, [])

    def test_upside_support_breakdown_uses_frozen_cohort_evidence(self):
        rows = []
        for i in range(16):
            rows.append({
                "cohort_date": "2026-08-02",
                "ticker": f"S{i}",
                "opportunity_score": 80 - i,
                "return_pct": 8 if i < 8 else -2,
                "opportunity_upside_support": "strong" if i < 8 else "weak",
                "opportunity_label": "Prioridade alta" if i < 8 else "Acompanhar",
                "sector": "Technology",
            })
        pack = MOD.summarize_horizon(rows, expected_matured_cohorts=1)
        self.assertGreater(pack["by_upside_support"]["strong"]["median_return_pct"], pack["by_upside_support"]["weak"]["median_return_pct"])
        self.assertGreater(pack["rank_information_coefficient"], 0)

    def test_evidence_policy_never_auto_tunes_production(self):
        mature = {"cohort_count": 8}
        result = MOD.evidence_policy({"28": mature, "84": mature, "168": {}})
        self.assertEqual(result["status"], "review_allowed")
        self.assertTrue(result["production_rules_frozen"])
        self.assertIn("never auto-tuned", result["rule"])

    def test_single_horizon_keeps_observe_only(self):
        result = MOD.evidence_policy({"28": {"cohort_count": 8}, "84": {}, "168": {}})
        self.assertEqual(result["status"], "observe_only")
        self.assertTrue(result["production_rules_frozen"])

    def test_rotation_context_is_frozen_and_reported(self):
        row = {
            "current_price": 100,
            "opportunity_score": 82,
            "opportunity_eligible": True,
            "opportunity_label": "Prioridade alta",
            "opportunity_upside_support": "strong",
            "opportunity_rotation_theme": "Semicondutores",
            "opportunity_rotation_signal": "strong_inflow",
            "opportunity_rotation_breadth_pct": 72,
            "opportunity_rotation_return_5d_pct": 3.2,
            "opportunity_rotation_etf_confirmed": True,
        }
        obs = MOD.make_observation(row)
        self.assertEqual(obs["opportunity_rotation_signal"], "strong_inflow")
        self.assertEqual(obs["opportunity_rotation_theme"], "Semicondutores")
        rows = [{
            "cohort_date": "2026-08-02", "ticker": "AAA", "opportunity_score": 82,
            "return_pct": 5, "opportunity_rotation_signal": "strong_inflow",
            "opportunity_label": "Prioridade alta", "opportunity_upside_support": "strong",
            "sector": "Technology",
        }]
        pack = MOD.summarize_horizon(rows, expected_matured_cohorts=1)
        self.assertIn("strong_inflow", pack["by_rotation_signal"])


    def test_market_regime_context_is_frozen_and_reported(self):
        row = {
            "current_price": 100,
            "opportunity_score": 79,
            "opportunity_eligible": True,
            "opportunity_label": "Oportunidade forte",
            "opportunity_upside_support": "strong",
            "opportunity_market_regime": "adverse",
            "opportunity_market_regime_source": "broad_benchmarks",
            "opportunity_market_breadth_20d_pct": 33,
            "opportunity_market_return_5d_pct": -2.5,
            "opportunity_market_return_20d_pct": -5.5,
            "opportunity_market_regime_evidence_count": 6,
        }
        obs = MOD.make_observation(row)
        self.assertEqual(obs["opportunity_market_regime"], "adverse")
        self.assertEqual(obs["opportunity_market_regime_source"], "broad_benchmarks")
        self.assertEqual(obs["opportunity_market_breadth_20d_pct"], 33)
        rows = [{
            "cohort_date": "2026-08-02", "ticker": "AAA", "opportunity_score": 69,
            "return_pct": 2, "opportunity_market_regime": "adverse",
            "opportunity_label": "Oportunidade forte", "opportunity_upside_support": "strong",
            "sector": "Technology",
        }]
        pack = MOD.summarize_horizon(rows, expected_matured_cohorts=1)
        self.assertIn("adverse", pack["by_market_regime"])



    def test_binary_event_risk_is_frozen_and_reported(self):
        row = {
            "current_price": 100,
            "opportunity_score": 59,
            "opportunity_eligible": True,
            "opportunity_label": "Interessante",
            "opportunity_upside_support": "strong",
            "opportunity_event_risk": "high_risk_imminent",
            "opportunity_event_risk_days": 5,
            "opportunity_event_risk_date": "2026-09-30",
            "opportunity_event_risk_source": "capital_structure",
        }
        obs = MOD.make_observation(row)
        self.assertEqual(obs["opportunity_event_risk"], "high_risk_imminent")
        self.assertEqual(obs["opportunity_event_risk_days"], 5)
        self.assertEqual(obs["opportunity_event_risk_source"], "capital_structure")
        rows = [{
            "cohort_date": "2026-08-02", "ticker": "AAA", "opportunity_score": 59,
            "return_pct": -4, "opportunity_event_risk": "high_risk_imminent",
            "opportunity_label": "Interessante", "opportunity_upside_support": "strong",
            "sector": "Technology",
        }]
        pack = MOD.summarize_horizon(rows, expected_matured_cohorts=1)
        self.assertIn("high_risk_imminent", pack["by_event_risk"])



    def test_revision_freshness_is_frozen_and_reported(self):
        row = {
            "current_price": 100,
            "opportunity_score": 77,
            "opportunity_eligible": True,
            "opportunity_label": "Oportunidade forte",
            "opportunity_upside_support": "moderate",
            "opportunity_revision_evidence": "stale",
            "opportunity_revision_evidence_age_days": 10,
            "opportunity_revision_evidence_coverage_pct": 80,
            "opportunity_revision_evidence_confidence": "high",
            "opportunity_revision_evidence_refresh_state": "cached_rotation",
        }
        obs = MOD.make_observation(row)
        self.assertEqual(obs["opportunity_revision_evidence"], "stale")
        self.assertEqual(obs["opportunity_revision_evidence_age_days"], 10)
        rows = [{
            "cohort_date": "2026-08-02", "ticker": "AAA", "opportunity_score": 77,
            "return_pct": 1, "opportunity_revision_evidence": "stale",
            "opportunity_label": "Oportunidade forte", "opportunity_upside_support": "moderate",
            "sector": "Technology",
        }]
        pack = MOD.summarize_horizon(rows, expected_matured_cohorts=1)
        self.assertIn("stale", pack["by_revision_evidence"])




if __name__ == "__main__":
    unittest.main(verbosity=2)
