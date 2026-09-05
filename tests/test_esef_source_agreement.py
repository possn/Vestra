import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import esef_enrich_v416 as esef
import normalize_market_provenance as provenance
import provenance_audit


class ESEFSourceAgreementTests(unittest.TestCase):
    def _metric_row(self):
        return {
            "date": "2025-12-31",
            "gross_margin": 0.40,
            "operating_margin": 0.20,
            "net_margin": 0.10,
            "roe": 0.15,
            "roce_proxy": 0.18,
        }

    def test_same_period_four_metrics_measure_agreement_without_changing_values(self):
        annual = self._metric_row()
        m = SimpleNamespace(annual_quality_history=[annual])
        esef_values = {
            "gross_margin": 0.41,       # +1 pp -> agrees
            "operating_margin": 0.22,   # +2 pp -> agrees
            "net_margin": 0.11,         # +1 pp -> agrees
            "roe": 0.25,                # +10 pp -> disagreement
            "roce_proxy": 0.90,         # deliberately excluded: different definition
        }

        self.assertTrue(esef.attach_same_period_observation(m, "2025-12-31", esef_values))
        self.assertEqual(annual["gross_margin"], 0.40, "diagnostic observation must not mutate Yahoo value")
        self.assertIn(esef.ESEF_AGREEMENT_OBSERVATION_KEY, annual)

        row = {
            "ticker": "TEST.L",
            "data_sources": ["Yahoo Finance", "ESEF / filings.xbrl.org"],
            "annual_quality_history": m.annual_quality_history,
            "esef_period_end": "2025-12-31",
        }
        provenance.normalize_row(row, "2026-09-05T17:00:00Z")

        self.assertNotIn(esef.ESEF_AGREEMENT_OBSERVATION_KEY, row["annual_quality_history"][0])
        self.assertEqual(row["source_agreement_checks"], 4)
        self.assertEqual(row["source_agreement_pct"], 75.0)
        self.assertEqual(row["source_agreement_period_end"], "2025-12-31")
        self.assertEqual(row["source_agreement_method"], provenance.SOURCE_AGREEMENT_METHOD)
        self.assertEqual(len(row["source_agreement_details"]), 4)
        self.assertNotIn("roce_proxy", {detail["metric"] for detail in row["source_agreement_details"]})
        self.assertEqual(row["data_provenance"]["agreement_checks"], 4)
        self.assertEqual(row["data_provenance"]["agreement_pct"], 75.0)
        self.assertEqual(row["data_provenance"]["agreement_period_end"], "2025-12-31")
        self.assertEqual(row["data_provenance"]["agreement_method"], provenance.SOURCE_AGREEMENT_METHOD)
        self.assertEqual(
            row["data_provenance"]["independent_fundamental_source_families"],
            ["yahoo", "esef"],
        )

    def test_mismatched_period_is_not_attached_or_measured(self):
        m = SimpleNamespace(annual_quality_history=[self._metric_row()])
        self.assertFalse(esef.attach_same_period_observation(
            m,
            "2024-12-31",
            {"gross_margin": 0.40, "operating_margin": 0.20},
        ))
        row = {
            "data_sources": ["Yahoo Finance", "ESEF / filings.xbrl.org"],
            "annual_quality_history": m.annual_quality_history,
            "esef_period_end": "2024-12-31",
        }
        provenance.normalize_row(row)
        self.assertEqual(row["data_provenance"]["agreement_checks"], 0)
        self.assertIsNone(row["data_provenance"]["agreement_pct"])
        self.assertEqual(provenance_audit._agreement_bucket(row["data_provenance"]), "not_measured")

    def test_one_metric_keeps_percentage_unmeasured(self):
        m = SimpleNamespace(annual_quality_history=[{"date": "2025-12-31", "roe": 0.15}])
        self.assertTrue(esef.attach_same_period_observation(m, "2025-12-31", {"roe": 0.16}))
        row = {
            "data_sources": ["Yahoo Finance", "ESEF / filings.xbrl.org"],
            "annual_quality_history": m.annual_quality_history,
            "esef_period_end": "2025-12-31",
        }
        provenance.normalize_row(row)
        self.assertEqual(row["source_agreement_checks"], 1)
        self.assertIsNone(row["source_agreement_pct"])
        self.assertEqual(row["data_provenance"]["agreement_checks"], 1)
        self.assertIsNone(row["data_provenance"]["agreement_pct"])
        self.assertEqual(provenance_audit._agreement_bucket(row["data_provenance"]), "not_measured")

    def test_existing_single_check_percentage_is_gated_in_provenance(self):
        row = {
            "data_sources": ["Yahoo Finance", "SEC EDGAR"],
            "source_agreement_checks": 1,
            "source_agreement_pct": 100.0,
        }
        p = provenance.build_provenance(row)
        self.assertEqual(p["agreement_checks"], 1)
        self.assertIsNone(p["agreement_pct"])
        self.assertEqual(provenance_audit._agreement_bucket(p), "not_measured")


if __name__ == "__main__":
    unittest.main(verbosity=2)
