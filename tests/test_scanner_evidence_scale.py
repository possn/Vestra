"""Fundamental evidence scale contract for generic scanner eligibility."""
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
dependencies = (
    "capital_allocation_intelligence", "moat", "sector_native",
    "value_trap", "opportunity_rank",
)
stubs = {}
for name in dependencies:
    module = types.ModuleType(name)
    module.assess = lambda row: {}
    stubs[name] = module
spec = importlib.util.spec_from_file_location("scanner", ROOT / "scripts" / "scanner.py")
scanner = importlib.util.module_from_spec(spec)
with patch.dict(sys.modules, stubs):
    spec.loader.exec_module(scanner)


class ScannerEvidenceScaleTests(unittest.TestCase):
    @staticmethod
    def valid():
        return {
            "score": 75,
            "data_coverage_pct": 80,
            "critical_metric_coverage_pct": 70,
            "confidence_score": 65,
            "score_reliability": "robust",
        }

    def test_accept_valid_evidence(self):
        self.assertEqual(scanner._evidence_ok(self.valid()), (True, None))

    def test_refuse_out_of_range_and_nonfinite_evidence(self):
        for field in ("score", "data_coverage_pct",
                      "critical_metric_coverage_pct", "confidence_score"):
            for invalid in (-1, 101, float("nan"), float("inf"), True):
                with self.subTest(field=field, invalid=invalid):
                    row = self.valid()
                    row[field] = invalid
                    self.assertFalse(scanner._evidence_ok(row)[0])

    def test_refuse_unknown_reliability(self):
        row = self.valid()
        row["score_reliability"] = "unknown"
        self.assertFalse(scanner._evidence_ok(row)[0])


if __name__ == "__main__":
    unittest.main()
