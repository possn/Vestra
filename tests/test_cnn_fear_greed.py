import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch
import importlib.util

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("refresh_cnn_fear_greed", ROOT / "scripts/refresh_cnn_fear_greed.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class CnnSentimentTests(unittest.TestCase):
    def test_official_schema_keeps_provider_identity(self):
        now = datetime.now(timezone.utc).isoformat()
        row = mod.normalized({"fear_and_greed": {"score":45, "rating":"neutral", "timestamp":now,
          "previous_close":45, "previous_1_week":46, "previous_1_month":32, "previous_1_year":29}})
        self.assertEqual(row["source"], "cnn")
        self.assertEqual(row["score"], 45)
        self.assertEqual(row["previous_1_year"], 29)

    def test_invalid_and_stale_data_fail_closed(self):
        with self.assertRaises(ValueError):
            mod.normalized({"fear_and_greed":{"score":None}})
        with self.assertRaises(ValueError):
            mod.normalized({"fear_and_greed":{"score":67,"timestamp":"2020-01-01T12:00:00Z"}})

    def test_three_indicators_are_not_blended(self):
        js = (ROOT / "dashboard-market-sentiment.js").read_text(encoding="utf-8")
        self.assertIn("CNN BUSINESS · FEAR & GREED INDEX", js)
        self.assertIn("data/cnn-fear-greed.json", js)
        self.assertIn("AAII · RETAIL SENTIMENT", js)
        self.assertIn("MARKET SENTIMENT · VESTRA READ", js)
        self.assertIn("payload?.source!=='cnn'", js)
        self.assertIn("loadCnn();", js)

if __name__ == "__main__":
    unittest.main()
