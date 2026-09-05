import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("vestra_confidence", ROOT / "scripts" / "confidence.py")
mod = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(mod)


def rich_row(**extra):
    row = {
        "ticker": "TEST",
        "quote_type": "EQUITY",
        "data_coverage_pct": 90,
        "score": 82,
        "data_sources": ["Yahoo Finance", "Analyst feed"],
        "roe": 0.2,
        "roa": 0.1,
        "profit_margin": 0.2,
        "operating_margin": 0.2,
        "gross_margin": 0.5,
        "revenue_growth": 0.1,
        "earnings_growth": 0.1,
        "free_cash_flow": 100,
        "operating_cash_flow": 120,
        "current_ratio": 1.5,
        "debt_to_equity": 0.5,
        "trailing_pe": 20,
        "forward_pe": 18,
        "enterprise_to_ebitda": 12,
        "price_to_book": 4,
        "roce_proxy": 0.18,
    }
    row.update(extra)
    return row


class ConfidenceProvenanceExplainabilityTests(unittest.TestCase):
    def test_analyst_feed_does_not_masquerade_as_second_fundamental_source(self):
        out = mod.assess(rich_row())
        self.assertIn(
            "Fundamentais dependem de uma única fonte independente",
            out["confidence_reasons"],
        )

    def test_normalized_provenance_count_takes_precedence(self):
        row = rich_row(
            data_sources=["Yahoo Finance", "SEC EDGAR", "Analyst feed"],
            data_provenance={
                "evidence_state": "observed",
                "independent_fundamental_source_count": 2,
            },
        )
        out = mod.assess(row)
        self.assertNotIn(
            "Fundamentais dependem de uma única fonte independente",
            out["confidence_reasons"],
        )
        self.assertIn("Filings oficiais presentes", out["confidence_reasons"])

    def test_carried_forward_evidence_is_explicit_without_changing_numeric_formula(self):
        base = rich_row()
        carried = rich_row(
            data_provenance={
                "evidence_state": "carried_forward",
                "independent_fundamental_source_count": 1,
            }
        )
        base_out = mod.assess(base)
        carried_out = mod.assess(carried)
        self.assertEqual(base_out["confidence_score"], carried_out["confidence_score"])
        self.assertEqual(base_out["score"], carried_out["score"])
        self.assertIn(
            "Fundamentais transportados do snapshot anterior",
            carried_out["confidence_reasons"],
        )

    def test_pipeline_status_fallback_marks_carried_forward_before_provenance_stage(self):
        out = mod.assess(rich_row(pipeline_status="equity_carried_forward"))
        self.assertIn(
            "Fundamentais transportados do snapshot anterior",
            out["confidence_reasons"],
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
