import copy
import math
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from market_turning_feature_lab import (
    rsi, mfi, series, feature_row, future_reversal_labels, lab_report,
)


class TurningFeatureLabTests(unittest.TestCase):
    def fixture(self):
        days = []
        current = date(2024, 1, 2)
        while len(days) < 420:
            if current.weekday() < 5:
                days.append(current.isoformat())
            current += timedelta(days=1)
        spy = []
        vix = []
        cor = []
        for i, day in enumerate(days):
            price = 120 + i * 0.06 + 3 * math.sin(i / 11)
            spy.append({"date": day, "close": price,
                        "high": price + 0.9, "low": price - 0.9,
                        "volume": 200000 + 100 * i})
            vix.append({"date": day, "close": 15 + 2 * math.cos(i / 8)})
            cor.append({"date": day, "close": 15 + 5 * math.sin(i / 18)})
        return {"SPY": spy, "^VIX": vix, "^VVIX": copy.deepcopy(vix),
                "^COR1M": cor, "^VIX3M": copy.deepcopy(vix),
                "HYG": copy.deepcopy(spy), "LQD": copy.deepcopy(spy)}

    def test_daily_weekly_mfi_genuine_ohlcv_and_causal(self):
        source = self.fixture()
        histories = {name: series(source, name) for name in source}
        asof = histories["SPY"][320]["date"]
        before = feature_row(histories, asof)
        self.assertIsInstance(before["rsi_daily_5"], float)
        self.assertIsInstance(before["rsi_daily_14"], float)
        self.assertIsInstance(before["rsi_weekly_14"], float)
        self.assertIsInstance(before["mfi_daily_14"], float)
        self.assertIsInstance(before["vix_percentile_126"], float)
        self.assertIsInstance(before["cor1m_percentile_126"], float)
        self.assertAlmostEqual(before["vix_1m_3m_ratio"], 1.0)
        # Data strictly after the as-of session must not change inputs.
        later = copy.deepcopy(histories)
        for row in later["SPY"][321:]:
            row["close"] *= 30
            row["high"] = row["close"] + 1
            row["low"] = row["close"] - 1
        for row in later["^COR1M"][321:]:
            row["close"] = 90
        self.assertEqual(before, feature_row(later, asof))

    def test_missing_volume_or_stale_options_never_becomes_a_number(self):
        raw = self.fixture()
        histories = {name: series(raw, name) for name in raw}
        asof = histories["SPY"][-1]["date"]
        histories["SPY"][-1].pop("volume")
        histories["^COR1M"] = histories["^COR1M"][:-1]
        result = feature_row(histories, asof)
        self.assertIsNone(result["mfi_daily_14"])
        self.assertIsNone(result["cor1m_percentile_126"])
        self.assertIsNotNone(result["rsi_daily_14"])

    def test_no_future_outcome_is_reported_as_failure(self):
        raw = self.fixture()
        spy = raw["SPY"]
        self.assertEqual(future_reversal_labels(spy, len(spy) - 1),
                         {"bottom": None, "top": None})
        report = lab_report(raw)
        self.assertTrue(report["research_only"])
        self.assertFalse(report["probability_calibrated"])
        self.assertIsNone(report["model_probability"])
        self.assertFalse(report["holdout"]["evaluated"])
        self.assertEqual(report["sample"]["rows"], len(spy) - 125)
        self.assertEqual(report["feature_coverage"]["mfi_daily_14"]["observed"],
                         len(spy) - 125)
        self.assertEqual(report["event_counts_descriptive_not_independent"]["bottom"]["matured"],
                         len(spy) - 125 - 20)
        self.assertTrue(report["feature_correlations_descriptive_not_validation"])
        self.assertIn("bottom", report["outcome_associations_in_sample_exploratory"])
        self.assertIn("top", report["outcome_associations_in_sample_exploratory"])
        # Even if every market factor correlates perfectly, the lab never
        # publishes or returns a live probability.
        self.assertFalse(report["score_or_live_vote_changed"])

    def test_duplicate_dates_and_future_revisions_are_rejected_or_isolated(self):
        raw = self.fixture()
        bad = copy.deepcopy(raw)
        bad["SPY"].insert(10, copy.deepcopy(bad["SPY"][9]))
        with self.assertRaises(ValueError):
            lab_report(bad)
        future = copy.deepcopy(raw)
        asof = raw["SPY"][300]["date"]
        initial = feature_row({k: series(v, k) for k, v in raw.items()}, asof)
        future["SPY"][-1]["close"] *= 5
        revised = feature_row({k: series(v, k) for k, v in future.items()}, asof)
        self.assertEqual(initial, revised)

    def test_rsi_mfi_initializations_are_undistorted(self):
        self.assertEqual(rsi([3] * 20), 50)
        self.assertEqual(rsi(list(range(20))), 100)
        self.assertEqual(rsi(list(range(20, 0, -1))), 0)
        self.assertIsNone(mfi([{"date": "2026-01-01", "close": 100}] * 14))


if __name__ == "__main__":
    unittest.main()
