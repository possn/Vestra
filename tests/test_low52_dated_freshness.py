"""Dated 52-week histories must be ordered and fresh before ranking."""
import unittest
from datetime import datetime, timedelta, timezone
from scripts.low52_intelligence import assess


def quality_history(dates):
    return {
        "ticker": "DATED", "quote_type": "EQUITY", "current_price": 100,
        "price_history_1y": [
            {"date": day.isoformat(), "close": 100.0} for day in dates
        ],
        "score": 80, "data_coverage_pct": 80,
        "critical_metric_coverage_pct": 70, "confidence_score": 80,
        "score_reliability": "robust", "quality_pct": 75,
        "balance_pct": 70, "cashflow_pct": 70, "execution_pct": 70,
        "value_pct": 70, "margin_of_safety_pct": 15,
        "estimate_momentum_score": 70, "estimate_signal": "improving",
        "risk_gate": "clear", "valuation_signal": "undervalued",
        "capital_structure_risk": "clear", "risk_flags": [],
        "capital_structure_flags": [],
    }


class DatedLow52IntegrityTests(unittest.TestCase):
    def setUp(self):
        today = datetime.now(timezone.utc).date()
        self.dates = [today - timedelta(days=i) for i in range(219, -1, -1)]

    def test_recent_ordered_history_is_assessable(self):
        result = assess(quality_history(self.dates))
        self.assertNotEqual(result["low52_status"], "insufficient")
        self.assertEqual(result["low52_observed_last_session"], self.dates[-1].isoformat())

    def test_stale_last_session_is_not_a_current_low(self):
        stale = [d - timedelta(days=14) for d in self.dates]
        result = assess(quality_history(stale))
        self.assertEqual(result["low52_status"], "insufficient")
        self.assertIsNone(result["low52_score"])

    def test_duplicate_or_unordered_sessions_are_rejected(self):
        for modification in ("duplicate", "reverse"):
            with self.subTest(modification=modification):
                dates = self.dates[:]
                if modification == "duplicate": dates[110] = dates[109]
                else: dates[110], dates[111] = dates[111], dates[110]
                self.assertEqual(assess(quality_history(dates))["low52_status"], "insufficient")

    def test_partial_date_provenance_fails_closed(self):
        row = quality_history(self.dates)
        del row["price_history_1y"][2]["date"]
        self.assertEqual(assess(row)["low52_status"], "insufficient")

    def test_invalid_future_session_fails_closed(self):
        dates = self.dates[:]
        shift = timedelta(days=8)
        dates = [d + shift for d in dates]
        self.assertEqual(assess(quality_history(dates))["low52_status"], "insufficient")


if __name__ == "__main__":
    unittest.main()
