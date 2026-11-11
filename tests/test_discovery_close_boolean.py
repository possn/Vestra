"""Discovery close-series identity and historical integrity regression."""
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "opportunity_rank", ROOT / "scripts" / "opportunity_rank.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class DiscoveryCloseBarTests(unittest.TestCase):
    def test_boolean_close_is_never_interpreted_as_price_one(self):
        valid = [{"close": 100.0 + i} for i in range(65)]
        self.assertEqual(len(module._closes({"price_history_1y": valid})), 65)
        for bad in (True, False):
            with self.subTest(bad=bad):
                history = list(valid)
                history[33] = {"close": bad}
                self.assertEqual(module._closes({"price_history_1y": history}), [])
                self.assertIsNone(module._ret(
                    module._closes({"price_history_1y": history}), 20))

    def test_scalar_boolean_history_is_also_invalid(self):
        self.assertEqual(module._closes({"price_history_1y": [100, True, 103]}), [])

    def test_finite_numeric_closes_are_unchanged(self):
        self.assertEqual(module._closes({"price_history_1y": [100, 102, 105]}),
                         [100.0, 102.0, 105.0])


if __name__ == "__main__":
    unittest.main()
