"""The discovery universe is not the verified OHLCV/signal population."""
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
# Discovery tests do not need network clients or provider installations.
for module in ("pandas", "requests", "yfinance"):
    if module not in sys.modules:
        try:
            __import__(module)
        except ImportError:
            sys.modules[module] = types.ModuleType(module)
import universe


class SmallcapUniverseExpansionTests(unittest.TestCase):
    def test_four_cap_bands_prevent_global_first_500_truncation(self):
        calls = []

        def screen(low, high, limit, sort_desc=False):
            calls.append((low, high, limit))
            return [f"B{len(calls)}_{i}" for i in range(600)]

        with patch.object(universe, "_us_cap_range_screener", side_effect=screen):
            symbols = universe.us_small_micro_cap()
        self.assertEqual(len(calls), 4)
        self.assertEqual(len(symbols), 2400)
        self.assertEqual(len(symbols), len(set(symbols)))
        self.assertEqual(calls[0][:2], (50_000_000, 150_000_000))
        self.assertEqual(calls[-1][:2], (900_000_000, 2_000_000_000))

    def test_overlap_is_deduplicated_and_budget_respected(self):
        with patch.object(universe, "_us_cap_range_screener", return_value=["AAA", "BBB"]):
            self.assertEqual(universe.us_small_micro_cap(), ["AAA", "BBB"])
        with patch.object(universe, "_us_cap_range_screener", return_value=["AAA", "BBB", "CCC"]):
            self.assertEqual(universe.us_small_micro_cap(2), ["AAA", "BBB"])

    def test_invalid_budget_is_rejected(self):
        for value in (-1, 1.5, True):
            with self.subTest(value=value), self.assertRaises(ValueError):
                universe.us_small_micro_cap(value)


if __name__ == "__main__":
    unittest.main()
