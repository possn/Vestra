import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from prebreakout_paired_gate_audit import summarize

def row(ticker, first, base, vcp, intact, *, evaluable=True):
    return {"ticker": ticker, "evaluable": evaluable, "first_rejection": first,
            "geometry_shadow": {"base_width_pass": base, "contractions_pass": vcp},
            "research_prebreakout_lineage": {"unbroken_prebreakout_position": intact},
            "ma_failed_checks": ["price_above_ma50"] if first == "moving_average_structure" else [],
            "ma_structure_shadow": {"status": "measured",
                "price_order_pass": first != "moving_average_structure",
                "three_slopes_rising": True,
                "all_pass": first != "moving_average_structure",
                "research_only_no_eligibility_or_score_effect": True},
            "technical_evidence_shadow": {"close_position20": 0.12, "relative_strength_to_index": None},
            "swing_geometry_shadow": {"status": "measured", "all_geometry_pass": bool(base and vcp and intact)},
            "geometry_phase_shadow": {"phase_offsets_sessions": list(range(11)),
                "both_pass_count": 2 if base and vcp else 0,
                "canonical_both_pass": bool(base and vcp)}}

def feed(rows):
    return {"schema": "vestra_prebreakout_v1", "generated_at": "2026-11-21T14:20:00+00:00",
            "attempted": len(rows), "eligible_universe": 1524,
            "research_observations": {"rows": rows},
            "gate_funnel": {"observed_rows": len(rows), "first_rejection_counts": {
                "moving_average_structure": sum(r.get("first_rejection") == "moving_average_structure" for r in rows)}}}

class PairedGateAuditTests(unittest.TestCase):
    def test_same_row_denominators_and_overlap(self):
        report = summarize(feed([row("A", "moving_average_structure", True, True, True),
                                 row("B", "moving_average_structure", True, False, True),
                                 row("C", "sequential_vcp_contractions", True, False, True),
                                 row("D", "passed_structural_gates", True, True, True)]))
        c = report["counts"]
        self.assertEqual(c["paired_evaluable"], 4)
        self.assertEqual(c["both_geometry_pass"], 2)
        self.assertEqual(c["geometry_both_unbroken_rejected_ma"], 1)
        self.assertEqual(c["strict_structural_pass"], 1)
        self.assertEqual(report["overlapping_ma_failed_checks"]["price_above_ma50"], 2)
        self.assertEqual(report["sample_not_recommendations"][0]["ticker"], "A")
        self.assertIsNone(report["calibrated_probability"])
        self.assertFalse(report["forecast_performance_validated"])

    def test_independent_ma_geometry_matrix_is_paired_not_first_rejection(self):
        rows = [row("A", "moving_average_structure", True, True, True),
                row("B", "moving_average_structure", True, False, True),
                row("C", "sequential_vcp_contractions", True, False, True),
                row("D", "passed_structural_gates", True, True, True)]
        matrix = summarize(feed(rows))["independent_ma_geometry_matrix"]
        self.assertEqual(matrix["counts"]["paired_rows"], 4)
        self.assertEqual(matrix["counts"]["geometry_pass_ma_fail"], 1)
        self.assertEqual(matrix["counts"]["geometry_pass_ma_pass"], 1)
        self.assertEqual(matrix["counts"]["geometry_fail_ma_fail"], 1)
        self.assertEqual(matrix["counts"]["geometry_fail_ma_pass"], 1)
        self.assertTrue(matrix["descriptive_not_an_ablation_or_forward_validation"])

    def test_missing_and_conflicting_ma_capture_is_not_counted_as_failure(self):
        rows = [row("A", "moving_average_structure", True, True, True),
                row("B", "passed_structural_gates", True, True, True),
                row("C", "base_width", False, False, True)]
        del rows[0]["ma_structure_shadow"]
        rows[1]["ma_structure_shadow"]["all_pass"] = False
        matrix = summarize(feed(rows))["independent_ma_geometry_matrix"]["counts"]
        self.assertEqual(matrix["paired_rows"], 1)
        self.assertEqual(matrix["geometry_fail_ma_pass"], 1)
        self.assertEqual(matrix["missing_or_conflicting_ma_capture"], 2)

    def test_alternative_geometry_same_population_and_phase_stability(self):
        rows = [row("A", "moving_average_structure", True, True, True),
                row("B", "moving_average_structure", True, False, True),
                row("C", "passed_structural_gates", True, True, True)]
        rows[1]["swing_geometry_shadow"]["all_geometry_pass"] = True
        rows[1]["geometry_phase_shadow"]["both_pass_count"] = 3
        alternative = summarize(feed(rows))["alternative_geometry_comparison"]
        count = alternative["counts"]
        self.assertEqual(count["swing_comparable"], 3)
        self.assertEqual(count["both_fixed_and_swing_pass"], 2)
        self.assertEqual(count["swing_only_pass"], 1)
        self.assertEqual(count["alternate_phase_only"], 1)
        self.assertEqual(count["fixed_pass_phase_robust"], 2)
        self.assertTrue(alternative["no_outcome_or_precision_claim"])

    def test_missing_alternatives_are_unknown_not_negative(self):
        rows = [row("A", "moving_average_structure", True, True, True),
                row("B", "moving_average_structure", True, False, True)]
        del rows[1]["swing_geometry_shadow"]
        rows[1]["geometry_phase_shadow"]["canonical_both_pass"] = True
        comparison = summarize(feed(rows))["alternative_geometry_comparison"]
        self.assertEqual(comparison["counts"]["swing_comparable"], 1)
        self.assertEqual(comparison["missing_or_unverifiable"]["swing"], 1)
        self.assertEqual(comparison["counts"]["phase_comparable"], 1)
        self.assertEqual(comparison["missing_or_unverifiable"]["phase"], 1)

    def test_missing_evidence_is_unknown_not_negative(self):
        rows = [row("A", "moving_average_structure", True, True, True),
                row("B", "moving_average_structure", True, True, True)]
        del rows[1]["geometry_shadow"]
        result = summarize(feed(rows))["counts"]
        self.assertEqual(result["paired_evaluable"], 1)
        self.assertEqual(result["missing_matched_evidence"], 1)
        self.assertEqual(result["both_geometry_pass"], 1)

    def test_rejects_duplicate_identity_and_bad_denominator(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            summarize(feed([row("A", "moving_average_structure", True, True, True)] * 2))
        data = feed([row("A", "moving_average_structure", True, True, True)])
        data["attempted"] = 2
        with self.assertRaisesRegex(ValueError, "denominator"):
            summarize(data)

    def test_rejects_inconsistent_funnel_and_naive_time(self):
        data = feed([row("A", "moving_average_structure", True, True, True)])
        data["gate_funnel"]["observed_rows"] = 2
        with self.assertRaisesRegex(ValueError, "reconcile"):
            summarize(data)
        data["gate_funnel"]["observed_rows"] = 1
        data["generated_at"] = "2026-11-21T14:20:00"
        with self.assertRaisesRegex(ValueError, "naive"):
            summarize(data)

if __name__ == "__main__":
    unittest.main()
