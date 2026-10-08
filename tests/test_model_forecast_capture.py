import json
import tempfile
import unittest
from pathlib import Path
from scripts.model_forecast_capture import append_forecast

FORECAST = dict(model_id="quality", model_version="1", prediction_id="p1",
                ticker="ABC", issued_at="2026-01-01T00:00:00Z",
                horizon_end="2026-04-01T00:00:00Z",
                probability_up=0.7, split="out_of_sample")
NOW = "2026-01-02T00:00:00Z"


class ForecastCaptureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "forecasts.jsonl"

    def test_append_and_duplicate_rejection(self):
        first = append_forecast(self.path, dict(FORECAST), NOW)
        self.assertEqual(first["previous_hash"], "0" * 64)
        with self.assertRaisesRegex(ValueError, "duplicate prediction"):
            append_forecast(self.path, dict(FORECAST), NOW)
        second = append_forecast(self.path, dict(FORECAST, prediction_id="p2"), NOW)
        self.assertEqual(second["previous_hash"], first["hash"])
        self.assertEqual(len(self.path.read_text().splitlines()), 2)

    def test_future_or_expired_forecast_rejected(self):
        with self.assertRaisesRegex(ValueError, "not live"):
            append_forecast(self.path, dict(FORECAST, issued_at="2027-01-01T00:00:00Z"), NOW)
        with self.assertRaisesRegex(ValueError, "not live"):
            append_forecast(self.path, dict(FORECAST, horizon_end="2026-01-01T12:00:00Z"), NOW)

    def test_tampering_rejected(self):
        append_forecast(self.path, dict(FORECAST), NOW)
        event = json.loads(self.path.read_text().strip())
        event["forecast"]["probability_up"] = 0.1
        self.path.write_text(json.dumps(event) + "\n")
        with self.assertRaisesRegex(ValueError, "integrity failure"):
            append_forecast(self.path, dict(FORECAST, prediction_id="p2"), NOW)

    def test_invalid_probability_rejected(self):
        with self.assertRaisesRegex(ValueError, "invalid probability"):
            append_forecast(self.path, dict(FORECAST, probability_up=True), NOW)


if __name__ == "__main__":
    unittest.main()
