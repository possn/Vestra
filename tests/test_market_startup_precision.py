"""Startup wire format may trim float tails, never lose evidence or exact integers."""
import importlib.util
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location("build_market_shards", SCRIPTS / "build_market_shards.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class StartupPrecisionTests(unittest.TestCase):
    def test_preserves_all_fields_types_and_full_source(self):
        item = {"ticker": "JPM", "market_cap": 123456789012345,
                "score": 71.12345678912345, "current_price": 0.000000012345678912345,
                "risk_gate": "clear", "flag": True, "missing": None,
                "evidence": {"ratios": [0.123456789123456, 1, None]}}
        original = repr(item)
        packed = mod.pack_index_payload({"stocks": [item], "generated_at": "2026-10-17"})
        decoded = mod.unpack_index_payload(packed)["stocks"][0]
        self.assertEqual(repr(item), original)
        for key in item:
            self.assertIn(key, decoded)
        self.assertEqual(decoded["market_cap"], item["market_cap"])
        self.assertEqual(decoded["flag"], True)
        self.assertEqual(decoded["risk_gate"], "clear")
        self.assertEqual(decoded["evidence"]["ratios"][1:], [1, None])
        self.assertAlmostEqual(decoded["score"], item["score"], places=9)
        self.assertLess(abs(decoded["current_price"] / item["current_price"] - 1), 1e-10)

    def test_nan_not_changed_into_fake_value(self):
        self.assertTrue(mod.math.isnan(mod._compact_startup_value(float("nan"))))


if __name__ == "__main__":
    unittest.main()
