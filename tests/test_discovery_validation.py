"""Contract tests for descriptive Discovery validation (synthetic fixtures only)."""
import unittest

from scripts.discovery_validation import evaluate


def fixture(date, ticker, score, ret, benchmark=2, **overrides):
    row = {
        "snapshot_date": date,
        "signal_asof": date,
        "ticker": ticker,
        "opportunity_score": str(score),
        "eligible": "true",
        "horizon_sessions": "20",
        "outcome_asof": "2026-04-30",
        "forward_total_return_pct": str(ret),
        "benchmark_total_return_pct": str(benchmark),
    }
    row.update(overrides)
    return row


class DiscoveryValidationTests(unittest.TestCase):
    def example(self):
        return [
            fixture("2026-01-02", "A", 95, 12),
            fixture("2026-01-02", "B", 80, 6),
            fixture("2026-01-02", "C", 60, -2),
            fixture("2026-01-02", "D", 40, 0),
            fixture("2026-02-02", "A", 92, 8),
            fixture("2026-02-02", "B", 81, 4),
            fixture("2026-02-02", "C", 61, -1),
            fixture("2026-02-02", "D", 42, 1),
        ]

    def test_no_real_performance_claim_without_multiple_dates(self):
        result = evaluate(self.example()[:4])
        self.assertEqual(result["status"], "insufficient_history")
        self.assertEqual(result["horizons"]["20"]["valid_dates"], 1)

    def test_top_quartile_is_measured_against_same_date_universe(self):
        result = evaluate(self.example())
        self.assertEqual(result["status"], "descriptive_only")
        self.assertEqual(result["horizons"]["20"]["valid_dates"], 2)
        self.assertAlmostEqual(result["horizons"]["20"]["top_minus_benchmark_pp"], 8)
        self.assertAlmostEqual(result["horizons"]["20"]["top_hit_rate"], 1.0)

    def test_future_signal_is_rejected(self):
        rows = self.example()
        rows[0]["signal_asof"] = "2026-01-03"
        with self.assertRaisesRegex(ValueError, "point-in-time"):
            evaluate(rows)

    def test_future_outcome_not_yet_realized_rejected(self):
        rows = self.example()
        rows[0]["outcome_asof"] = "2026-01-02"
        with self.assertRaisesRegex(ValueError, "point-in-time"):
            evaluate(rows)

    def test_duplicate_observation_is_rejected(self):
        rows = self.example()
        with self.assertRaisesRegex(ValueError, "duplicate"):
            evaluate(rows + [dict(rows[0])])

    def test_inconsistent_benchmark_is_rejected(self):
        rows = self.example()
        rows[0]["benchmark_total_return_pct"] = "3"
        with self.assertRaisesRegex(ValueError, "benchmark"):
            evaluate(rows)

    def test_nan_rejected(self):
        rows = self.example()
        rows[0]["opportunity_score"] = "nan"
        with self.assertRaisesRegex(ValueError, "Non-finite"):
            evaluate(rows)

    def test_ineligible_is_excluded_from_rank(self):
        rows = self.example()
        rows[0]["eligible"] = "false"
        result = evaluate(rows)
        self.assertEqual(result["horizons"]["20"]["valid_dates"], 1)
        self.assertEqual(result["status"], "insufficient_history")


if __name__ == "__main__":
    unittest.main()
