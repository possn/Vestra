"""Fail-closed evidence contracts for background insider and near-low alerts."""
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location(
    "insider_alerts", ROOT / "scripts" / "insider_alerts.py")
alerts = importlib.util.module_from_spec(spec)
# Architecture CI intentionally uses stdlib-only Python. Isolate transport and
# SEC client imports: these tests exercise pure evidence logic, not networking.
stub_insiders = types.ModuleType("insiders")
for name in ("_fetch_structured_filing", "_load_ticker_cik_map",
             "_recent_form4_rows"):
    setattr(stub_insiders, name, lambda *args, **kwargs: None)
with patch.dict(sys.modules, {
        "requests": types.ModuleType("requests"), "insiders": stub_insiders}):
    spec.loader.exec_module(alerts)


class InsiderAlertEvidenceTests(unittest.TestCase):
    @staticmethod
    def quality_row(hist=None, current=100):
        return {
            "ticker": "ABC", "quote_type": "EQUITY",
            "score": 80, "current_price": current,
            "price_history_1y": hist if hist is not None else
                [{"close": 100} for _ in range(220)],
            "thesis_direction": "stable",
            "data_coverage_pct": 80,
            "critical_metric_coverage_pct": 70,
            "confidence_score": 80,
            "score_reliability": "robust",
            "quality_pct": 75,
            "balance_pct": 70,
            "cashflow_pct": 70,
            "execution_pct": 70,
            "value_pct": 70,
            "margin_of_safety_pct": 15,
            "estimate_momentum_score": 70,
            "estimate_signal": "improving",
            "risk_gate": "clear",
            "valuation_signal": "undervalued",
            "capital_structure_risk": "clear",
            "risk_flags": [],
            "capital_structure_flags": [],
        }

    def candidates(self, row):
        with patch.object(alerts, "_load_json", return_value={"stocks": [row]}):
            return alerts._near_low_candidates()

    def test_low52_alert_refuses_missing_or_weak_evidence(self):
        for field, invalid in (
            ("data_coverage_pct", None),
            ("critical_metric_coverage_pct", 30),
            ("confidence_score", 10),
            ("score_reliability", "unknown"),
            ("risk_gate", "unknown"),
            ("capital_structure_risk", "unknown"),
            ("quality_pct", float("nan")),
        ):
            with self.subTest(field=field):
                row = self.quality_row()
                row[field] = invalid
                self.assertNotIn("ABC", self.candidates(row))

    def test_wider_15pct_alert_band_requires_watch_grade_resilience(self):
        valid = self.quality_row(current=112)
        self.assertTrue(self.candidates(valid)["ABC"]["in_zone"])
        risk = self.quality_row(current=112)
        risk["risk_gate"] = "high"
        self.assertNotIn("ABC", self.candidates(risk))
        dilution = self.quality_row(current=112)
        dilution["risk_flags"] = ["severe_dilution"]
        self.assertNotIn("ABC", self.candidates(dilution))
        distant = self.quality_row(current=116)
        self.assertNotIn("ABC", self.candidates(distant))

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
            return self.quality_row(hist=hist)
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
