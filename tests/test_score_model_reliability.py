import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("vestra_confidence_model_gate", ROOT / "scripts" / "confidence.py")
mod = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(mod)


class ScoreModelReliabilityTests(unittest.TestCase):
    def test_general_model_keeps_existing_critical_contract(self):
        row = {key: 1.0 for key in mod._CRITICAL_GENERAL}
        row["score_model"] = "general"
        pct, model, count = mod._critical_coverage(row)
        self.assertEqual(model, "general")
        self.assertEqual(count, len(mod._CRITICAL_GENERAL))
        self.assertEqual(pct, 100.0)

    def test_bank_gate_uses_bank_native_evidence_not_generic_liquidity(self):
        fields = mod._CRITICAL_BY_MODEL["bank"]
        row = {key: 1.0 for key in fields}
        row.update({
            "score_model": "bank",
            "current_ratio": None,
            "enterprise_to_ebitda": None,
            "gross_margin": None,
        })
        pct, model, count = mod._critical_coverage(row)
        self.assertEqual(model, "bank")
        self.assertEqual(count, len(fields))
        self.assertEqual(pct, 100.0)

    def test_missing_bank_asset_quality_now_reduces_reliability_coverage(self):
        fields = mod._CRITICAL_BY_MODEL["bank"]
        row = {key: 1.0 for key in fields}
        row["score_model"] = "bank"
        row["provision_to_revenue"] = None
        pct, _, _ = mod._critical_coverage(row)
        self.assertLess(pct, 100.0)
        self.assertAlmostEqual(pct, (len(fields) - 1) / len(fields) * 100.0)

    def test_biotech_gate_does_not_require_generic_pe_multiples(self):
        fields = mod._CRITICAL_BY_MODEL["biotech"]
        row = {key: 1.0 for key in fields}
        row.update({
            "score_model": "biotech",
            "trailing_pe": None,
            "forward_pe": None,
            "enterprise_to_ebitda": None,
            "price_to_book": None,
        })
        pct, model, _ = mod._critical_coverage(row)
        self.assertEqual(model, "biotech")
        self.assertEqual(pct, 100.0)

    def test_non_positive_model_valuation_placeholder_is_missing(self):
        fields = mod._CRITICAL_BY_MODEL["reit"]
        row = {key: 1.0 for key in fields}
        row["score_model"] = "reit"
        row["reit_p_ffo_proxy"] = 0
        pct, _, _ = mod._critical_coverage(row)
        self.assertAlmostEqual(pct, (len(fields) - 1) / len(fields) * 100.0)

    def test_assess_emits_model_aware_gate_metadata(self):
        row = {
            "ticker": "TEST",
            "quote_type": "EQUITY",
            "score_model": "biotech",
            "score": 80,
            "data_coverage_pct": 90,
            "data_sources": ["Yahoo Finance"],
        }
        row.update({key: 1.0 for key in mod._CRITICAL_BY_MODEL["biotech"]})
        out = mod.assess(row)
        self.assertEqual(out["critical_metric_model"], "biotech")
        self.assertEqual(out["critical_metric_field_count"], len(mod._CRITICAL_BY_MODEL["biotech"]))
        self.assertEqual(out["critical_metric_coverage_pct"], 100.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
