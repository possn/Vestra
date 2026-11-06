"""Prospective Discovery attrition: compare all frozen scores, not survivors."""
import datetime as dt
import unittest
from scripts.opportunity_forward_validation import score_quintile_capture


class QuintileCaptureTests(unittest.TestCase):
    def test_all_frozen_scores_define_bins_even_if_high_scores_disappear(self):
        frozen = {"T%02d" % i: {"opportunity_score": i} for i in range(10)}
        snapshots = [{"date": "2026-08-01", "observations": frozen}]
        outcomes = [
            {"cohort_date": "2026-08-01", "horizon_days": 28,
             "ticker": "T%02d" % i, "validation_eligible": True,
             "return_pct": i / 10} for i in range(6)
        ]
        result = score_quintile_capture(dt.date(2026, 09, 01),
                                        snapshots, outcomes, 28)
        self.assertEqual([q["expected"] for q in result["quintiles"]], [2]*5)
        self.assertEqual([q["validated"] for q in result["quintiles"]], [2,2,2,0,0])
        self.assertEqual(result["validated_capture_spread_pp"], 100)
        self.assertEqual(result["selection_bias_status"], "unresolved")

    def test_duplicate_or_unvalidated_outcome_never_boosts_capture(self):
        snapshots = [{"date": "2026-08-01", "observations": {
            "A": {"opportunity_score": 10},
            "B": {"opportunity_score": 20},
        }}]
        outcomes = [
            {"cohort_date": "2026-08-01", "horizon_days": 28, "ticker": "A",
             "validation_eligible": True, "return_pct": 1},
            {"cohort_date": "2026-08-01", "horizon_days": 28, "ticker": "A",
             "validation_eligible": True, "return_pct": 1},
            {"cohort_date": "2026-08-01", "horizon_days": 28, "ticker": "B",
             "validation_eligible": False, "return_pct": 7},
        ]
        result = score_quintile_capture(dt.date(2026, 9, 1),
                                        snapshots, outcomes, 28)
        self.assertEqual(sum(x["recorded"] for x in result["quintiles"]), 2)
        self.assertEqual(sum(x["validated"] for x in result["quintiles"]), 1)
        self.assertEqual(sum(x["unvalidated"] for x in result["quintiles"]), 1)

    def test_unmatured_cohorts_not_counted_and_no_fabricated_zero(self):
        snapshots = [{"date": "2026-10-30", "observations": {
            "A": {"opportunity_score": 90},
        }}]
        result = score_quintile_capture(dt.date(2026, 11, 6),
                                        snapshots, [], 28)
        self.assertEqual(result["matured_cohorts"], 0)
        self.assertEqual(result["selection_bias_status"], "not_yet_mature")
        self.assertEqual(result["validated_capture_spread_pp"], None)
        self.assertTrue(all(x["validated_capture_pct"] is None
                            for x in result["quintiles"]))

    def test_missing_scores_are_visible_and_ties_are_deterministic(self):
        snapshots = [{"date": "2026-08-01", "observations": {
            "Z": {"opportunity_score": 50},
            "A": {"opportunity_score": 50},
            "NO_SCORE": {},
        }}]
        result = score_quintile_capture(dt.date(2026, 9, 1),
                                        snapshots, [], 28)
        self.assertEqual(result["missing_or_invalid_score_count"], 1)
        self.assertEqual(sum(x["expected"] for x in result["quintiles"]), 2)


if __name__ == "__main__":
    unittest.main()
