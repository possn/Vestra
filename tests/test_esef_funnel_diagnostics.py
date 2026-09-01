import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "scripts" / "esef_enrich_v416.py").read_text(encoding="utf-8")
ENRICH_SOURCE = SOURCE.split("def enrich(raw,priority=None,max_nonpriority=220):", 1)[1]


class ESEFFunnelDiagnosticsTests(unittest.TestCase):
    def test_funnel_covers_each_existing_retrieval_stage(self):
        for key in (
            "eligible", "attempted", "isin_resolved", "isin_missing",
            "lei_resolved", "lei_missing", "filing_found", "filing_missing",
            "report_parsed", "report_failed", "enriched",
        ):
            self.assertIn(repr(key), ENRICH_SOURCE)
        self.assertIn("log.info('ESEF funnel %s'", ENRICH_SOURCE)

    def test_diagnostics_do_not_add_duplicate_retrieval_calls(self):
        self.assertEqual(ENRICH_SOURCE.count("resolve_isin_with_source(t,s)"), 1)
        self.assertEqual(ENRICH_SOURCE.count("resolve_lei(s,isin)"), 1)
        self.assertEqual(ENRICH_SOURCE.count("latest_filing(s,lei,c)"), 1)
        self.assertEqual(ENRICH_SOURCE.count("report(s,f)"), 1)

    def test_failures_are_counted_before_existing_fail_closed_continue(self):
        self.assertIn("diag['isin_missing']+=1\n            continue", ENRICH_SOURCE)
        self.assertIn("diag['lei_missing']+=1\n            continue", ENRICH_SOURCE)
        self.assertIn("diag['filing_missing']+=1\n            continue", ENRICH_SOURCE)
        self.assertIn("diag['report_failed']+=1\n            continue", ENRICH_SOURCE)


if __name__ == "__main__":
    unittest.main()
