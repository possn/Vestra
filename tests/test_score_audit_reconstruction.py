import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("vestra_score_audit", ROOT / "scripts" / "score_audit.py")
mod = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(mod)


def general_row(i, *, cap=None, published_cap=None):
    value = 20.0 + i * 8.0
    dims = {name: value for name in mod.MODEL_WEIGHTS["general"]}
    raw = min(value, cap) if cap is not None else value
    published = min(raw, published_cap) if published_cap is not None else raw
    return {
        "ticker": f"T{i}",
        "score_model": "general",
        "score_dimensions": dims,
        "score_raw": raw,
        "score": published,
        "score_cap": cap,
        "data_coverage_pct": 80.0,
        "sector": "Test",
    }


class ScoreAuditReconstructionTests(unittest.TestCase):
    def test_apply_score_cap_mirrors_structural_risk_gate(self):
        self.assertEqual(mod.apply_score_cap(82.0, {"score_cap": 59.0}), 59.0)
        self.assertEqual(mod.apply_score_cap(42.0, {"score_cap": 59.0}), 42.0)
        self.assertEqual(mod.apply_score_cap(82.0, {"score_cap": None}), 82.0)

    def test_raw_score_prefers_pre_confidence_score(self):
        self.assertEqual(mod.raw_score({"score_raw": 71, "score": 59}), 71)
        self.assertEqual(mod.raw_score({"score": 59}), 59)

    def test_all_weight_packs_sum_to_one(self):
        for model, weights in mod.MODEL_WEIGHTS.items():
            self.assertAlmostEqual(sum(weights.values()), 1.0, places=9, msg=model)

    def test_effective_weight_profile_quantifies_missing_dimension_renormalization(self):
        weights = mod.MODEL_WEIGHTS["general"]
        dims = {name: 50.0 for name in weights}
        full = mod.effective_weight_profile(dims, weights)
        self.assertAlmostEqual(full["missing_weight_pct"], 0.0, places=6)
        self.assertAlmostEqual(full["renormalization_factor"], 1.0, places=6)

        sparse = dict(dims)
        sparse["Quality"] = None
        sparse["Growth"] = None
        profile = mod.effective_weight_profile(sparse, weights)
        self.assertAlmostEqual(profile["missing_weight_pct"], 33.0, places=6)
        self.assertGreater(profile["renormalization_factor"], 1.4)
        self.assertIsNotNone(profile["dominant_dimension"])

    def test_model_audit_reports_material_missing_weight(self):
        rows = [general_row(i) for i in range(10)]
        for row in rows:
            row["score_dimensions"]["Quality"] = None
            row["score_dimensions"]["Growth"] = None
        result = mod.model_audit("general", rows)
        renorm = result["missing_weight_renormalization"]
        self.assertEqual(renorm["rows_missing_at_least_20pct_weight"], 10)
        self.assertEqual(renorm["rows_missing_at_least_35pct_weight"], 0)
        self.assertAlmostEqual(result["weight_pack_sum"], 1.0, places=9)

    def test_model_audit_does_not_call_confidence_moderation_reconstruction_error(self):
        rows = [
            general_row(0),
            general_row(1),
            general_row(2),
            general_row(3, published_cap=59),
            general_row(4, published_cap=59),
            general_row(5, cap=59, published_cap=59),
            general_row(6, cap=59, published_cap=59),
            general_row(7, cap=69, published_cap=59),
            general_row(8, cap=69, published_cap=59),
            general_row(9, published_cap=59),
        ]
        result = mod.model_audit("general", rows)
        self.assertEqual(result["raw_vs_reconstructed_rank_spearman"], 1.0)
        self.assertLess(result["published_vs_raw_rank_spearman"], 1.0)

    def test_model_audit_exposes_raw_and_published_layers_separately(self):
        rows = [general_row(i, published_cap=59 if i >= 5 else None) for i in range(10)]
        result = mod.model_audit("general", rows)
        self.assertIn("mean_raw_score", result)
        self.assertIn("raw_vs_reconstructed_rank_spearman", result)
        self.assertIn("published_vs_raw_rank_spearman", result)
        self.assertNotIn("production_vs_reconstructed_rank_spearman", result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
