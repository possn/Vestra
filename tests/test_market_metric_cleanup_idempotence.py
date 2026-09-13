from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class MarketMetricCleanupIdempotenceTests(unittest.TestCase):
    def test_empty_or_placeholder_values_never_coerce_to_zero(self):
        js = (ROOT / "market-metric-cleanup.js").read_text(encoding="utf-8")
        self.assertIn("if(!z||!/[0-9]/.test(z))return null", js)

    def test_invalid_multiple_placeholder_is_written_once(self):
        js = (ROOT / "market-metric-cleanup.js").read_text(encoding="utf-8")
        self.assertIn("x!=null&&x<=0&&v.textContent!=='—'", js)
        self.assertIn("window.VestraMarketMetricCleanup", js)
        self.assertIn("version:'1.2'", js)


if __name__ == "__main__":
    unittest.main(verbosity=2)
