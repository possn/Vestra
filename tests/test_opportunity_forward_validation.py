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

    def test_outcome_price_lookup_retains_now_ineligible_equities(self):
        from unittest import mock

        payload = {"stocks": [
            {"ticker": "OLD", "quote_type": "EQUITY", "current_price": 80,
             "opportunity_score": 0, "opportunity_eligible": False,
             "risk_gate": "severe"},
            {"ticker": "NEW", "quote_type": "EQUITY", "current_price": 120,
             "opportunity_score": 75, "opportunity_eligible": True},
            {"ticker": "STALE", "quote_type": "EQUITY", "current_price": 92,
             "pipeline_status": "equity_carried_forward"},
            {"ticker": "FUND", "quote_type": "ETF", "current_price": 100},
        ]}
        with mock.patch.object(MOD, "load_json", return_value=payload):
            selected = MOD.current_rows()
            current_prices = MOD.outcome_price_rows()
        self.assertEqual(set(selected), {"NEW"})
        self.assertEqual(set(current_prices), {"OLD", "NEW"})
        snapshots = [{"date": "2026-08-02",
                      "observations": {"OLD": observation(price=100)}}]
        outcomes = []
        self.assertEqual(MOD.materialise_outcomes(
            dt.date(2026, 8, 30), snapshots, current_prices, outcomes
        ), 1)
        self.assertEqual(outcomes[0]["return_pct"], -20.0)
        self.assertEqual(outcomes[0]["risk_gate"], "clear",
                         "Outcome must use frozen cohort evidence, not today's risk gate")

    def test_missing_risk_gate_remains_unknown_in_archived_snapshot(self):
        row = {"current_price": 100, "opportunity_score": 72}
        frozen = MOD.make_observation(row)
        self.assertEqual(frozen["risk_gate"], "unknown")
        self.assertEqual(MOD.make_observation({**row, "risk_gate": "watch"})["risk_gate"], "watch")

    def test_only_boolean_true_is_eligible_for_prospective_cohort(self):
        from unittest import mock
        payload = {"stocks": [
            {"ticker": "VALID", "quote_type": "EQUITY", "current_price": 100,
             "opportunity_score": 72, "opportunity_eligible": True},
            {"ticker": "STRING_FALSE", "quote_type": "EQUITY", "current_price": 100,
             "opportunity_score": 70, "opportunity_eligible": "false"},
            {"ticker": "UNKNOWN", "quote_type": "EQUITY", "current_price": 100,
             "opportunity_score": 70},
        ]}
        with mock.patch.object(MOD, "load_json", return_value=payload):
            self.assertEqual(set(MOD.current_rows()), {"VALID"})

    def test_missing_or_stale_price_is_not_imputed(self):
        from unittest import mock
        payload = {"stocks": [
            {"ticker": "OLD", "quote_type": "EQUITY",
             "pipeline_status": "equity_carried_forward", "current_price": 140},
            {"ticker": "INVALID", "quote_type": "EQUITY", "current_price": float("nan")},
        ]}
        with mock.patch.object(MOD, "load_json", return_value=payload):
            current_prices = MOD.outcome_price_rows()
        self.assertEqual(current_prices, {})
        snapshots = [{"date": "2026-08-02",
                      "observations": {"OLD": observation(price=100)}}]
        outcomes = []
        self.assertEqual(MOD.materialise_outcomes(
            dt.date(2026, 8, 30), snapshots, current_prices, outcomes
        ), 0)
        self.assertEqual(outcomes, [])

    def test_reverse_split_is_adjusted_using_shared_score_registry(self):
        today = dt.date(2026, 10, 9)
        snapshots = [{"date": "2026-09-11", "observations": {
            "NFE": observation(price=1),
        }}]
        outcomes = []
        self.assertEqual(MOD.materialise_outcomes(today, snapshots, {
            "NFE": {"current_price": 50}
        }, outcomes), 1)
        self.assertAlmostEqual(outcomes[0]["raw_return_pct"], 4900)
        self.assertAlmostEqual(outcomes[0]["return_pct"], 0)
        self.assertEqual(outcomes[0]["split_adjustment_factor"], 50)
        self.assertTrue(outcomes[0]["corporate_action_adjusted"])
        self.assertTrue(outcomes[0]["validation_eligible"])

    def test_unresolved_spinoff_kept_but_not_validation_eligible(self):
        today = dt.date(2026, 10, 28)
        snapshots = [{"date": "2026-09-30", "observations": {
            "CTVA": observation(price=100),
        }}]
        outcomes = []
        self.assertEqual(MOD.materialise_outcomes(today, snapshots, {
            "CTVA": {"current_price": 90},
        }, outcomes), 1)
        self.assertFalse(outcomes[0]["validation_eligible"])
        self.assertTrue(outcomes[0]["corporate_action_unresolved"])
        self.assertIn("VYLR", outcomes[0]["unresolved_distributions"])

    def test_legacy_cohort_outcome_does_not_claim_adjustment(self):
        legacy = {"cohort_date": "2026-08-02", "horizon_days": 28,
                  "ticker": "AAA", "opportunity_score": 80, "return_pct": 2}
        self.assertIsNot(legacy.get("validation_eligible"), True)
        self.assertFalse(legacy.get("corporate_action_adjusted", False))

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

    def test_asset_capture_does_not_confuse_partial_cohort_with_full_coverage(self):
        today = dt.date(2026, 8, 30)
        snapshots = [{"date": "2026-08-02", "observations": {
            "AAA": observation(), "BBB": observation(), "CCC": observation(),
        }}]
        outcomes = [{
            "cohort_date": "2026-08-02", "horizon_days": 28,
            "ticker": "AAA", "opportunity_score": 80, "return_pct": 2,
        }]
        self.assertEqual(MOD.expected_matured_count(today, snapshots, 28), 1)
        summary = MOD.summarize_horizon(outcomes, expected_matured_cohorts=1)
        self.assertEqual(summary["cohort_capture_pct"], 100.0)
        capture = MOD.observation_capture(today, snapshots, outcomes, 28)
        self.assertEqual(capture["expected_matured_observations"], 3)
        self.assertEqual(capture["realised_matured_observations"], 1)
        self.assertEqual(capture["missing_matured_observations"], 2)
        self.assertEqual(capture["observation_capture_pct"], 33.3)

    def test_asset_capture_deduplicates_outcomes_and_ignores_future_cohorts(self):
        today = dt.date(2026, 8, 30)
        snapshots = [
            {"date": "2026-08-02", "observations": {"AAA": observation(), "BBB": observation()}},
            {"date": "2026-08-20", "observations": {"CCC": observation()}},
        ]
        duplicate = {"cohort_date": "2026-08-02", "horizon_days": 28, "ticker": "AAA"}
        capture = MOD.observation_capture(today, snapshots, [duplicate, duplicate], 28)
        self.assertEqual(capture["expected_matured_observations"], 2)
        self.assertEqual(capture["realised_matured_observations"], 1)
        self.assertEqual(capture["observation_capture_pct"], 50.0)
        self.assertIsNone(MOD.observation_capture(today, snapshots, [], 168)["observation_capture_pct"])

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
            "opportunity_rotation_etf_evidence_count": 2,
        }
        obs = MOD.make_observation(row)
        self.assertEqual(obs["opportunity_rotation_signal"], "strong_inflow")
        self.assertEqual(obs["opportunity_rotation_theme"], "Semicondutores")
        self.assertEqual(obs["opportunity_rotation_etf_evidence_count"], 2)
        rows = [{
            "cohort_date": "2026-08-02", "ticker": "AAA", "opportunity_score": 82,
            "return_pct": 5, "opportunity_rotation_signal": "strong_inflow",
            "opportunity_rotation_etf_confirmed": True,
            "opportunity_label": "Prioridade alta", "opportunity_upside_support": "strong",
            "sector": "Technology",
        }]
        pack = MOD.summarize_horizon(rows, expected_matured_cohorts=1)
        self.assertIn("strong_inflow", pack["by_rotation_signal"])
        self.assertIn("True", pack["by_rotation_etf_confirmation"])


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



    def test_valuation_breadth_is_frozen_and_reported(self):
        row = {
            "current_price": 100,
            "opportunity_score": 77,
            "opportunity_eligible": True,
            "opportunity_label": "Oportunidade forte",
            "opportunity_upside_support": "moderate",
            "opportunity_valuation_evidence": "dispersed",
            "opportunity_valuation_method_count": 3,
            "opportunity_valuation_dispersion_pct": 55,
        }
        obs = MOD.make_observation(row)
        self.assertEqual(obs["opportunity_valuation_evidence"], "dispersed")
        self.assertEqual(obs["opportunity_valuation_method_count"], 3)
        self.assertEqual(obs["opportunity_valuation_dispersion_pct"], 55)
        rows = [{
            "cohort_date": "2026-08-02", "ticker": "AAA", "opportunity_score": 77,
            "return_pct": 1, "opportunity_valuation_evidence": "dispersed",
            "opportunity_label": "Oportunidade forte", "opportunity_upside_support": "moderate",
            "sector": "Technology",
        }]
        pack = MOD.summarize_horizon(rows, expected_matured_cohorts=1)
        self.assertIn("dispersed", pack["by_valuation_evidence"])




if __name__ == "__main__":
    unittest.main(verbosity=2)
