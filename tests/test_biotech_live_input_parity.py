import sys
import unittest
from pathlib import Path
from types import SimpleNamespace, ModuleType
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
fundamentals_stub = ModuleType("fundamentals")
fundamentals_stub.RawMetrics = type("RawMetrics", (), {})
with patch.dict(sys.modules, {"fundamentals": fundamentals_stub}):
    from score import _score_model_for, _benchmark_values, _percentile_rank, _avg
    from audit_biotech_live_input_parity import measure, shadow_ablation


class LiveInputParityTests(unittest.TestCase):
    def test_uses_exact_input_and_one_decimal_published_values(self):
        raw = []
        for i in range(25):
            raw.append(SimpleNamespace(
                ticker=f"BT{i}", quote_type="EQUITY", error=None,
                sector="Healthcare", industry="Biotechnology",
                gross_margin=0.10 + i * 0.01, roa=-0.40 + i * 0.02,
            ))
        scored = []
        for row in raw:
            expected = _avg([
                _percentile_rank(row.gross_margin, [x.gross_margin for x in raw]),
                _percentile_rank(row.roa, [x.roa for x in raw]),
            ])
            scored.append(SimpleNamespace(ticker=row.ticker,
                score_dimensions={"Operating Quality": round(expected, 1)}))
        output = measure(raw, scored)
        self.assertEqual(output["biotech_input_rows"], 25)
        self.assertEqual(output["comparable_rows"], 25)
        self.assertEqual(output["outside_rounding_tolerance"], 0)
        self.assertEqual(output["max_absolute_parity_delta"], 0)

    def test_same_run_shadow_is_nonmutating_and_reports_observed_pairs(self):
        raw = [SimpleNamespace(
            ticker=f"BT{i}", quote_type="EQUITY", error=None,
            sector="Healthcare", industry="Biotechnology",
            gross_margin=i / 100, roa=(24-i) / 100,
        ) for i in range(25)]
        scored = [SimpleNamespace(
            ticker=x.ticker, score_raw=float(75-i), score_dimensions={
                "Operating Quality": 50.0,
                "Cash Runway": float(i+1),
            }) for i,x in enumerate(raw)]
        before = [dict(x.score_dimensions) for x in scored]
        result = shadow_ablation(raw, scored)
        self.assertEqual(result["same_run_biotech_rows"], 25)
        self.assertFalse(result["native_quality_parity_passed"])
        self.assertFalse(any(c["parity_gate_passed"] for c in result["candidates"]))
        self.assertFalse(result["historical_cohort_comparable"])
        self.assertEqual([x["roa_weight"] for x in result["candidates"]],
                         [0.0, 0.1, 0.2, 0.3, 0.4, 0.5])
        self.assertTrue(all(x["pairs"] == 25 for x in result["candidates"]))
        self.assertTrue(all(x["uncapped_ranking_rows"] == 25 for x in result["candidates"]))
        self.assertTrue(all(x["uncapped_rank_shifts_ge_10"] is not None for x in result["candidates"]))
        self.assertEqual([x.score_dimensions for x in scored], before)

    def test_shadow_accepts_only_exact_same_cohort_native_quality(self):
        raw = [SimpleNamespace(
            ticker=f"BT{i}", quote_type="EQUITY", error=None,
            sector="Healthcare", industry="Biotechnology",
            gross_margin=0.10 + i * 0.01, roa=-0.40 + i * 0.02,
        ) for i in range(25)]
        gross = [r.gross_margin for r in raw]
        roa = [r.roa for r in raw]
        scored = [SimpleNamespace(
            ticker=r.ticker, score_raw=50.0 + i,
            score_dimensions={
                "Operating Quality": round(_avg([
                    _percentile_rank(r.gross_margin, gross),
                    _percentile_rank(r.roa, roa),
                ]), 1),
                "Cash Runway": float(i + 1),
            }) for i, r in enumerate(raw)]
        result = shadow_ablation(raw, scored)
        self.assertEqual(result["native_quality_parity_rows"], 25)
        self.assertTrue(result["native_quality_parity_passed"])
        self.assertEqual(result["native_quality_max_rounding_delta"], 0)
        self.assertTrue(all(c["parity_gate_passed"] for c in result["candidates"]))

    def test_detects_a_real_mismatch_without_changing_scores(self):
        raw = [SimpleNamespace(ticker=f"BT{i}", quote_type="EQUITY", error=None,
                 sector="Healthcare", industry="Biotechnology",
                 gross_margin=i/25, roa=i/40) for i in range(25)]
        scored = [SimpleNamespace(ticker=row.ticker,
                 score_dimensions={"Operating Quality": 50.0}) for row in raw]
        before = [x.score_dimensions.copy() for x in scored]
        output = measure(raw, scored)
        self.assertGreater(output["outside_rounding_tolerance"], 0)
        self.assertEqual([x.score_dimensions for x in scored], before)


if __name__ == "__main__":
    unittest.main()
