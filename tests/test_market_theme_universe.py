from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
MARKET=(ROOT/'market.js').read_text(encoding='utf-8')
STOCKS=(ROOT/'market-stock-themes-tools.js').read_text(encoding='utf-8')

class MarketThemeUniverseTests(unittest.TestCase):
    def test_etf_theme_discovery_uses_all_known_funds(self):
        self.assertIn('let funds=M.stocks.filter(isFund);', MARKET)
        self.assertNotIn('M.stocks.filter(isFund).filter(s=>n(s.score)!=null||n(s.expense_ratio)!=null)', MARKET)
        self.assertIn('long_business_summary', MARKET)

    def test_ideas_and_stocks_are_separate_surfaces(self):
        self.assertIn("ideasLabel.textContent = 'Ideias'", STOCKS)
        self.assertIn("stocksButton.dataset.marketStockBrowser = '1'", STOCKS)
        self.assertIn("label.textContent = 'Ações'", STOCKS)
        self.assertIn("version: '1.1'", STOCKS)

    def test_stock_theme_results_keep_unscored_companies(self):
        self.assertNotIn('.filter(stock => number(stock?.score) != null)', STOCKS)
        self.assertIn('matches.slice(0, 100)', STOCKS)
        self.assertIn('long_business_summary', STOCKS)

if __name__=='__main__':
    unittest.main(verbosity=2)
