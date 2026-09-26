import datetime as dt
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "score_forward_validation", ROOT / "scripts" / "score_forward_validation.py"
)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


class ScoreForwardValidationPersistenceTests(unittest.TestCase):
    def test_materialised_outcome_is_not_duplicated(self):
        today = dt.date(2026, 8, 30)
        snapshots = [{
            "date": "2026-08-02",
            "observations": {
                "AAA": {
                    "price": 100,
                    "score": 80,
                    "quality_pct": 90,
                    "sector": "Technology",
                    "score_model": "general",
                    "confidence_score": 75,
                    "risk_gate": "clear",
                }
            },
        }]
        rows = {"AAA": {"current_price": 110}}
        outcomes = []
        self.assertEqual(MOD.materialise_outcomes(today, snapshots, rows, outcomes), 1)
        self.assertEqual(len(outcomes), 1)
        self.assertAlmostEqual(outcomes[0]["return_pct"], 10.0)
        self.assertEqual(outcomes[0]["horizon_days"], 28)
        self.assertEqual(MOD.materialise_outcomes(today, snapshots, rows, outcomes), 0)
        self.assertEqual(len(outcomes), 1)

    def test_late_horizon_is_not_backfilled_with_wrong_return(self):
        today = dt.date(2026, 8, 30)
        snapshots = [{
            # 60 days old: too late for the 28-day window and not yet mature
            # for 84 days. It must not be assigned to either horizon.
            "date": "2026-07-01",
            "observations": {"AAA": {"price": 100, "score": 80}},
        }]
        outcomes = []
        MOD.materialise_outcomes(today, snapshots, {"AAA": {"current_price": 130}}, outcomes)
        self.assertEqual(outcomes, [])

    def test_status_depends_on_matured_cohorts_not_pooled_n(self):
        rows = []
        for i in range(120):
            rows.append({
                "cohort_date": "2026-08-02",
                "ticker": f"T{i}",
                "score": 30 + i / 2,
                "return_pct": -5 + i / 20,
                "score_model": "general",
                "sector": "Technology",
            })
        summary = MOD.summarize_horizon(rows, expected_matured_cohorts=1)
        self.assertEqual(summary["n"], 120)
        self.assertEqual(summary["cohort_count"], 1)
        self.assertEqual(summary["status"], "collecting_evidence")

    def test_multiple_cohorts_unlock_stronger_status(self):
        rows = []
        for cohort in range(8):
            date = (dt.date(2026, 1, 1) + dt.timedelta(days=7 * cohort)).isoformat()
            for i in range(30):
                rows.append({
                    "cohort_date": date,
                    "ticker": f"T{cohort}_{i}",
                    "score": 40 + i,
                    "return_pct": -3 + i / 5,
                    "score_model": "general",
                    "sector": "Technology",
                })
        summary = MOD.summarize_horizon(rows, expected_matured_cohorts=8)
        self.assertEqual(summary["cohort_count"], 8)
        self.assertEqual(summary["status"], "multiple_cohorts_available")
        self.assertGreater(summary["median_cohort_rank_ic"], 0)
        self.assertGreater(summary["median_cohort_top_minus_bottom_pct"], 0)

    def test_robust_quintile_spreads_expose_outlier_distortion(self):
        rows = []
        for i in range(100):
            score = 100 - i
            realised = 5.0 if i < 20 else (1.0 if i >= 80 else 2.0)
            rows.append({
                "cohort_date": "2026-08-02",
                "ticker": f"T{i}",
                "score": score,
                "return_pct": realised,
                "score_model": "general",
                "sector": "Technology",
            })
        # One extreme top-quintile winner should move the raw mean materially,
        # while median and winsorized diagnostics remain representative.
        rows[0]["return_pct"] = 1000.0
        pack = MOD.metric_pack(rows)
        self.assertGreater(pack["top_minus_bottom_pct"], 40)
        self.assertEqual(pack["median_top_minus_bottom_pct"], 4.0)
        self.assertEqual(pack["winsorized_top_minus_bottom_pct"], 4.0)

    def test_winsorized_mean_does_not_mutate_observations(self):
        values = [1000.0] + [5.0] * 19
        before = list(values)
        result = MOD.winsorized_mean(values)
        self.assertEqual(values, before)
        self.assertEqual(result, 5.0)

    def test_maturity_dates_expose_first_and_next_checkpoint(self):
        today = dt.date(2026, 8, 30)
        snapshots = [{"date": "2026-08-27", "observations": {}}, {"date": "2026-09-03", "observations": {}}]
        first, pending = MOD.maturity_dates(today, snapshots, 28)
        self.assertEqual(first, dt.date(2026, 9, 24))
        self.assertEqual(pending, dt.date(2026, 9, 24))

    def test_factor_diagnostics_are_exposed(self):
        rows = []
        for i in range(30):
            rows.append({
                "cohort_date": "2026-08-02",
                "ticker": f"T{i}",
                "score": i,
                "quality_pct": i,
                "return_pct": i * 0.5,
                "score_model": "general",
                "sector": "Technology",
            })
        summary = MOD.summarize_horizon(rows, expected_matured_cohorts=1)
        self.assertIn("quality_pct", summary["factor_rank_information_coefficient"])
        self.assertGreater(summary["factor_rank_information_coefficient"]["quality_pct"], 0)


    def test_score_v2_readiness_stays_frozen_without_two_mature_horizons(self):
        strong = {
            "cohort_count": 8,
            "cohort_capture_pct": 100,
            "median_cohort_rank_ic": 0.08,
            "median_cohort_top_minus_bottom_pct": 4.0,
            "peer_shadow_comparison": {
                "cohort_count": 8,
                "median_production_cohort_rank_ic": 0.08,
                "median_peer_shadow_cohort_rank_ic": 0.12,
                "median_production_cohort_top_minus_bottom_pct": 4.0,
                "median_peer_shadow_cohort_top_minus_bottom_pct": 5.0,
            },
        }
        result = MOD.score_v2_readiness({"28": strong, "84": {}, "168": {}})
        self.assertEqual(result["status"], "production_change_deferred")
        self.assertTrue(result["production_weights_frozen"])
        self.assertEqual(result["qualified_horizons"], [28])

    def test_score_v2_readiness_allows_review_but_not_deployment(self):
        def strong():
            return {
                "cohort_count": 8,
                "cohort_capture_pct": 90,
                "median_cohort_rank_ic": 0.06,
                "median_cohort_top_minus_bottom_pct": 3.0,
                "peer_shadow_comparison": {
                    "cohort_count": 8,
                    "median_production_cohort_rank_ic": 0.06,
                    "median_peer_shadow_cohort_rank_ic": 0.10,
                    "median_production_cohort_top_minus_bottom_pct": 3.0,
                    "median_peer_shadow_cohort_top_minus_bottom_pct": 3.5,
                },
            }
        result = MOD.score_v2_readiness({"28": strong(), "84": strong(), "168": {}})
        self.assertEqual(result["status"], "candidate_review_allowed")
        self.assertFalse(result["production_weights_frozen"])
        self.assertEqual(result["qualified_horizons"], [28, 84])
        self.assertIn("permits review, not deployment", result["rule"])

    def test_score_v2_readiness_rejects_shadow_improvement_with_worse_spread(self):
        pack = {
            "cohort_count": 8,
            "cohort_capture_pct": 100,
            "median_cohort_rank_ic": 0.08,
            "median_cohort_top_minus_bottom_pct": 4.0,
            "peer_shadow_comparison": {
                "cohort_count": 8,
                "median_production_cohort_rank_ic": 0.08,
                "median_peer_shadow_cohort_rank_ic": 0.14,
                "median_production_cohort_top_minus_bottom_pct": 4.0,
                "median_peer_shadow_cohort_top_minus_bottom_pct": 2.0,
            },
        }
        result = MOD.score_v2_readiness({"28": pack, "84": pack, "168": {}})
        self.assertTrue(result["production_weights_frozen"])
        reasons = result["blockers"][0]["reasons"]
        self.assertIn("shadow_spread_worse_or_unavailable", reasons)


if __name__ == "__main__":
    unittest.main(verbosity=2)
