"""Fail-closed evidence contracts for background insider and near-low alerts."""
import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location(
    "insider_alerts", ROOT / "scripts" / "insider_alerts.py")
alerts = importlib.util.module_from_spec(spec)
spec.loader.exec_module(alerts)


class InsiderAlertEvidenceTests(unittest.TestCase):
    def test_group_ignores_nan_infinity_boolean_negative_and_overflow(self):
        transactions = [
            {"type": "buy", "owner": "Director", "date": "2026-11-10",
             "shares": 10, "value": 2000, "price": 20},
            {"type": "buy", "owner": "Director", "date": "2026-11-10",
             "shares": float("nan"), "value": float("inf"), "price": float("nan")},
            {"type": "buy", "owner": "Director", "date": "2026-11-10",
             "shares": True, "value": -200, "price": False},
            {"type": "buy", "owner": "Director", "date": "2026-11-10",
             "shares": float("inf"), "value": 1e308, "price": -1},
            {"type": "buy", "owner": "Director", "date": "2026-11-10",
             "value": 1e308},
        ]
        group = alerts._group_transactions(transactions)[0]
        self.assertEqual(group["shares"], 10)
        self.assertEqual(group["value"], 1e308)
        self.assertEqual(group["prices"], [20])
        self.assertTrue(group["known_value"])

    def test_unknown_amount_stays_unknown_not_zero_evidence(self):
        group = alerts._group_transactions([
            {"type": "buy", "owner": "A", "value": float("nan"),
             "shares": True, "price": float("inf")}])[0]
        self.assertFalse(group["known_value"])
        self.assertFalse(group["known_shares"])
        self.assertEqual(group["prices"], [])

    def test_near_low_requires_200_finite_positive_closes(self):
        def row(hist):
            return {"ticker": "ABC", "score": 80, "current_price": 100,
                    "price_history_1y": hist, "thesis_direction": "stable"}
        good = [dict(close=100) for _ in range(220)]
        with patch.object(alerts, "_load_json", return_value={"stocks": [row(good)]}):
            self.assertTrue(alerts._near_low_candidates()["ABC"]["in_zone"])
        for history in ([{"close": 100}] * 3,
                        good[:10] + [{"close": float("nan")}] + good[11:],
                        good[:10] + [{"close": False}] + good[11:],
                        good[:10] + [{"close": 0}] + good[11:]):
            with self.subTest(history=history[10:11]):
                with patch.object(alerts, "_load_json",
                                  return_value={"stocks": [row(history)]}):
                    self.assertNotIn("ABC", alerts._near_low_candidates())

    def test_nonfinite_current_price_never_enters_price_alert_map(self):
        with patch.object(alerts, "_load_json", return_value={"stocks": [
            {"ticker": "GOOD", "current_price": 20},
            {"ticker": "BAD", "current_price": float("inf")},
            {"ticker": "NAN", "current_price": float("nan")}] }):
            self.assertEqual(alerts._current_price_map(), {"GOOD": 20})


if __name__ == "__main__":
    unittest.main()
