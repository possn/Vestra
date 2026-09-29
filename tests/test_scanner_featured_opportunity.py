import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import scanner  # noqa: E402


class ScannerFeaturedOpportunityTests(unittest.TestCase):
    def base_row(self):
        return {
            "ticker": "TEST",
            "quote_type": "EQUITY",
            "score": 70,
            "quality_pct": 60,
            "value_pct": 50,
            "data_coverage_pct": 80,
            "critical_metric_coverage_pct": 70,
            "confidence_score": 80,
            "score_reliability": "robust",
            "risk_gate": "clear",
        }

    def test_discovery_eligible_but_not_featured_is_not_best_opportunity(self):
        overlay = {
            "opportunity_score": 60.0,
            "opportunity_label": "Interessante",
            "opportunity_eligible": True,
            "opportunity_featured": False,
            "opportunity_reasons": ["Discovery elegível"],
            "opportunity_cautions": [],
        }
        with mock.patch.object(scanner, "_structural_overlays", return_value=overlay):
            out = scanner.assess(self.base_row())
        self.assertTrue(out["opportunity_eligible"])
        self.assertFalse(out["opportunity_featured"])
        self.assertNotIn("best_opportunities", out["scanner_results"])
        self.assertNotEqual(out.get("scanner_best"), "best_opportunities")

    def test_featured_candidate_is_exposed_as_best_opportunity(self):
        overlay = {
            "opportunity_score": 72.0,
            "opportunity_label": "Oportunidade forte",
            "opportunity_eligible": True,
            "opportunity_featured": True,
            "opportunity_reasons": ["Discovery forte"],
            "opportunity_cautions": [],
        }
        with mock.patch.object(scanner, "_structural_overlays", return_value=overlay):
            out = scanner.assess(self.base_row())
        self.assertIn("best_opportunities", out["scanner_results"])
        self.assertEqual(out["scanner_results"]["best_opportunities"]["score"], 72.0)
        self.assertEqual(out["scanner_best"], "best_opportunities")
        self.assertEqual(out["scanner_best_score"], 72.0)

    def test_suppressed_scanner_payload_explicitly_marks_not_featured(self):
        out = scanner._empty("Sem evidência")
        self.assertFalse(out["opportunity_eligible"])
        self.assertFalse(out["opportunity_featured"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
