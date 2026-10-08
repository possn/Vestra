import unittest
from scripts.model_evidence_ledger import evaluate


BASE = dict(model_id="quality", model_version="1", ticker="ABC",
            prediction_id="p1", issued_at="2025-01-01T00:00:00Z",
            horizon_end="2025-04-01T00:00:00Z",
            outcome_observed_at="2025-04-02T00:00:00Z",
            probability_up=0.8, realized_up=True, split="out_of_sample")


class LedgerTests(unittest.TestCase):
    def test_no_data_is_unavailable(self):
        result = evaluate([], "2026-01-01T00:00:00Z")
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["models"], {})

    def test_brier_and_small_sample(self):
        result = evaluate([BASE], "2026-01-01T00:00:00Z")
        self.assertEqual(result["models"]["quality"]["brier"], 0.04)
        self.assertEqual(result["models"]["quality"]["status"], "observed_insufficient_sample")

    def test_duplicate_prediction_not_double_counted(self):
        result = evaluate([BASE, dict(BASE)], "2026-01-01T00:00:00Z")
        self.assertEqual(result["eligible_count"], 1)
        self.assertEqual(result["rejected"]["duplicate_prediction"], 1)

    def test_no_lookahead(self):
        future = dict(BASE, outcome_observed_at="2027-01-01T00:00:00Z")
        result = evaluate([future], "2026-01-01T00:00:00Z")
        self.assertEqual(result["eligible_count"], 0)
        self.assertEqual(result["rejected"]["non_point_in_time"], 1)

    def test_no_in_sample_or_fake_probabilities(self):
        sample = dict(BASE, split="in_sample")
        invalid = dict(BASE, probability_up=True)
        result = evaluate([sample, invalid], "2026-01-01T00:00:00Z")
        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["rejected"]["not_out_of_sample"], 1)
        self.assertEqual(result["rejected"]["invalid_probability"], 1)


if __name__ == "__main__":
    unittest.main()
