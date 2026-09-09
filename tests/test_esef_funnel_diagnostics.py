import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SOURCE = (ROOT / "scripts" / "esef_enrich_v416.py").read_text(encoding="utf-8")
SHIM_SOURCE = (ROOT / "scripts" / "esef_enrich.py").read_text(encoding="utf-8")
ENRICH_SOURCE = SOURCE.split("def enrich(raw,priority=None,max_nonpriority=220):", 1)[1]


class ESEFFunnelDiagnosticsTests(unittest.TestCase):
    def test_funnel_covers_each_existing_retrieval_stage(self):
        for key in (
            "eligible", "attempted", "isin_resolved", "isin_missing",
            "lei_resolved", "lei_missing", "filing_found", "filing_missing",
            "report_parsed", "report_failed", "enriched",
            "prior_isin_reused", "prior_lei_reused",
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

    def test_prior_identity_is_reused_only_as_a_complete_valid_pair(self):
        self.assertIn("prior_isin=str(getattr(m,'_verified_esef_isin','')", ENRICH_SOURCE)
        self.assertIn("prior_lei=str(getattr(m,'_verified_esef_lei','')", ENRICH_SOURCE)
        self.assertIn("prior_pair_valid=bool(ISIN_RE.match(prior_isin) and LEI_RE.match(prior_lei))", ENRICH_SOURCE)
        self.assertIn("if prior_pair_valid:", ENRICH_SOURCE)
        self.assertIn("isin,isin_source=prior_isin,'Prior verified ESEF identity'", ENRICH_SOURCE)
        self.assertIn("lei=prior_lei", ENRICH_SOURCE)
        self.assertIn("if lei is None:\n            lei=resolve_lei(s,isin)", ENRICH_SOURCE)

    def test_shim_seeds_cache_only_from_previously_published_esef_rows(self):
        self.assertIn('_ESEF_SOURCE = "ESEF / filings.xbrl.org"', SHIM_SOURCE)
        self.assertIn("_ESEF_SOURCE not in sources", SHIM_SOURCE)
        self.assertIn("_ISIN_RE.match(isin)", SHIM_SOURCE)
        self.assertIn("_LEI_RE.match(lei)", SHIM_SOURCE)
        self.assertIn('out[ticker] = (isin, lei)', SHIM_SOURCE)
        self.assertIn('re.compile(r"^[A-Z0-9]{18}[0-9]{2}$")', SHIM_SOURCE)
        self.assertNotIn("name", SHIM_SOURCE.split("def _verified_identity_cache", 1)[1].split("def _attach_verified_identities", 1)[0])


if __name__ == "__main__":
    unittest.main()
