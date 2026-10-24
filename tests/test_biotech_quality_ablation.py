import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from audit_biotech_quality_ablation import _percentile, report

class BiotechAblationTests(unittest.TestCase):
    def test_percentile_observes_source_and_missing_values(self):
        self.assertEqual(_percentile(2, [1, 2, 3]), 200/3)
        self.assertIsNone(_percentile(None, [1, 2]))
        self.assertIsNone(_percentile(1, []))

    def test_diagnostic_never_publishes_a_model(self):
        result = report()
        print("BIOTECH_GROSS_ONLY_SHADOW", result)
        self.assertFalse(result["candidate_published"])
        self.assertGreater(result["comparable_pairs"], 20)
        self.assertIsNotNone(result["gross_only_candidate_rho"])

if __name__ == "__main__":
    unittest.main()
