import unittest

from scripts.low52_intelligence import assess


def quality_row(current_price=105.0):
    return {
        "ticker": "TEST",
        "quote_type": "EQUITY",
        "current_price": current_price,
        "price_history_1y": [100.0] * 218 + [120.0, 150.0],
        "score": 80,
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


class Low52IntelligenceTests(unittest.TestCase):
    def test_unrecognized_reliability_fails_closed(self):
        for reliability in (None, "", "unknown", "high", "insufficient",
                            "insufficient_data", "suppressed"):
            with self.subTest(reliability=reliability):
                row = quality_row(current_price=100.0)
                row["score_reliability"] = reliability
                result = assess(row)
                self.assertEqual(result["low52_status"], "insufficient")
                self.assertIsNone(result["low52_score"])

    def test_canonical_reliability_levels_remain_allowed(self):
        for reliability in ("robust", "moderate_evidence", "limited_evidence"):
            with self.subTest(reliability=reliability):
                row = quality_row(current_price=100.0)
                row["score_reliability"] = reliability
                self.assertNotEqual(assess(row)["low52_status"], "insufficient")

    def test_short_close_history_cannot_claim_a_52week_opportunity(self):
        for length in (1, 3, 30, 199):
            with self.subTest(length=length):
                row = quality_row()
                row["price_history_1y"] = [100.0] * length
                row["fifty_two_week_low"] = 90.0
                row["fifty_two_week_high"] = 150.0
                result = assess(row)
                self.assertEqual(result["low52_status"], "insufficient")
                self.assertIsNone(result["low52_score"])

    def test_numpy_boolean_scalars_fail_closed_in_prices_and_scores(self):
        # Simulate both NumPy boolean scalar identities in stdlib-only CI.
        def scalar(name):
            return type(name, (), {
                "__module__": "numpy",
                "__init__": lambda self, value: setattr(self, "value", value),
                "__float__": lambda self: float(self.value),
            })

        for cls in (scalar("bool_"), scalar("bool")):
            for bad in (True, False):
                with self.subTest(dtype=cls.__name__, value=bad):
                    for field in ("score", "confidence_score", "data_coverage_pct",
                                  "critical_metric_coverage_pct", "current_price"):
                        row = quality_row(current_price=100.0)
                        row[field] = cls(bad)
                        result = assess(row)
                        self.assertEqual(result["low52_status"], "insufficient")
                        self.assertIsNone(result["low52_score"])
                    row = quality_row(current_price=100.0)
                    row["price_history_1y"][19] = cls(bad)
                    result = assess(row)
                    self.assertEqual(result["low52_status"], "insufficient")
                    self.assertIsNone(result["low52_score"])

    def test_boolean_daily_close_fails_closed_even_with_provider_extrema(self):
        for bad in (True, False):
            with self.subTest(close=bad):
                row = quality_row()
                row["price_history_1y"][17] = bad
                row["fifty_two_week_low"] = 100.0
                row["fifty_two_week_high"] = 150.0
                result = assess(row)
                self.assertEqual(result["low52_status"], "insufficient")
                self.assertIsNone(result["low52_score"])

        row = quality_row()
        row["price_history_1y"][17] = {"close": True}
        self.assertEqual(assess(row)["low52_status"], "insufficient")

    def test_observed_close_minimum_is_not_mislabeled_intraday_low(self):
        result = assess(quality_row())
        self.assertEqual(result["low52_price_basis"],
                         "observed_daily_closes_minimum_200_sessions")
        self.assertEqual(result["low52_observed_close_sessions"], 220)
        self.assertIn("fechos diários observados", result["low52_reasons"][0])

    def test_provider_extrema_keep_explicit_distinct_provenance(self):
        row = quality_row()
        row["price_history_1y"] = []
        row["fifty_two_week_low"] = 100.0
        row["fifty_two_week_high"] = 150.0
        result = assess(row)
        self.assertEqual(result["low52_price_basis"], "provider_reported_52week_extrema")
        self.assertEqual(result["low52_observed_close_sessions"], 0)
        self.assertIn("fornecedor", result["low52_reasons"][0])

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

    def test_missing_critical_metric_coverage_never_becomes_low52_opportunity(self):
        for missing in (None, ""):
            with self.subTest(coverage=missing):
                row = quality_row()
                row["critical_metric_coverage_pct"] = missing
                result = assess(row)
                self.assertEqual(result["low52_status"], "insufficient")
                self.assertIsNone(result["low52_score"])

    def test_nonfinite_and_boolean_evidence_does_not_create_low52_opportunity(self):
        for bad in (float("inf"), float("-inf"), float("nan"), True, False):
            with self.subTest(value=bad):
                for field in ("score", "data_coverage_pct", "confidence_score"):
                    row = quality_row()
                    row[field] = bad
                    result = assess(row)
                    self.assertEqual(result["low52_status"], "insufficient")
                    self.assertIsNone(result["low52_score"])

    def test_out_of_range_core_evidence_cannot_inflate_low52_opportunity(self):
        for field in ("score", "data_coverage_pct",
                      "critical_metric_coverage_pct", "confidence_score"):
            for value in (-0.01, 100.01, 1000, "-1", "101"):
                with self.subTest(field=field, value=value):
                    row = quality_row(current_price=100.0)
                    row[field] = value
                    result = assess(row)
                    self.assertEqual(result["low52_status"], "insufficient")
                    self.assertIsNone(result["low52_score"])
                    self.assertIn("Métricas fundamentais fora da escala 0–100",
                                  result["low52_reasons"])
        valid = quality_row(current_price=100.0)
        valid.update({"score": 100, "data_coverage_pct": 100,
                      "critical_metric_coverage_pct": 100, "confidence_score": 100})
        self.assertNotEqual(assess(valid)["low52_status"], "insufficient")

    def test_out_of_range_component_scores_cannot_inflate_low52(self):
        for field in ("quality_pct", "balance_pct", "cashflow_pct",
                      "execution_pct", "value_pct", "estimate_momentum_score"):
            for invalid in (-0.1, 100.1, 1000, "105"):
                with self.subTest(field=field, invalid=invalid):
                    row = quality_row(current_price=100.0)
                    row[field] = invalid
                    result = assess(row)
                    self.assertEqual(result["low52_status"], "insufficient")
                    self.assertIsNone(result["low52_score"])
                    self.assertIn("Dimensões de classificação fora da escala 0–100",
                                  result["low52_reasons"])
        row = quality_row(current_price=100.0)
        for field in ("quality_pct", "balance_pct", "cashflow_pct",
                      "execution_pct", "value_pct", "estimate_momentum_score"):
            row[field] = 100
        self.assertNotEqual(assess(row)["low52_status"], "insufficient")

    def test_infinite_resilience_metric_is_not_counted_as_quality(self):
        row = quality_row()
        row.update({"quality_pct": float("inf"), "balance_pct": float("inf"),
                    "cashflow_pct": float("inf"), "execution_pct": float("inf")})
        result = assess(row)
        self.assertEqual(result["low52_status"], "insufficient")
        self.assertIsNone(result["low52_score"])

    def test_missing_risk_gate_cannot_be_inferred_clear(self):
        for missing in (None, "", "unknown"):
            with self.subTest(missing=missing):
                row = quality_row()
                row["risk_gate"] = missing
                result = assess(row)
                self.assertEqual(result["low52_status"], "insufficient")
                self.assertIsNone(result["low52_score"])
                self.assertIn("Risk Gate sem avaliação conclusiva", result["low52_reasons"])

    def test_missing_capital_structure_risk_cannot_create_opportunity(self):
        row = quality_row()
        row.pop("capital_structure_risk")
        result = assess(row)
        self.assertEqual(result["low52_status"], "insufficient")
        self.assertIsNone(result["low52_score"])

    def test_malformed_risk_flags_cannot_clear_severe_dilution(self):
        baseline = quality_row(current_price=100.0)
        baseline["capital_structure_flags"] = ["severe_dilution"]
        self.assertEqual(assess(baseline)["low52_status"], "structural_risk")
        for field in ("risk_flags", "capital_structure_flags"):
            for invalid in ("severe_dilution", {"severe_dilution": True},
                            [None], [True], [["severe_dilution"]]):
                with self.subTest(field=field, invalid=invalid):
                    row = quality_row(current_price=100.0)
                    row[field] = invalid
                    result = assess(row)
                    self.assertEqual(result["low52_status"], "insufficient")
                    self.assertIsNone(result["low52_score"])
                    self.assertIn("Indicadores de risco malformados", result["low52_reasons"])
        # Explicit well-formed risk flags remain effective.
        for field in ("risk_flags", "capital_structure_flags"):
            row = quality_row(current_price=100.0)
            row[field] = ["severe_dilution"]
            self.assertEqual(assess(row)["low52_status"], "structural_risk")

    def test_severe_risk_gate_is_structural_risk_even_near_low(self):
        row = quality_row()
        row["risk_gate"] = "severe"
        result = assess(row)
        self.assertEqual(result["low52_status"], "structural_risk")
        self.assertGreaterEqual(result["low52_deterioration_penalty"], 35)

    def test_high_capital_structure_risk_cannot_become_opportunity(self):
        for capital_risk, flags in (("high", []), ("severe", []),
                                    ("clear", ["severe_dilution"])):
            with self.subTest(capital_risk=capital_risk, flags=flags):
                row = quality_row(current_price=100.0)
                row.update({
                    "score": 100, "quality_pct": 100, "balance_pct": 100,
                    "cashflow_pct": 100, "execution_pct": 100,
                    "confidence_score": 100, "estimate_momentum_score": 100,
                    "value_pct": 100, "margin_of_safety_pct": 100,
                    "capital_structure_risk": capital_risk,
                    "capital_structure_flags": flags,
                })
                result = assess(row)
                self.assertEqual(result["low52_status"], "structural_risk")
                self.assertGreater(result["low52_score"], 70)

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

    def test_corrupt_history_fails_closed_even_with_valid_fallback_extrema(self):
        for corrupt in (None, "broken", 0, -10, float("nan"), float("inf")):
            with self.subTest(corrupt=corrupt):
                row = quality_row()
                row["price_history_1y"] = [100.0, corrupt, 150.0]
                row["fifty_two_week_low"] = 100.0
                row["fifty_two_week_high"] = 150.0
                result = assess(row)
                self.assertEqual(result["low52_status"], "insufficient")
                self.assertIsNone(result["low52_score"])

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
