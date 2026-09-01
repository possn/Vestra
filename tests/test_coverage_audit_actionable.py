import unittest

from scripts.coverage_audit import (
    actionable_gap,
    gap_priority,
    missing_critical_metrics,
    retrieval_lane,
)


class CoverageAuditActionableTests(unittest.TestCase):
    def test_us_sparse_row_prefers_sec_before_gap_fallbacks(self):
        row = {
            "ticker": "TEST",
            "region": "United States",
            "quote_type": "EQUITY",
            "data_sources": ["Yahoo Finance"],
            "roe": None,
            "roa": 0.1,
        }
        self.assertIn("roe", missing_critical_metrics(row))
        self.assertEqual(retrieval_lane(row), "sec_edgar")

    def test_european_sparse_row_prefers_esef(self):
        row = {
            "ticker": "TEST.DE",
            "region": "Germany",
            "data_sources": ["Yahoo Finance"],
            "roe": None,
        }
        self.assertEqual(retrieval_lane(row), "esef")

    def test_existing_official_source_moves_to_statement_gap(self):
        row = {
            "ticker": "TEST",
            "region": "United States",
            "data_sources": ["Yahoo Finance", "SEC EDGAR"],
            "roe": None,
            "gap_statement_enriched": False,
        }
        self.assertEqual(retrieval_lane(row), "annual_statement_gap")

    def test_missing_values_remain_missing_not_zero(self):
        row = {
            "ticker": "TEST",
            "region": "Canada",
            "data_sources": ["Yahoo Finance"],
            "roe": None,
            "roa": 0,
        }
        missing = missing_critical_metrics(row)
        self.assertIn("roe", missing)
        self.assertNotIn("roa", missing)

    def test_actionable_gap_contains_explainable_lane_and_missing_fields(self):
        row = {
            "ticker": "TEST.PA",
            "name": "Test SA",
            "region": "France",
            "score_model": "general",
            "data_sources": ["Yahoo Finance"],
            "data_coverage_pct": 61,
            "critical_metric_coverage_pct": 50,
            "roe": None,
            "roa": None,
            "data_provenance": {"evidence_state": "observed"},
        }
        item = actionable_gap(row)
        self.assertEqual(item["recommended_retrieval_lane"], "esef")
        self.assertEqual(item["evidence_state"], "observed")
        self.assertGreaterEqual(item["missing_critical_count"], 2)
        self.assertIn("roe", item["missing_critical_metrics"])

    def test_priority_puts_lower_critical_coverage_first(self):
        weaker = {
            "ticker": "WEAK",
            "critical_coverage_pct": 40,
            "coverage_pct": 55,
            "missing_critical_count": 8,
        }
        stronger = {
            "ticker": "STRONG",
            "critical_coverage_pct": 70,
            "coverage_pct": 80,
            "missing_critical_count": 2,
        }
        self.assertLess(gap_priority(weaker), gap_priority(stronger))


if __name__ == "__main__":
    unittest.main()
