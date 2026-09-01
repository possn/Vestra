from pathlib import Path
import unittest


class PortfolioAlternativeNavigationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = Path('portfolio-sheet-navigation.js').read_text(encoding='utf-8')
        cls.loader = Path('market-data-loader.js').read_text(encoding='utf-8')

    def test_portfolio_ticker_click_opens_company_directly(self):
        source = self.source
        self.assertIn("const ticker=e.target.closest?.('[data-market-ticker]');", source)
        self.assertIn("const portfolioSheet=!sh.hidden && sh.dataset.tool==='portfolio';", source)
        self.assertIn("if(ticker && portfolioSheet && content()?.contains(ticker))", source)
        self.assertIn("e.stopImmediatePropagation();", source)
        self.assertIn("void openCompany(ticker.dataset.marketTicker,{origin:'portfolio',sourceNode:ticker});", source)

    def test_watch_star_is_owned_by_navigation_and_never_opens_dossier(self):
        source = self.source
        self.assertIn("const watch=e.target.closest?.('[data-market-watch]');", source)
        self.assertIn("if(watch && portfolioSheet && content()?.contains(watch))", source)
        self.assertIn("window.VestraMarket?.toggleWatch?.(watch.dataset.marketWatch);", source)
        self.assertNotIn("openCompany(watch.dataset.marketWatch", source)

    def test_dossier_capture_ignores_watch_controls_before_matching_parent_ticker(self):
        loader = self.loader
        watch = loader.index("const watch=e.target.closest?.('[data-market-watch]');")
        guard = loader.index("if(watch) return;", watch)
        row = loader.index("const row=e.target.closest?.('[data-market-ticker]');", guard)
        self.assertLess(watch, guard)
        self.assertLess(guard, row)

    def test_portfolio_return_contract_is_preserved(self):
        source = self.source
        self.assertIn("sh.dataset.tool='ticker-from-portfolio';", source)
        self.assertIn("sh.dataset.returnView='portfolio';", source)
        self.assertIn("reopenPortfolioAnalysis();", source)


if __name__ == '__main__':
    unittest.main()
