"""Dividend yield unit ambiguity must not create absurd Dividend Growers."""
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
stubs = {}
for name in ("capital_allocation_intelligence", "moat", "sector_native",
             "value_trap", "opportunity_rank"):
    module = types.ModuleType(name)
    module.assess = lambda row: {}
    stubs[name] = module
spec = importlib.util.spec_from_file_location("scanner_yield_gate", ROOT / "scripts" / "scanner.py")
scanner = importlib.util.module_from_spec(spec)
with patch.dict(sys.modules, stubs):
    spec.loader.exec_module(scanner)


def eligible(div_yield):
    return {
        "quote_type": "EQUITY",
        "score": 70, "quality_pct": 75, "confidence_score": 80,
        "data_coverage_pct": 80, "critical_metric_coverage_pct": 75,
        "score_reliability": "robust", "risk_gate": "clear",
        "dividend_yield": div_yield,
        "annual_dividend_history": [1.2, 1.1, 1.0],
        "diluted_shares_yoy": 0.01,
        "dividend_fcf_coverage": 1.5,
    }


class DividendYieldScaleGateTests(unittest.TestCase):
    def test_regular_fraction_yield_still_admitted(self):
        result = scanner.assess(eligible(0.05))
        self.assertIn("dividend_growers", result["scanner_results"])
        self.assertIn("5.0%", result["scanner_results"]["dividend_growers"]["reasons"][0])

    def test_ambiguous_or_extreme_unit_inputs_rejected(self):
        for value in (0.9, 1.05, 2.63, 43.1, 5.0, float("inf"),
                      float("nan"), True, -0.1, 0):
            with self.subTest(value=value):
                result = scanner.assess(eligible(value))
                self.assertNotIn("dividend_growers", result["scanner_results"])

    def test_conservative_boundary(self):
        self.assertIn("dividend_growers", scanner.assess(eligible(0.25))["scanner_results"])
        self.assertNotIn("dividend_growers", scanner.assess(eligible(0.25001))["scanner_results"])


if __name__ == "__main__":
    unittest.main()
