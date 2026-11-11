"""Dividend-growth finite aggregation regression for scanner research overlays."""
import importlib.util
import math
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
    stub = types.ModuleType(name)
    stub.assess = lambda row: {}
    stubs[name] = stub
spec = importlib.util.spec_from_file_location("scanner", ROOT / "scripts" / "scanner.py")
scanner = importlib.util.module_from_spec(spec)
with patch.dict(sys.modules, stubs):
    spec.loader.exec_module(scanner)


class DividendGrowthAggregationTests(unittest.TestCase):
    def test_mean_of_finite_components_cannot_overflow(self):
        # Two finite, very large year-on-year growth observations can sum
        # to Infinity before division. Never propagate a non-finite mean.
        row = {"annual_dividend_history": [1e308, 1.0, 1e308, 1.0]}
        value = scanner._dividend_growth(row)
        self.assertIsNotNone(value)
        self.assertTrue(math.isfinite(value))
        self.assertGreater(value, 0)

    def test_regular_growth_mean_unchanged(self):
        row = {"annual_dividend_history": [121.0, 110.0, 100.0]}
        self.assertAlmostEqual(scanner._dividend_growth(row), 0.1)

    def test_nonfinite_individual_growth_stays_excluded(self):
        row = {"annual_dividend_history": [1e308, 1e-308]}
        self.assertIsNone(scanner._dividend_growth(row))


if __name__ == "__main__":
    unittest.main()
