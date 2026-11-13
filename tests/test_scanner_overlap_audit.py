"""Tests that scanner overlap is measured, never mechanically erased."""
import importlib.util
import unittest
from pathlib import Path

path = Path(__file__).resolve().parents[1] / "scripts" / "audit_scanner_overlap.py"
spec = importlib.util.spec_from_file_location("audit_scanner_overlap", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ScannerOverlapAuditTests(unittest.TestCase):
    def test_general_baseline_is_not_independent_strategy(self):
        data = {"generated_at": "2026-11-12T15:55:01Z", "ticker_count": 3,
                "tickers": {"A": {"best_opportunities": {"score": 49}},
                            "B": {"best_opportunities": {"score": 50}, "qarp": {"score": 70}},
                            "C": {"turnarounds": {"score": 80}, "qarp": {"score": 75}}}}
        report = module.audit(data)
        self.assertEqual(report["unique_valid_tickers"], 3)
        self.assertEqual(report["multi_lens_tickers"], 2)
        self.assertEqual(report["specialized_tickers"], 2)
        self.assertEqual(report["general_only_tickers"], 1)
        self.assertEqual(report["specialized_without_general"], 1)
        self.assertEqual(report["strategies"]["qarp"], 2)
        self.assertTrue(report["read_only"])
        self.assertEqual(len(data["tickers"]["B"]), 2)

    def test_lineage_is_explicit_not_inferred_from_publish_time(self):
        payload = {"generated_at": "2026-11-13T01:00:00Z", "tickers": {
            "A": {"best_opportunities": {"score": 45}, "qarp": {"score": 67, "source": "financial_feed", "as_of": "2026-11-12"}},
            "B": {"positive_revisions": {"score": 80, "source": "  ", "signal_date": "2026-11-10"}}
        }}
        report = module.audit(payload)
        self.assertEqual(report["total_lens_records"], 3)
        self.assertEqual(report["explicit_lineage_coverage"]["source"]["qarp"]["present"], 1)
        self.assertEqual(report["explicit_lineage_coverage"]["source"]["positive_revisions"]["present"], 0)
        self.assertEqual(report["explicit_lineage_coverage"]["as_of"]["best_opportunities"]["missing"], 1)
        self.assertEqual(report["explicit_lineage_coverage"]["signal_date"]["positive_revisions"]["present"], 1)
        self.assertEqual(payload["tickers"]["A"]["best_opportunities"], {"score": 45})

    def test_invalid_rows_and_empty_source(self):
        report = module.audit({"ticker_count": 2, "tickers": {"A": {}, "B": {"qarp": {"score": 3}}}})
        self.assertEqual(report["invalid_or_empty_ticker_rows"], 1)
        self.assertEqual(report["unique_valid_tickers"], 1)
        with self.assertRaises(ValueError):
            module.audit({"tickers": []})


if __name__ == "__main__":
    unittest.main()
