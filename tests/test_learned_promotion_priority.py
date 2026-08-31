from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "scripts" / "run.py"


class LearnedPromotionPriorityTests(unittest.TestCase):
    def test_learned_snapshot_is_loaded_separately(self):
        src = RUN.read_text(encoding="utf-8")
        self.assertIn("LEARNED_SNAPSHOT_PATH", src)
        self.assertIn("def _load_learned_tickers()", src)
        self.assertIn('payload.get("rows", [])', src)

    def test_learned_names_are_fetched_before_bulk_portfolio(self):
        src = RUN.read_text(encoding="utf-8")
        learned = src.index("raw_learned = fetch_many(learned_tickers")
        portfolio = src.index("raw_portfolio = fetch_many(portfolio_remainder")
        broad = src.index("raw_remainder = fetch_many(remainder_tickers")
        self.assertLess(learned, portfolio)
        self.assertLess(portfolio, broad)
        self.assertIn("workers_override=1, retries=3", src)

    def test_learned_result_wins_dedup_and_missing_promotion_is_visible(self):
        src = RUN.read_text(encoding="utf-8")
        portfolio_update = src.index("raw_by_symbol.update({r.ticker: r for r in raw_portfolio})")
        learned_update = src.index("raw_by_symbol.update({r.ticker: r for r in raw_learned})")
        self.assertLess(portfolio_update, learned_update)
        self.assertIn("Learned ticker promotion incomplete", src)
        self.assertIn("Learned ticker promotion complete", src)


if __name__ == "__main__":
    unittest.main()
