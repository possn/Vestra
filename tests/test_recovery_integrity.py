"""Recovery classification must not manufacture momentum from broken OHLCV."""
import unittest
from datetime import datetime, timedelta, timezone

from scripts import recovery_confirmation as recovery


def equity(history, **fields):
    return {
        "quote_type": "EQUITY",
        "price_history_1y": history,
        "risk_gate": "clear",
        "estimate_signal": "improving",
        "thesis_direction": "up",
        "drawdown_driver_trend": "improving",
        **fields,
    }


class RecoveryIntegrityTests(unittest.TestCase):
    def test_complete_61_sessions_can_be_evaluated(self):
        row = equity([100 + i * .3 for i in range(65)])
        self.assertNotEqual(recovery.assess(row)["recovery_status"], "insufficient")

    def test_full_year_dated_weekly_closes_use_distinct_weekly_horizons(self):
        end=datetime.now(timezone.utc).date()-timedelta(days=2)
        history=[{"date":(end-timedelta(days=7*(52-i))).isoformat(),
                  "close":100+i*.35} for i in range(53)]
        result=recovery.assess(equity(history))
        self.assertNotEqual(result["recovery_status"],"insufficient")
        self.assertEqual(result["recovery_price_basis"],"dated_weekly_closes_4_12_weeks")
        self.assertEqual(result["recovery_observed_last_session"],end.isoformat())
        self.assertIsNotNone(result["recovery_return_4w_pct"])
        self.assertIsNotNone(result["recovery_return_12w_pct"])
        self.assertIsNone(result["recovery_return_20d_pct"])
        self.assertIsNone(result["recovery_return_60d_pct"])

    def test_short_undated_and_sparse_weekly_histories_cannot_confirm(self):
        end=datetime.now(timezone.utc).date()-timedelta(days=2)
        cases=[[100+i*.35 for i in range(53)],
               [{"date":(end-timedelta(days=7*(35-i))).isoformat(),"close":100+i*.35}
                for i in range(36)],
               [{"date":(end-timedelta(days=14*(50-i))).isoformat(),"close":100+i*.35}
                for i in range(51)]]
        for history in cases:
            with self.subTest(n=len(history)):
                self.assertEqual(recovery.assess(equity(history))["recovery_status"],"insufficient")

    def test_missing_nan_inf_boolean_and_bad_prices_are_not_dropped(self):
        base = [100 + i * .3 for i in range(65)]
        for bad in (None, float("nan"), float("inf"), True, False, 0, -1, "not-a-price"):
            with self.subTest(bad=repr(bad)):
                bars = base[:]
                bars[25] = bad
                result = recovery.assess(equity(bars))
                self.assertEqual(result["recovery_status"], "insufficient")
                self.assertIsNone(result["recovery_score"])

    def test_partial_60_session_window_never_confirms_recovery(self):
        row = equity([100 + i * .3 for i in range(60)])
        self.assertEqual(recovery.assess(row)["recovery_status"], "insufficient")

    def test_unknown_risk_gate_never_defaults_to_clear(self):
        row = equity([100 + i * .3 for i in range(65)], risk_gate=None)
        result = recovery.assess(row)
        self.assertEqual(result["recovery_status"], "insufficient")
        self.assertIsNone(result["recovery_score"])

    def test_high_risk_blocks_recovery(self):
        row = equity([100 + i * .3 for i in range(65)], risk_gate="high")
        self.assertEqual(recovery.assess(row)["recovery_status"], "failed")

    def test_non_equities_are_excluded(self):
        for quote_type in ("FUND", "CRYPTOCURRENCY", "ETF", "MUTUALFUND"):
            self.assertEqual(recovery.assess(equity([100] * 65, quote_type=quote_type)), {})


if __name__ == "__main__":
    unittest.main()
