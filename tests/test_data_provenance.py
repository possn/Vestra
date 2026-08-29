import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "normalize_market_provenance",
    ROOT / "scripts" / "normalize_market_provenance.py",
)
mod = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(mod)


class DataProvenanceTests(unittest.TestCase):
    def test_observed_row_keeps_independent_source_families(self):
        row = {
            "ticker": "ABC",
            "data_sources": ["Yahoo Finance", "SEC EDGAR", "Yahoo Statements (targeted)"],
            "sec_period_end": "2026-06-30",
            "source_agreement_checks": 4,
            "source_agreement_pct": 100.0,
        }
        changed = mod.normalize_row(row, "2026-08-29T06:00:00Z")
        self.assertTrue(changed)
        p = row["data_provenance"]
        self.assertEqual(p["evidence_state"], "observed")
        self.assertEqual(p["source_count"], 3)
        self.assertEqual(p["independent_source_count"], 2)
        self.assertEqual(p["independent_source_families"], ["yahoo", "sec_edgar"])
        self.assertEqual(p["agreement_checks"], 4)
        self.assertEqual(p["agreement_pct"], 100.0)
        self.assertEqual(p["filing_periods"]["sec_edgar"], "2026-06-30")
        self.assertEqual(p["pipeline_generated_at"], "2026-08-29T06:00:00Z")

    def test_esef_identity_and_derived_metrics_are_explicit(self):
        row = {
            "ticker": "XYZ.L",
            "data_sources": ["Yahoo Finance", "ESEF / filings.xbrl.org"],
            "identity_source": "GLEIF/ANNA ISIN→LEI",
            "isin": "GB0000000001",
            "lei": "213800TESTLEI000001",
            "esef_period_end": "2025-12-31",
            "derived_metrics": ["fcf_margin"],
        }
        mod.normalize_row(row)
        p = row["data_provenance"]
        self.assertEqual(p["identity_source"], "GLEIF/ANNA ISIN→LEI")
        self.assertEqual(p["isin"], "GB0000000001")
        self.assertEqual(p["lei"], "213800TESTLEI000001")
        self.assertEqual(p["filing_periods"]["esef"], "2025-12-31")
        self.assertEqual(p["derived_metrics"], ["fcf_margin"])
        self.assertFalse(p["derived_metrics_are_independent"])

    def test_carried_and_metadata_rows_are_not_presented_as_fresh_evidence(self):
        carried = {"data_sources": ["Yahoo Finance"], "pipeline_status": "equity_carried_forward"}
        metadata = {"data_sources": [], "pipeline_status": "equity_catalog_only"}
        mod.normalize_row(carried)
        mod.normalize_row(metadata)
        self.assertEqual(carried["data_provenance"]["evidence_state"], "carried_forward")
        self.assertEqual(metadata["data_provenance"]["evidence_state"], "metadata_only")
        self.assertEqual(metadata["data_provenance"]["source_count"], 0)

    def test_official_congress_source_is_normalized_without_fabrication(self):
        row = {
            "data_sources": ["Yahoo Finance", "STOCK Act / Bargo"],
            "congress_trades": [{"type": "buy"}],
        }
        mod.normalize_row(row)
        self.assertNotIn("STOCK Act / Bargo", row["data_sources"])
        self.assertIn(mod.OFFICIAL_CONGRESS_SOURCE, row["data_sources"])
        families = row["data_provenance"]["source_families"]
        self.assertIn("stock_act", families)

        no_trades = {"data_sources": ["Yahoo Finance", "Bargo"], "congress_trades": []}
        mod.normalize_row(no_trades)
        self.assertNotIn(mod.OFFICIAL_CONGRESS_SOURCE, no_trades["data_sources"])

    def test_normalization_is_idempotent(self):
        row = {"data_sources": ["Yahoo Finance", "SEC EDGAR"], "source_agreement_checks": 2}
        self.assertTrue(mod.normalize_row(row, "2026-08-29T06:00:00Z"))
        self.assertFalse(mod.normalize_row(row, "2026-08-29T06:00:00Z"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
