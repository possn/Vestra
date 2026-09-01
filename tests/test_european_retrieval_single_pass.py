import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class EuropeanRetrievalSinglePassTests(unittest.TestCase):
    def test_esef_shim_does_not_run_yahoo_statement_fallbacks(self):
        src = (ROOT / "scripts" / "esef_enrich.py").read_text(encoding="utf-8")
        self.assertNotIn("from gap_retrieval", src)
        self.assertNotIn("from quarterly_gap_retrieval", src)
        self.assertNotIn("_enrich_gap(", src)
        self.assertNotIn("_enrich_quarterly_gap(", src)

    def test_pipeline_owns_one_annual_and_one_quarterly_gap_pass(self):
        src = (ROOT / "scripts" / "run.py").read_text(encoding="utf-8")
        self.assertEqual(src.count("raw = enrich_gap_retrieval(raw"), 1)
        self.assertEqual(src.count("raw = enrich_quarterly_gap_retrieval(raw"), 1)
        self.assertLess(
            src.index("raw = enrich_esef(raw"),
            src.index("raw = enrich_gap_retrieval(raw"),
        )
        self.assertLess(
            src.index("raw = enrich_gap_retrieval(raw"),
            src.index("raw = enrich_quarterly_gap_retrieval(raw"),
        )


if __name__ == "__main__":
    unittest.main()
