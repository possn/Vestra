#!/usr/bin/env python3
"""Synthetic regression contract for missing-horizon coverage."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from prebreakout_forward_evaluation import aggregate, evaluate


class MissingHorizonCoverageTests(unittest.TestCase):
    def test_no_future_session_stays_in_denominator(self):
        bars = [{"date": "2026-10-20", "close": 100.0}]
        missing = evaluate({"date": "2026-10-20", "ticker": "A"}, bars, bars, (5,))
        self.assertEqual(missing["results"], {})
        observed = {"ticker": "B", "results": {5: {
            "return": 0.1, "excess_return": 0.05, "max_adverse_excursion": -0.02
        }}}
        result = aggregate([missing, observed], (5,))[5]
        self.assertEqual(result["n"], 1)
        self.assertEqual(result["n_missing"], 1)
        self.assertEqual(result["hit_rate"], 1.0)

    def test_all_missing_stays_visible_without_performance_metrics(self):
        result = aggregate([{"results": {}}, {"results": {5: None}}], (5,))[5]
        self.assertEqual(result, {"n": 0, "n_missing": 2})

    def test_empty_cohort_is_not_misreported_as_observations(self):
        self.assertEqual(aggregate([], (5,))[5], {"n": 0, "n_missing": 0})

    def test_generator_is_consumed_once_across_horizons(self):
        source = ({"results": {5: None, 10: None}} for _ in range(3))
        result = aggregate(source, (5, 10))
        self.assertEqual(result[5]["n_missing"], 3)
        self.assertEqual(result[10]["n_missing"], 3)

    def test_malformed_missing_results_fails_closed(self):
        with self.assertRaises(ValueError):
            aggregate([{"ticker": "A"}], (5,))


if __name__ == "__main__":
    unittest.main()
