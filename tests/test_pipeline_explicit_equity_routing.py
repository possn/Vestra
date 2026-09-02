from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUN = (ROOT / "scripts" / "run.py").read_text(encoding="utf-8")


class PipelineExplicitEquityRoutingTests(unittest.TestCase):
    def test_run_uses_canonical_equity_candidate_contract(self):
        self.assertIn("from asset_types import is_equity_candidate", RUN)

    def test_analyst_retrieval_excludes_only_explicit_non_equities(self):
        self.assertIn(
            "[dataclasses.asdict(s) for s in scored if is_equity_candidate(s.quote_type)]",
            RUN,
        )

    def test_insider_and_congress_routes_use_equity_candidate_contract(self):
        self.assertIn(
            'us_tickers = [s.ticker for s in scored if "." not in s.ticker and is_equity_candidate(s.quote_type)]',
            RUN,
        )
        self.assertIn("insider_map = annotate_insiders(us_tickers)", RUN)
        self.assertIn("congress_map = fetch_congress_for_universe(us_tickers)", RUN)

    def test_us_equity_quality_denominator_excludes_explicit_non_equities(self):
        self.assertIn(
            'us_equity_rows = [r for r in rows if is_equity_candidate(r.get("quote_type")) and "." not in (r.get("ticker") or "")]',
            RUN,
        )

    def test_no_blank_type_is_forced_to_equity(self):
        asset_types = (ROOT / "scripts" / "asset_types.py").read_text(encoding="utf-8")
        self.assertIn("return not is_explicit_non_equity(value)", asset_types)
        self.assertNotIn('normalized_quote_type(value) == "EQUITY"', asset_types)


if __name__ == "__main__":
    unittest.main(verbosity=2)
