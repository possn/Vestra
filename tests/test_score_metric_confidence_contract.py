from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ScoreMetricConfidenceContractTests(unittest.TestCase):
    def test_metric_confidence_depends_on_metric_coverage_not_risk_gate(self):
        source = (ROOT / 'scripts' / 'score.py').read_text(encoding='utf-8')
        self.assertIn('confidence = "high" if metric_coverage >= 70 else "medium" if metric_coverage >= 40 else "low"', source)
        self.assertNotIn('if risk_gate == "severe":\n            confidence = "low"', source)
        self.assertNotIn('elif risk_gate == "high" and confidence == "high":\n            confidence = "medium"', source)


if __name__ == '__main__':
    unittest.main(verbosity=2)
