import unittest

from scripts.low52_intelligence import assess


def quality_row(current_price=105.0):
    return {
        "ticker": "TEST",
        "quote_type": "EQUITY",
        "current_price": current_price,
        "price_history_1y": [100.0, 120.0, 150.0],
        "score": 80,
        "data_coverage_pct": 80,
        "critical_metric_coverage_pct": 70,
        "confidence_score": 80,
        "score_reliability": "high",
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


class Low52IntelligenceTests(unittest.TestCase):
    def test_etfs_are_excluded_from_low52_equity_intelligence(self):
        row = quality_row()
        row["quote_type"] = "ETF"
        self.assertEqual(assess(row), {})

    def test_exact_ten_percent_above_low_remains_inside_intelligence_zone(self):
        result = assess(quality_row(current_price=110.0))
        self.assertAlmostEqual(result["low52_above_low_pct"], 10.0, places=2)
        self.assertNotEqual(result["low52_status"], "not_near_low")

    def test_more_than_ten_percent_above_low_is_outside_intelligence_zone(self):
        result = assess(quality_row(current_price=110.01))
        self.assertGreater(result["low52_above_low_pct"], 10.0)
        self.assertEqual(result["low52_status"], "not_near_low")

    def test_low_fundamental_coverage_never_becomes_opportunity(self):
        row = quality_row()
        row["data_coverage_pct"] = 54.9
        result = assess(row)
        self.assertEqual(result["low52_status"], "insufficient")
        self.assertIsNone(result["low52_score"])
        self.assertIn("Cobertura fundamental inferior a 55%", result["low52_reasons"])

    def test_severe_risk_gate_is_structural_risk_even_near_low(self):
        row = quality_row()
        row["risk_gate"] = "severe"
        result = assess(row)
        self.assertEqual(result["low52_status"], "structural_risk")
        self.assertGreaterEqual(result["low52_deterioration_penalty"], 35)

    def test_weak_resilience_is_value_trap_risk(self):
        row = quality_row()
        row.update({
            "score": 65,
            "confidence_score": 60,
            "quality_pct": 40,
            "balance_pct": 40,
            "cashflow_pct": 40,
            "execution_pct": 40,
            "valuation_signal": "fair",
            "margin_of_safety_pct": 0,
            "estimate_momentum_score": 50,
            "estimate_signal": "stable",
        })
        result = assess(row)
        self.assertLess(result["low52_resilience_score"], 48)
        self.assertEqual(result["low52_status"], "value_trap_risk")

    def test_high_quality_near_low_can_be_opportunity(self):
        result = assess(quality_row())
        self.assertEqual(result["low52_status"], "opportunity")
        self.assertGreaterEqual(result["low52_score"], 70)
        self.assertGreaterEqual(result["low52_resilience_score"], 62)

    def test_explicit_52_week_extrema_are_valid_fallback_without_history(self):
        row = quality_row()
        row["price_history_1y"] = []
        row["fifty_two_week_low"] = 100
        row["fifty_two_week_high"] = 150
        row["current_price"] = 105
        result = assess(row)
        self.assertNotEqual(result["low52_status"], "insufficient")
        self.assertEqual(result["low52_price_low"], 100)
        self.assertEqual(result["low52_price_high"], 150)
        self.assertAlmostEqual(result["low52_above_low_pct"], 5.0, places=2)

    def test_invalid_explicit_extrema_do_not_create_false_signal(self):
        row = quality_row()
        row["price_history_1y"] = []
        row["fifty_two_week_low"] = 150
        row["fifty_two_week_high"] = 100
        result = assess(row)
        self.assertEqual(result["low52_status"], "insufficient")
        self.assertIsNone(result["low52_score"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
