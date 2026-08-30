from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class WorkerMissingNumericSemanticsTests(unittest.TestCase):
    def test_null_safe_numeric_helper_prevents_number_null_zero_coercion(self):
        worker = read("worker.js")
        self.assertIn("function numberOrNull(node)", worker)
        self.assertIn("if (value === null || value === undefined || value === '') return null", worker)
        self.assertIn("const v = numberOrNull(node)", worker)
        self.assertNotIn("const v = Number(raw(node))", worker)
        self.assertNotIn("const n = Number(raw(v))", worker)

    def test_market_payload_uses_null_safe_numeric_reads(self):
        worker = read("worker.js")
        self.assertIn("const marketCap = firstFinite(numberOrNull(price.marketCap)", worker)
        self.assertIn("analyst_price_target_mean: target !== null && target > 0 ? target : null", worker)
        self.assertIn("current_ratio: numberOrNull(fd.currentRatio)", worker)
        self.assertIn("beta: numberOrNull(ks.beta)", worker)
        self.assertIn('missing_numeric_policy: "null"', worker)

    def test_missing_chart_closes_are_not_serialized_as_zero(self):
        worker = read("worker.js")
        self.assertIn("const close = numberOrNull(closes[i])", worker)
        self.assertIn("close !== null && close > 0", worker)
        self.assertNotIn("close:Number(closes[i])", worker)

    def test_new_market_cache_generation_does_not_reuse_zero_coerced_payloads(self):
        worker = read("worker.js")
        self.assertIn("market45:${canonical}", worker)
        self.assertNotIn("market41:${canonical}", worker)


if __name__ == "__main__":
    unittest.main(verbosity=2)
