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

    def test_reverse_split_normalizes_forward_return_and_preserves_raw_return(self):
        adjusted = MOD.split_adjusted_return(
            "NFE",
            "2026-09-03",
            "2026-10-01",
            0.2761,
            6.57,
        )
        self.assertTrue(adjusted["corporate_action_adjusted"])
        self.assertEqual(adjusted["split_adjustment_factor"], 50.0)
        self.assertGreater(adjusted["raw_return_pct"], 2200)
        self.assertAlmostEqual(adjusted["return_pct"], -52.4085, places=3)

    def test_persisted_split_outcomes_are_repaired_idempotently(self):
        outcomes = [{
            "cohort_date": "2026-08-27",
            "evaluated_date": "2026-09-24",
            "horizon_days": 28,
            "ticker": "GOSS",
            "start_price": 0.1739,
            "end_price": 10.93,
            "return_pct": 6185.221392,
        }]
        self.assertEqual(MOD.repair_persisted_split_outcomes(outcomes), 1)
        first = dict(outcomes[0])
        self.assertTrue(first["corporate_action_adjusted"])
        self.assertEqual(first["split_adjustment_factor"], 80.0)
        self.assertGreater(first["raw_return_pct"], 6000)
        self.assertLess(abs(first["return_pct"]), 30)
        self.assertEqual(MOD.repair_persisted_split_outcomes(outcomes), 0)
        self.assertEqual(outcomes[0], first)

    def test_spinoff_total_return_includes_distributed_child_value(self):
        adjusted = MOD.corporate_action_adjusted_return(
            "CTVA",
            "2026-09-03",
            "2026-10-01",
            89.97,
            11.92,
            end_rows={"VYLR": {"current_price": 68.26}},
        )
        self.assertTrue(adjusted["corporate_action_adjusted"])
        self.assertFalse(adjusted["corporate_action_unresolved"])
        self.assertTrue(adjusted["validation_eligible"])
        self.assertEqual(adjusted["distribution_value_per_parent"], 68.26)
        self.assertLess(abs(adjusted["return_pct"]), 15)
        self.assertLess(adjusted["raw_return_pct"], -80)

    def test_unresolved_spinoff_is_retained_but_not_validation_eligible(self):
        adjusted = MOD.corporate_action_adjusted_return(
            "CTVA",
            "2026-09-03",
            "2026-10-01",
            89.97,
            11.92,
            end_rows={},
        )
        self.assertTrue(adjusted["corporate_action_unresolved"])
        self.assertFalse(adjusted["validation_eligible"])
        self.assertEqual(adjusted["unresolved_distributions"], ["VYLR"])
        self.assertLess(adjusted["return_pct"], -80)

    def test_snapshot_keeps_distribution_reference_price_even_without_score(self):
        snap = MOD.make_snapshot(
            dt.date(2026, 10, 1),
            {"CTVA": {"current_price": 11.92, "score": 50}},
            {},
            {"VYLR": {"current_price": 68.26}},
        )
        self.assertEqual(snap["corporate_action_reference_prices"]["VYLR"], 68.26)

    def test_large_unsplit_return_is_not_clipped(self):
        adjusted = MOD.split_adjusted_return(
            "FEAM",
            "2026-09-03",
            "2026-10-01",
            1.56,
            3.88,
        )
        self.assertFalse(adjusted["corporate_action_adjusted"])
        self.assertEqual(adjusted["split_adjustment_factor"], 1.0)
        self.assertAlmostEqual(adjusted["return_pct"], 148.717949, places=5)

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

    def test_report_freshness_rejects_expired_or_wrong_generator_reports(self):
        now = dt.datetime(2026, 10, 4, 16, 0, tzinfo=dt.timezone.utc)
        current = {
            "schema_version": MOD.REPORT_SCHEMA_VERSION,
            "generator_version": MOD.REPORT_GENERATOR_VERSION,
            "freshness": {"valid_through": "2026-10-05T04:00:00+00:00"},
        }
        self.assertTrue(MOD.evaluate_report_freshness(current, now)["is_current"])

        expired = dict(current)
        expired["freshness"] = {"valid_through": "2026-10-04T15:00:00+00:00"}
        self.assertEqual(
            MOD.evaluate_report_freshness(expired, now)["reasons"],
            ["report_expired"],
        )

        wrong_generator = dict(current)
        wrong_generator["generator_version"] = "legacy-validator"
        self.assertIn(
            "generator_version_mismatch",
            MOD.evaluate_report_freshness(wrong_generator, now)["reasons"],
        )

    def test_score_model_breakdown_is_cohort_aware_not_just_pooled(self):
        rows = []
        for cohort, date in enumerate(("2026-08-01", "2026-08-08")):
            for i in range(40):
                score = i
                realised = i if cohort == 0 else (40 - i)
                rows.append({
                    "cohort_date": date,
                    "ticker": f"T{cohort}_{i}",
                    "score": score,
                    "return_pct": realised,
                    "score_model": "bank",
                    "sector": "Financial Services",
                })
        summary = MOD.summarize_horizon(rows, expected_matured_cohorts=2)
        bank = summary["by_score_model"]["bank"]
        self.assertEqual(bank["cohort_count"], 2)
        self.assertEqual(bank["status"], "collecting_evidence")
        self.assertEqual(len(bank["cohorts"]), 2)
        self.assertEqual(bank["positive_ic_cohorts"], 1)
        self.assertAlmostEqual(bank["median_cohort_rank_ic"], 0.0, places=4)

    def test_model_stability_diagnostics_are_descriptive_and_cohort_based(self):
        rows = []
        cohort_specs = [
            ("2026-08-01", 0.10, 4.0),
            ("2026-08-08", 0.30, 8.0),
            ("2026-08-15", -0.10, -2.0),
            ("2026-08-22", 0.20, 6.0),
        ]
        for cohort_date, ic_direction, spread_direction in cohort_specs:
            for i in range(40):
                score = i
                if ic_direction >= 0:
                    realised = i
                else:
                    realised = 40 - i
                # Use a deterministic top/bottom separation sign without relying
                # on an exact target magnitude.
                realised += (spread_direction / 100.0) * i
                rows.append({
                    "cohort_date": cohort_date,
                    "ticker": f"{cohort_date}_{i}",
                    "score": score,
                    "return_pct": realised,
                    "score_model": "general",
                    "sector": "Technology",
                })
        summary = MOD.summarize_horizon(rows, expected_matured_cohorts=4)
        stability = summary["by_score_model"]["general"]["stability"]
        self.assertEqual(stability["cohorts_with_both_metrics"], 4)
        self.assertGreaterEqual(stability["joint_positive_cohorts"], 3)
        self.assertIsNotNone(stability["rank_ic"]["range"])
        self.assertIsNotNone(stability["rank_ic"]["median_absolute_deviation"])
        self.assertIsNotNone(stability["robust_spread_pct"]["range"])
        self.assertIn("Descriptive only", stability["interpretation"])

    def test_model_composition_stability_tracks_adjacent_universe_overlap(self):
        rows = []
        first = [f"T{i}" for i in range(40)]
        second = [f"T{i}" for i in range(10, 50)]
        third = [f"T{i}" for i in range(20, 60)]
        for date, tickers in [
            ("2026-08-01", first),
            ("2026-08-08", second),
            ("2026-08-15", third),
        ]:
            for i, ticker in enumerate(tickers):
                rows.append({
                    "cohort_date": date,
                    "ticker": ticker,
                    "score": i,
                    "return_pct": i,
                    "score_model": "general",
                    "sector": "Technology",
                })
        diag = MOD.cohort_composition_diagnostics(rows)
        self.assertEqual(diag["cohort_count"], 3)
        self.assertEqual(diag["adjacent_pair_count"], 2)
        self.assertEqual(diag["cohort_size"]["min"], 40)
        self.assertEqual(diag["cohort_size"]["max"], 40)
        self.assertEqual(diag["median_adjacent_overlap_n"], 30.0)
        self.assertEqual(diag["median_adjacent_jaccard_pct"], 60.0)
        self.assertEqual(diag["min_adjacent_jaccard_pct"], 60.0)
        self.assertIn("Descriptive only", diag["interpretation"])
        summary = MOD.summarize_horizon(rows, expected_matured_cohorts=3)
        integrated = summary["by_score_model"]["general"]["composition_stability"]
        self.assertEqual(integrated["median_adjacent_jaccard_pct"], 60.0)
        self.assertEqual(integrated["adjacent_pair_count"], 2)


    def test_model_status_requires_multiple_cohorts_even_with_large_pooled_n(self):
        rows = [
            {
                "cohort_date": "2026-08-01",
                "ticker": f"B{i}",
                "score": i,
                "return_pct": i,
                "score_model": "biotech",
                "sector": "Healthcare",
            }
            for i in range(200)
        ]
        summary = MOD.summarize_horizon(rows, expected_matured_cohorts=1)
        biotech = summary["by_score_model"]["biotech"]
        self.assertEqual(biotech["n"], 200)
        self.assertEqual(biotech["cohort_count"], 1)
        self.assertEqual(biotech["status"], "collecting_evidence")

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
            "median_cohort_robust_spread_pct": 4.0,
            "peer_shadow_comparison": {
                "cohort_count": 8,
                "median_production_cohort_rank_ic": 0.08,
                "median_peer_shadow_cohort_rank_ic": 0.12,
                "median_production_cohort_top_minus_bottom_pct": 4.0,
                "median_peer_shadow_cohort_top_minus_bottom_pct": 5.0,
                "median_production_cohort_robust_spread_pct": 4.0,
                "median_peer_shadow_cohort_robust_spread_pct": 5.0,
            },
        }
        result = MOD.score_v2_readiness(
            {"28": strong, "84": {}, "168": {}},
            candidate_role="candidate",
            candidate_id="test-v2",
        )
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
                "median_cohort_robust_spread_pct": 3.0,
                "peer_shadow_comparison": {
                    "cohort_count": 8,
                    "median_production_cohort_rank_ic": 0.06,
                    "median_peer_shadow_cohort_rank_ic": 0.10,
                    "median_production_cohort_top_minus_bottom_pct": 3.0,
                    "median_peer_shadow_cohort_top_minus_bottom_pct": 3.5,
                    "median_production_cohort_robust_spread_pct": 3.0,
                    "median_peer_shadow_cohort_robust_spread_pct": 3.5,
                },
            }
        result = MOD.score_v2_readiness(
            {"28": strong(), "84": strong(), "168": {}},
            candidate_role="candidate",
            candidate_id="test-v2",
        )
        self.assertEqual(result["status"], "candidate_review_allowed")
        self.assertFalse(result["production_weights_frozen"])
        self.assertEqual(result["qualified_horizons"], [28, 84])
        self.assertIn("permits review, not deployment", result["rule"])

    def test_summary_exposes_winsorized_cohort_spread_for_readiness(self):
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
        rows[0]["return_pct"] = 1000.0
        summary = MOD.summarize_horizon(rows, expected_matured_cohorts=1)
        self.assertGreater(summary["median_cohort_top_minus_bottom_pct"], 40)
        self.assertEqual(summary["median_cohort_robust_spread_pct"], 4.0)
        self.assertGreater(
            summary["median_cohort_top_minus_bottom_pct"],
            summary["median_cohort_robust_spread_pct"] * 10,
        )
        self.assertEqual(summary["positive_robust_spread_cohorts"], 1)

    def test_score_v2_readiness_uses_robust_not_raw_spread(self):
        def pack():
            return {
                "cohort_count": 8,
                "cohort_capture_pct": 100,
                "median_cohort_rank_ic": 0.08,
                "median_cohort_top_minus_bottom_pct": -20.0,
                "median_cohort_robust_spread_pct": 4.0,
                "peer_shadow_comparison": {
                    "cohort_count": 8,
                    "median_production_cohort_rank_ic": 0.08,
                    "median_peer_shadow_cohort_rank_ic": 0.12,
                    "median_production_cohort_top_minus_bottom_pct": -20.0,
                    "median_peer_shadow_cohort_top_minus_bottom_pct": -25.0,
                    "median_production_cohort_robust_spread_pct": 4.0,
                    "median_peer_shadow_cohort_robust_spread_pct": 5.0,
                },
            }
        result = MOD.score_v2_readiness(
            {"28": pack(), "84": pack(), "168": {}},
            candidate_role="candidate",
            candidate_id="test-v2",
        )
        self.assertEqual(result["status"], "candidate_review_allowed")
        self.assertEqual(result["qualified_horizons"], [28, 84])

    def test_score_v2_readiness_rejects_production_parity_shadow(self):
        strong = {
            "cohort_count": 8,
            "cohort_capture_pct": 100,
            "median_cohort_rank_ic": 0.08,
            "median_cohort_top_minus_bottom_pct": 4.0,
            "median_cohort_robust_spread_pct": 4.0,
            "peer_shadow_comparison": {
                "cohort_count": 8,
                "median_production_cohort_rank_ic": 0.08,
                "median_peer_shadow_cohort_rank_ic": 0.12,
                "median_production_cohort_top_minus_bottom_pct": 4.0,
                "median_peer_shadow_cohort_top_minus_bottom_pct": 5.0,
                "median_production_cohort_robust_spread_pct": 4.0,
                "median_peer_shadow_cohort_robust_spread_pct": 5.0,
            },
        }
        result = MOD.score_v2_readiness(
            {"28": strong, "84": strong, "168": strong},
            candidate_role="production_parity_reconstruction",
            candidate_id=None,
        )
        self.assertEqual(result["status"], "production_change_deferred")
        self.assertTrue(result["production_weights_frozen"])
        self.assertFalse(result["independent_candidate_active"])
        self.assertEqual(result["qualified_horizons"], [])
        for blocker in result["blockers"]:
            self.assertIn("no_independent_score_candidate", blocker["reasons"])

    def test_score_v2_readiness_rejects_shadow_improvement_with_worse_spread(self):
        pack = {
            "cohort_count": 8,
            "cohort_capture_pct": 100,
            "median_cohort_rank_ic": 0.08,
            "median_cohort_top_minus_bottom_pct": 4.0,
            "median_cohort_robust_spread_pct": 4.0,
            "peer_shadow_comparison": {
                "cohort_count": 8,
                "median_production_cohort_rank_ic": 0.08,
                "median_peer_shadow_cohort_rank_ic": 0.14,
                "median_production_cohort_top_minus_bottom_pct": 4.0,
                "median_peer_shadow_cohort_top_minus_bottom_pct": 2.0,
                "median_production_cohort_robust_spread_pct": 4.0,
                "median_peer_shadow_cohort_robust_spread_pct": 2.0,
            },
        }
        result = MOD.score_v2_readiness(
            {"28": pack, "84": pack, "168": {}},
            candidate_role="candidate",
            candidate_id="test-v2",
        )
        self.assertTrue(result["production_weights_frozen"])
        reasons = result["blockers"][0]["reasons"]
        self.assertIn("shadow_spread_worse_or_unavailable", reasons)


if __name__ == "__main__":
    unittest.main(verbosity=2)
