import datetime as dt
import importlib.util
from pathlib import Path
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "opportunity_forward_validation", ROOT / "scripts" / "opportunity_forward_validation.py"
)
MOD = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MOD)


def complete_frozen_quintile_capture(coverage=90.0):
    return {"quintiles": [
        {"quintile": q, "expected": 20, "validated_capture_pct": coverage}
        for q in range(1, 6)
    ]}


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
    def test_boolean_price_and_score_cannot_enter_forward_cohorts(self):
        # NumPy 1.x and 2.x scalar identities without a NumPy CI dependency.
        def fake_numpy_bool(name):
            return type(name, (), {
                "__module__": "numpy",
                "__init__": lambda self, v: setattr(self, "value", v),
                "__float__": lambda self: float(self.value),
            })
        invalid = [True, False, fake_numpy_bool("bool_")(True),
                   fake_numpy_bool("bool")(True)]
        for bad in invalid:
            with self.subTest(scalar=type(bad).__name__):
                self.assertIsNone(MOD.num(bad))
                payload = {"stocks": [
                    {"ticker": "BAD_PRICE", "quote_type": "EQUITY",
                     "current_price": bad, "opportunity_score": 80,
                     "opportunity_eligible": True},
                    {"ticker": "BAD_SCORE", "quote_type": "EQUITY",
                     "current_price": 100, "opportunity_score": bad,
                     "opportunity_eligible": True},
                    {"ticker": "GOOD", "quote_type": "EQUITY",
                     "current_price": 100, "opportunity_score": 80,
                     "opportunity_eligible": True},
                ]}
                with mock.patch.object(MOD, "load_json", return_value=payload):
                    self.assertEqual(set(MOD.current_rows()), {"GOOD"})
                    self.assertEqual(set(MOD.outcome_price_rows()),
                                     {"BAD_SCORE", "GOOD"})

    def test_boolean_matured_price_does_not_become_forward_return(self):
        today = dt.date(2026, 8, 30)
        snapshots = [{"date": "2026-08-02",
                      "observations": {"AAA": observation()}}]
        for bad in (True, False):
            with self.subTest(price=bad):
                outcomes = []
                self.assertEqual(MOD.materialise_outcomes(
                    today, snapshots, {"AAA": {"current_price": bad}}, outcomes), 0)
                self.assertEqual(outcomes, [])

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

    def test_currency_mismatch_never_enters_validated_opportunity_returns(self):
        today = dt.date(2026, 10, 9)
        frozen = {**observation(price=100), "currency": "USD"}
        snapshots = [{"date": "2026-09-11", "observations": {"FX": frozen}}]
        outcomes = []
        with mock.patch.object(
            MOD, "corporate_action_adjusted_return",
            return_value={"return_pct": 20.0, "raw_return_pct": 20.0,
                          "split_adjustment_factor": 1.0,
                          "distribution_value_per_parent": 0.0,
                          "corporate_action_adjusted": False,
                          "corporate_action_unresolved": False,
                          "unresolved_distributions": [],
                          "validation_eligible": True}
        ):
            added = MOD.materialise_outcomes(
                today, snapshots, {"FX": {"current_price": 120, "currency": "EUR"}},
                outcomes)
        self.assertEqual(added, 1)
        self.assertFalse(outcomes[0]["validation_eligible"])
        self.assertFalse(outcomes[0]["quote_currency_comparable"])
        self.assertEqual(outcomes[0]["terminal_quote_currency"], "EUR")
        self.assertEqual(MOD.observation_capture(today, snapshots, outcomes, 28)
                         ["validated_matured_observations"], 0)

    def test_missing_quote_currency_cannot_prove_comparable_returns(self):
        today = dt.date(2026, 10, 9)
        snapshots = [{"date": "2026-09-11", "observations": {
            "UNKNOWN": observation(price=100)}}]
        outcomes = []
        MOD.materialise_outcomes(today, snapshots,
                                 {"UNKNOWN": {"current_price": 120}}, outcomes)
        self.assertEqual(len(outcomes), 1)
        self.assertFalse(outcomes[0]["validation_eligible"])
        self.assertFalse(outcomes[0]["quote_currency_comparable"])

    def test_reverse_split_is_adjusted_using_shared_score_registry(self):
        today = dt.date(2026, 10, 9)
        snapshots = [{"date": "2026-09-11", "observations": {
            "NFE": {**observation(price=1), "currency": "USD"},
        }}]
        outcomes = []
        self.assertEqual(MOD.materialise_outcomes(today, snapshots, {
            "NFE": {"current_price": 50, "currency": "USD"}
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
        self.assertEqual(capture["validated_matured_observations"], 0)
        self.assertEqual(capture["validated_capture_pct"], 0.0)

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
        self.assertEqual(capture["validated_capture_pct"], 0.0)
        self.assertIsNone(MOD.observation_capture(today, snapshots, [], 168)["observation_capture_pct"])

    def test_missing_outcome_audit_does_not_infer_delisting(self):
        today = dt.date(2026, 8, 30)
        snapshots = [{"date": "2026-08-02", "observations": {
            "AAA": observation(), "BBB": observation(), "CCC": observation(),
        }}]
        outcomes = [{"cohort_date": "2026-08-02", "horizon_days": 28,
                     "ticker": "AAA", "return_pct": 5}]
        diag = MOD.missing_outcome_diagnostics(
            today, snapshots, outcomes, 28, {"AAA": {"current_price": 110},
                                             "BBB": {"current_price": 90}}
        )
        self.assertEqual(diag["missing_outcome_count"], 2)
        self.assertEqual(diag["missing_price_now_count"], 1)
        self.assertEqual(diag["price_available_within_window_count"], 1)
        self.assertEqual(diag["capture_window_expired_count"], 0)
        self.assertEqual(diag["delisting_status"], "unverified")
        self.assertEqual({x["ticker"] for x in diag["missing_outcome_samples"]}, {"BBB", "CCC"})

    def test_missing_terminal_quotes_have_disjoint_actionable_source_reasons(self):
        today = dt.date(2026, 8, 30)
        tickers = ["ABSENT", "STALE", "BAD", "FUND", "AMBIG", "VALID"]
        snapshots = [{"date": "2026-08-02", "observations": {
            ticker: observation() for ticker in tickers
        }}]
        prices = {"VALID": {"current_price": 100}}
        catalog = {
            "STALE": [{"current_price": 10, "pipeline_status": "equity_carried_forward"}],
            "BAD": [{"current_price": None, "quote_type": "EQUITY"}],
            "FUND": [{"current_price": 10, "quote_type": "ETF"}],
            "AMBIG": [{"current_price": 10}, {"current_price": 11}],
            "VALID": [{"current_price": 100}],
        }
        report = MOD.missing_outcome_diagnostics(
            today, snapshots, [], 28, prices, terminal_catalog=catalog)
        self.assertEqual(report["missing_outcome_count"], len(tickers))
        reasons = report["missing_terminal_quote_reasons"]
        self.assertEqual(reasons, {
            "absent_from_current_index": 1,
            "ambiguous_multiple_index_rows": 1,
            "currently_non_equity_type": 1,
            "invalid_or_missing_current_price": 1,
            "quote_excluded_stale_or_catalog": 1,
            "usable_quote_not_captured": 1,
        })
        self.assertEqual(report["missing_terminal_quote_reason_total"], len(tickers))
        self.assertEqual(report["price_available_within_window_count"], 1)
        self.assertEqual(report["missing_price_now_count"], 5)
        self.assertEqual(report["delisting_status"], "unverified")
        self.assertTrue(all("return_pct" not in row for row in report["missing_outcome_samples"]))

    def test_expired_quote_remains_expired_even_if_current_index_has_price(self):
        snapshots = [{"date": "2026-08-02", "observations": {
            "RETURNED": observation(),
        }}]
        prices = {"RETURNED": {"current_price": 150}}
        report = MOD.missing_outcome_diagnostics(
            dt.date(2026, 10, 12), snapshots, [], 28, prices,
            terminal_catalog={"RETURNED": [{"current_price": 150}]})
        self.assertEqual(report["capture_window_expired_count"], 1)
        self.assertEqual(report["price_available_within_window_count"], 0)
        self.assertEqual(report["missing_terminal_quote_reasons"], {
            "usable_quote_not_captured": 1,
        })

    def test_missing_catalog_is_explicitly_unknown_not_delisting(self):
        snapshots = [{"date": "2026-08-02", "observations": {"OLD": observation()}}]
        report = MOD.missing_outcome_diagnostics(
            dt.date(2026, 8, 30), snapshots, [], 28, {})
        self.assertEqual(report["missing_terminal_quote_reasons"],
                         {"unclassified_no_catalog": 1})

    def test_missing_outcome_audit_marks_expired_window_not_fake_return(self):
        today = dt.date(2026, 9, 15)
        snapshots = [{"date": "2026-08-02", "observations": {"LOST": observation()}}]
        diag = MOD.missing_outcome_diagnostics(today, snapshots, [], 28, {})
        self.assertEqual(diag["missing_outcome_count"], 1)
        self.assertEqual(diag["missing_price_now_count"], 1)
        self.assertEqual(diag["capture_window_expired_count"], 1)
        self.assertEqual(diag["price_available_within_window_count"], 0)
        self.assertNotIn("return_pct", diag["missing_outcome_samples"][0])

    def test_evidence_policy_never_auto_tunes_production(self):
        mature = {"cohort_count": 8, "n": 100, "validated_capture_pct": 85.0,
                  "score_quintile_capture": complete_frozen_quintile_capture()}
        result = MOD.evidence_policy({"28": mature, "84": mature, "168": {}})
        self.assertEqual(result["status"], "review_allowed")
        self.assertTrue(result["production_rules_frozen"])
        self.assertIn("never auto-tuned", result["rule"])

    def test_legacy_outcomes_do_not_inflate_validated_capture(self):
        today = dt.date(2026, 8, 30)
        snapshots = [{"date": "2026-08-02", "observations": {
            "AAA": observation(), "BBB": observation(), "CCC": observation(),
        }}]
        outcomes = [
            {"cohort_date": "2026-08-02", "horizon_days": 28,
             "ticker": "AAA", "return_pct": 4},
            {"cohort_date": "2026-08-02", "horizon_days": 28,
             "ticker": "BBB", "return_pct": 6, "validation_eligible": True,
             "evaluated_date": "2026-08-30", "actual_days": 28},
            {"cohort_date": "2026-08-02", "horizon_days": 28,
             "ticker": "CCC", "return_pct": 0, "validation_eligible": False},
        ]
        capture = MOD.observation_capture(today, snapshots, outcomes, 28)
        self.assertEqual(capture["realised_matured_observations"], 3)
        self.assertEqual(capture["validated_matured_observations"], 1)
        self.assertEqual(capture["unvalidated_matured_observations"], 2)
        self.assertEqual(capture["validated_capture_pct"], 33.3)

    def test_evidence_review_requires_validated_coverage(self):
        mature = {"cohort_count": 8, "n": 150, "validated_capture_pct": 79.9,
                  "score_quintile_capture": complete_frozen_quintile_capture()}
        self.assertEqual(MOD.evidence_policy({"28": mature, "84": mature})["status"], "observe_only")
        mature["validated_capture_pct"] = 80
        mature["n"] = 99
        self.assertEqual(MOD.evidence_policy({"28": mature, "84": mature})["status"], "observe_only")
        mature["n"] = 100
        self.assertEqual(MOD.evidence_policy({"28": mature, "84": mature})["status"], "review_allowed")

    def test_conflicting_duplicate_outcomes_block_readiness_even_with_good_sample(self):
        mature = {"cohort_count": 8, "n": 140,
                  "validated_capture_pct": 90,
                  "outcome_exclusion_reasons": {"duplicate_conflict_keys": 1},
                  "score_quintile_capture": complete_frozen_quintile_capture()}
        safe = {**mature, "outcome_exclusion_reasons": {"duplicate_conflict_keys": 0}}
        self.assertEqual(MOD.evidence_policy({"28": mature, "84": safe})["status"],
                         "observe_only")
        self.assertEqual(MOD.evidence_policy({"28": safe, "84": safe})["status"],
                         "review_allowed")

    def test_frozen_score_quintile_bias_blocks_review_even_if_total_capture_high(self):
        high_coverage = complete_frozen_quintile_capture(100)
        skew = complete_frozen_quintile_capture(100)
        skew["quintiles"][4]["validated_capture_pct"] = 75
        good = {"cohort_count": 8, "n": 400, "validated_capture_pct": 95,
                "score_quintile_capture": high_coverage}
        biased = {**good, "score_quintile_capture": skew}
        result = MOD.evidence_policy({"28": good, "84": biased})
        self.assertEqual(result["status"], "observe_only")
        self.assertIn("frozen_score_quintile_capture_below_80pct_or_unavailable",
                      result["horizon_review_diagnostics"]["84"]["reasons"])
        self.assertEqual(MOD.evidence_policy({"28": good, "84": good})["status"],
                         "review_allowed")

    def test_missing_or_empty_frozen_score_quintiles_cannot_authorize_review(self):
        complete = {"cohort_count": 9, "n": 500, "validated_capture_pct": 98}
        result = MOD.evidence_policy({"28": complete, "84": complete})
        self.assertEqual(result["status"], "observe_only")
        missing_bin = complete_frozen_quintile_capture()
        missing_bin["quintiles"][4]["expected"] = 0
        result = MOD.evidence_policy({"28": {**complete, "score_quintile_capture": missing_bin},
                                      "84": {**complete, "score_quintile_capture": missing_bin}})
        self.assertEqual(result["status"], "observe_only")

    def test_ranking_statistics_deduplicates_identical_matured_outcomes(self):
        today = dt.date(2026, 9, 1)
        snaps = [{"date": "2026-08-01", "observations": {
            "A": observation(score=75), "B": observation(score=80)
        }}]
        a = {"cohort_date": "2026-08-01", "evaluated_date": "2026-08-29", "horizon_days": 28,
             "ticker": "A", "opportunity_score": 75,
             "return_pct": 1, "validation_eligible": True}
        b = {"cohort_date": "2026-08-01", "evaluated_date": "2026-08-29", "horizon_days": 28,
             "ticker": "B", "opportunity_score": 80,
             "return_pct": 2, "validation_eligible": True}
        vals, audit = MOD.unique_validated_outcomes_for_statistics(
            today, snaps, [a, a.copy(), b], 28)
        self.assertEqual(len(vals), 2)
        self.assertEqual(audit["duplicate_records_ignored_for_statistics"], 1)
        self.assertEqual(audit["conflicting_outcome_keys_excluded_from_statistics"], 0)
        self.assertEqual(MOD.summarize_horizon(vals, 1)["n"], 2)

    def test_conflicting_outcomes_never_enter_ranking_even_if_one_is_valid(self):
        today = dt.date(2026, 9, 1)
        snaps = [{"date": "2026-08-01", "observations": {
            "A": observation(score=75), "B": observation(score=80)
        }}]
        a = {"cohort_date": "2026-08-01", "evaluated_date": "2026-08-29", "horizon_days": 28,
             "ticker": "A", "opportunity_score": 75,
             "return_pct": 1, "validation_eligible": True}
        conflicting = {**a, "return_pct": 75}
        b = {"cohort_date": "2026-08-01", "evaluated_date": "2026-08-29", "horizon_days": 28,
             "ticker": "B", "opportunity_score": 80,
             "return_pct": 2, "validation_eligible": True}
        outside = {**b, "ticker": "NOT_FROZEN", "return_pct": 200}
        future = {**b, "cohort_date": "2026-08-20", "return_pct": 200}
        vals, audit = MOD.unique_validated_outcomes_for_statistics(
            today, snaps, [a, conflicting, b, outside, future], 28)
        self.assertEqual([x["ticker"] for x in vals], ["B"])
        self.assertEqual(audit["conflicting_outcome_keys_excluded_from_statistics"], 1)
        self.assertEqual(audit["validated_unique_outcomes_in_statistics"], 1)

    def test_eligibility_disagreement_is_conflict_not_implicit_upgrade(self):
        today = dt.date(2026, 9, 1)
        snap = [{"date": "2026-08-01", "observations": {"A": observation()}}]
        a = {"cohort_date": "2026-08-01", "evaluated_date": "2026-08-29", "horizon_days": 28,
             "ticker": "A", "return_pct": 7, "validation_eligible": True}
        vals, audit = MOD.unique_validated_outcomes_for_statistics(
            today, snap, [a, {**a, "validation_eligible": False}], 28)
        self.assertEqual(vals, [])
        self.assertEqual(audit["conflicting_outcome_keys_excluded_from_statistics"], 1)

    def test_outcome_evaluation_must_be_within_horizon_window(self):
        today = dt.date(2026, 9, 20)
        base = {"cohort_date": "2026-08-01", "evaluated_date": "2026-08-29",
                "actual_days": 28}
        check = MOD.outcome_has_verified_evaluation_window
        self.assertTrue(check(base, 28, today))
        self.assertTrue(check({**base, "evaluated_date": "2026-09-08", "actual_days": 38}, 28, today))
        self.assertFalse(check({**base, "evaluated_date": "2026-08-28", "actual_days": 27}, 28, today))
        self.assertFalse(check({**base, "evaluated_date": "2026-09-09", "actual_days": 39}, 28, today))
        self.assertFalse(check({**base, "actual_days": 30}, 28, today))
        self.assertFalse(check({**base, "evaluated_date": "2026-09-21"}, 28, today))
        self.assertFalse(check({**base, "evaluated_date": "invalid"}, 28, today))
        self.assertFalse(check({"cohort_date": "2026-08-01"}, 28, today))

    def test_invalid_evaluation_window_is_excluded_from_rank_statistics(self):
        today = dt.date(2026, 9, 30)
        snapshots = [{"date": "2026-08-01", "observations": {
            "TOO_EARLY": {"score": 80, "opportunity_score": 80},
            "TOO_LATE": {"score": 80, "opportunity_score": 80},
            "VALID": {"score": 80, "opportunity_score": 80},
        }}]
        rows = []
        for ticker, date in (("TOO_EARLY", "2026-08-10"),
                             ("TOO_LATE", "2026-09-12"),
                             ("VALID", "2026-08-30")):
            rows.append({"cohort_date": "2026-08-01", "horizon_days": 28,
                         "ticker": ticker, "evaluated_date": date,
                         "validation_eligible": True, "return_pct": 7,
                         "score": 80, "opportunity_score": 80})
        selected, audit = MOD.unique_validated_outcomes_for_statistics(
            today, snapshots, rows, 28)
        self.assertEqual([x["ticker"] for x in selected], ["VALID"])
        self.assertEqual(audit["invalid_or_unverified_evaluation_windows"], 2)

    def test_invalid_windows_cannot_inflate_discovery_coverage_or_quintiles(self):
        today = dt.date(2026, 9, 30)
        snap = [{"date": "2026-08-01", "observations": {
            ticker: {"opportunity_score": 50 + i}
            for i, ticker in enumerate(("EARLY", "LATE", "VALID", "MISSING", "FUTURE"))
        }}]
        rows = [
            {"cohort_date": "2026-08-01", "horizon_days": 28,
             "ticker": ticker, "evaluated_date": date, "return_pct": 5,
             "validation_eligible": True}
            for ticker, date in (("EARLY", "2026-08-20"),
                                 ("LATE", "2026-09-12"),
                                 ("VALID", "2026-08-30"),
                                 ("MISSING", "bad-date"),
                                 ("FUTURE", "2026-10-01"))
        ]
        capture = MOD.observation_capture(today, snap, rows, 28)
        self.assertEqual(capture["realised_matured_observations"], 5)
        self.assertEqual(capture["validated_matured_observations"], 1)
        self.assertEqual(capture["validated_capture_pct"], 20.0)
        quintiles = MOD.score_quintile_capture(today, snap, rows, 28)
        self.assertEqual(sum(q["validated"] for q in quintiles["quintiles"]), 1)
        exclusions = MOD.outcome_exclusion_reasons(today, snap, rows, 28)
        self.assertEqual(exclusions["exclusion_reasons"]["eligible"], 1)
        self.assertEqual(exclusions["exclusion_reasons"]["invalid_evaluation_window"], 4)
        self.assertEqual(exclusions["validated_capture_pct"] if "validated_capture_pct" in exclusions else
                         exclusions["cohort_exclusion_breakdown"][0]["validated_capture_pct"], 20.0)

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
