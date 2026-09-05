import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class MarketCompanyBriefNoRefetchTests(unittest.TestCase):
    def test_company_brief_reuses_market_runtime_state(self):
        source = (ROOT / "market-company-brief.js").read_text(encoding="utf-8")
        self.assertIn("window.VestraMarket", source)
        self.assertIn("resolvePortfolioStock", source)
        self.assertNotIn("fetch('./data/stocks-index.json'", source)
        self.assertNotIn("fetch('./data/stocks.json'", source)

    def test_company_brief_still_refreshes_after_dossier_mutations(self):
        source = (ROOT / "market-company-brief.js").read_text(encoding="utf-8")
        self.assertIn("new MutationObserver", source)
        self.assertIn("requestAnimationFrame", source)
        self.assertIn("repair()", source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
