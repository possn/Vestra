import importlib.util
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

SPEC = importlib.util.spec_from_file_location("vestra_score_audit_publishability", SCRIPTS / "score_audit.py")
mod = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(mod)


class ScoreAuditPublishabilityTests(unittest.TestCase):
    def test_heavily_renormalized_published_rows_are_counted(self):
        rows = [
            {
                "ticker": "A",
                "score": 70,
                "score_raw": 70,
                "score_reliability": "robust",
                "score_dimensions": {
                    "Quality": 80,
                    "Balance": 70,
                    "Capital Allocation": 60,
                },
                "data_coverage_pct": 40,
            },
            {
                "ticker": "B",
                "score": None,
                "score_raw": 55,
                "score_reliability": "insufficient_data",
                "score_dimensions": {
                    "Quality": 50,
                    "Balance": 50,
                    "Capital Allocation": 50,
                },
                "data_coverage_pct": 30,
            },
        ]
        out = mod.model_audit("general", rows)
        renorm = out["missing_weight_renormalization"]
        self.assertEqual(renorm["rows_missing_at_least_35pct_weight"], 2)
        self.assertEqual(renorm["published_rows_missing_at_least_35pct_weight"], 1)
        self.assertEqual(renorm["robust_rows_missing_at_least_35pct_weight"], 1)

    def test_publishability_diagnostic_does_not_change_reconstructed_score(self):
        rows = [{
            "ticker": "A",
            "score": 70,
            "score_raw": 70,
            "score_reliability": "robust",
            "score_dimensions": {
                "Quality": 80,
                "Balance": 70,
                "Capital Allocation": 60,
            },
            "data_coverage_pct": 40,
        }]
        out = mod.model_audit("general", rows)
        self.assertIn("raw_vs_reconstructed_rank_spearman", out)
        self.assertIn("missing_weight_renormalization", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
