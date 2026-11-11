"""Reject Boolean values masquerading as numerical Discovery signals."""
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "opportunity_rank", ROOT / "scripts" / "opportunity_rank.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class DiscoveryNumericIntegrityTests(unittest.TestCase):
    def test_bool_is_not_an_observed_financial_metric(self):
        self.assertIsNone(module._f(True))
        self.assertIsNone(module._f(False))
        self.assertIsNone(module._f(None))
        self.assertIsNone(module._f(""))

    def test_valid_numeric_values_are_unchanged(self):
        self.assertEqual(module._f(1), 1.0)
        self.assertEqual(module._f(0), 0.0)
        self.assertEqual(module._f("73.5"), 73.5)

    def test_nonfinite_numeric_values_are_unknown(self):
        self.assertIsNone(module._f(float("nan")))
        self.assertIsNone(module._f(float("inf")))
        self.assertIsNone(module._f(float("-inf")))


if __name__ == "__main__":
    unittest.main()
