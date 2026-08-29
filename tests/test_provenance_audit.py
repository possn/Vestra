import datetime as dt
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "provenance_audit",
    ROOT / "scripts" / "provenance_audit.py",
)
mod = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(mod)


class ProvenanceAuditTests(unittest.TestCase):
    def test_summary_separates_observed_fundamental_and_official_evidence(self):
        rows = [
            {
                "data_provenance": {
                    "evidence_state": "observed",
                    "source_families": ["yahoo", "analyst", "sec_edgar"],
                    "independent_fundamental_source_count": 2,
                    "independent_fundamental_source_families": ["yahoo", "sec_edgar"],
                    "agreement_checks": 4,
                    "agreement_pct": 100.0,
                    "filing_periods": {"sec_edgar": "2026-06-30"},
                }
            },
            {
                "data_provenance": {
                    "evidence_state": "carried_forward",
                    "source_families": ["yahoo", "sec_form4"],
                    "independent_fundamental_source_count": 1,
                    "independent_fundamental_source_families": ["yahoo"],
                    "agreement_checks": 0,
                    "agreement_pct": None,
                    "filing_periods": {},
                }
            },
        ]
        out = mod.summarize(rows, dt.date(2026, 8, 29))
        self.assertEqual(out["count"], 2)
        self.assertEqual(out["provenance_coverage_pct"], 100.0)
        self.assertEqual(out["evidence_state"]["observed"], 1)
        self.assertEqual(out["independent_fundamental_source_count"]["2"], 1)
        self.assertEqual(out["official_filing_rows"], 1)
        self.assertEqual(out["agreement"]["gte90"], 1)
        self.assertEqual(out["agreement"]["not_measured"], 1)
        self.assertEqual(out["official_filing_freshness"]["lte190d"], 1)
        self.assertEqual(out["source_family_coverage"]["analyst"], 1)
        self.assertNotIn("analyst", out["fundamental_source_family_coverage"])

    def test_supplemental_source_does_not_create_fundamental_confirmation(self):
        rows = [{
            "data_provenance": {
                "evidence_state": "observed",
                "source_families": ["yahoo", "analyst", "sec_form4"],
                "independent_fundamental_source_count": 1,
                "independent_fundamental_source_families": ["yahoo"],
                "filing_periods": {},
            }
        }]
        out = mod.summarize(rows, dt.date(2026, 8, 29))
        self.assertEqual(out["independent_fundamental_source_count"]["1"], 1)
        self.assertEqual(out["official_filing_rows"], 0)
        self.assertEqual(out["source_family_coverage"]["analyst"], 1)
        self.assertEqual(out["source_family_coverage"]["sec_form4"], 1)
        self.assertEqual(out["fundamental_source_family_coverage"], {"yahoo": 1})

    def test_weakest_evidence_prefers_metadata_and_carried_rows(self):
        payload = {
            "generated_at": "2026-08-29T06:00:00Z",
            "stocks": [
                {"ticker": "OBS", "quote_type": "EQUITY", "region": "US", "data_coverage_pct": 90,
                 "data_provenance": {"evidence_state": "observed", "independent_fundamental_source_count": 2, "independent_fundamental_source_families": ["yahoo", "sec_edgar"], "filing_periods": {}}},
                {"ticker": "META", "quote_type": "EQUITY", "region": "US", "data_coverage_pct": 0,
                 "data_provenance": {"evidence_state": "metadata_only", "independent_fundamental_source_count": 0, "independent_fundamental_source_families": [], "filing_periods": {}}},
                {"ticker": "CARRY", "quote_type": "EQUITY", "region": "UK", "data_coverage_pct": 70,
                 "data_provenance": {"evidence_state": "carried_forward", "independent_fundamental_source_count": 1, "independent_fundamental_source_families": ["yahoo"], "filing_periods": {}}},
            ],
        }
        audit = mod.build_audit(payload, dt.date(2026, 8, 29))
        tickers = [x["ticker"] for x in audit["weakest_evidence_dossiers"][:3]]
        self.assertEqual(tickers, ["META", "CARRY", "OBS"])
        self.assertIn("US", audit["by_region"])
        self.assertEqual(audit["schema_version"], 2)
        self.assertEqual(audit["independent_source_scope"], "fundamentals")


if __name__ == "__main__":
    unittest.main(verbosity=2)
