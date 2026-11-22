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
            "technical_evidence_shadow": {"close_position20": 0.12, "relative_strength_to_index": None}}

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
