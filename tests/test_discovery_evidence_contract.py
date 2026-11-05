"""Regression contracts for Discovery evidence eligibility.

Run: python -m unittest discover -s tests -p 'test_discovery_evidence_contract.py'
"""
import unittest
from unittest.mock import patch

from scripts import opportunity_rank


class DiscoveryEvidenceContractTests(unittest.TestCase):
    def row(self, **overrides):
        row = {
            "quote_type": "EQUITY",
            "score": 85,
            "confidence_score": 90,
            "data_coverage_pct": 90,
            "critical_metric_coverage_pct": 85,
            "score_reliability": "robust",
            "risk_gate": "clear",
        }
        row.update(overrides)
        return row

    def assess(self, row):
        with patch.object(opportunity_rank, "_timing_assessment", return_value={
            "score": 72, "reasons": [], "cautions": [],
            "overextended": False, "severely_overextended": False
        }):
            return opportunity_rank.assess(row)

    def test_missing_critical_coverage_is_not_eligible(self):
        result = self.assess(self.row(critical_metric_coverage_pct=None))
        self.assertFalse(result["opportunity_eligible"])
        self.assertIsNone(result["opportunity_score"])
        self.assertIn("Cobertura de métricas críticas", result["opportunity_reason"])

    def test_insufficient_data_reliability_is_not_eligible(self):
        result = self.assess(self.row(score_reliability="insufficient_data"))
        self.assertFalse(result["opportunity_eligible"])
        self.assertIsNone(result["opportunity_score"])

    def test_missing_reliability_is_not_eligible(self):
        result = self.assess(self.row(score_reliability=None))
        self.assertFalse(result["opportunity_eligible"])
        self.assertIsNone(result["opportunity_score"])

    def test_legacy_invalid_reliability_is_not_eligible(self):
        result = self.assess(self.row(score_reliability="suppressed"))
        self.assertFalse(result["opportunity_eligible"])
        self.assertIsNone(result["opportunity_score"])


if __name__ == "__main__":
    unittest.main()
