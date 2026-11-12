"""Stale dated daily bars must not confirm a current recovery."""
import unittest
from datetime import datetime, timedelta, timezone

from scripts.recovery_confirmation import assess


def row(dates):
    return {
        "ticker": "REC", "quote_type": "EQUITY", "risk_gate": "clear",
        "estimate_signal": "improving", "thesis_direction": "up",
        "drawdown_driver_trend": "improving",
        "price_history_1y": [
            {"date": day.isoformat(), "close": 100 + 0.3 * i}
            for i, day in enumerate(dates)
        ],
    }


class RecoveryDatedFreshnessTests(unittest.TestCase):
    def setUp(self):
        today = datetime.now(timezone.utc).date()
        self.days = [today - timedelta(days=i) for i in range(64, -1, -1)]

    def test_current_dated_series_is_evaluable(self):
        self.assertIn(assess(row(self.days))["recovery_status"],
                      ("confirmed", "recovering", "stabilizing", "unconfirmed"))

    def test_stale_dates_do_not_confirm_recovery(self):
        dates = [day - timedelta(days=12) for day in self.days]
        result = assess(row(dates))
        self.assertEqual(result["recovery_status"], "insufficient")
        self.assertIsNone(result["recovery_score"])

    def test_duplicate_or_unordered_sessions_are_not_compressed(self):
        for mode in ("duplicate", "reverse"):
            dates = self.days[:]
            if mode == "duplicate":
                dates[20] = dates[19]
            else:
                dates[20], dates[21] = dates[21], dates[20]
            with self.subTest(mode=mode):
                self.assertEqual(assess(row(dates))["recovery_status"], "insufficient")

    def test_partial_dates_and_future_session_fail_closed(self):
        payload = row(self.days)
        del payload["price_history_1y"][4]["date"]
        self.assertEqual(assess(payload)["recovery_status"], "insufficient")
        future = [day + timedelta(days=9) for day in self.days]
        self.assertEqual(assess(row(future))["recovery_status"], "insufficient")


if __name__ == "__main__":
    unittest.main()
