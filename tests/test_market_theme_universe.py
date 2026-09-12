from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
MARKET=(ROOT/'market.js').read_text(encoding='utf-8')
STOCKS=(ROOT/'market-stock-themes-tools.js').read_text(encoding='utf-8')
STOCKS_CSS=(ROOT/'market-stock-themes-tools.css').read_text(encoding='utf-8')
POLISH=(ROOT/'market-ui-polish.js').read_text(encoding='utf-8')
SW=(ROOT/'sw.js').read_text(encoding='utf-8')

class MarketThemeUniverseTests(unittest.TestCase):
    def test_etf_theme_discovery_uses_all_known_funds(self):
        self.assertIn('let funds=M.stocks.filter(isFund);', MARKET)
        self.assertNotIn('M.stocks.filter(isFund).filter(s=>n(s.score)!=null||n(s.expense_ratio)!=null)', MARKET)
        self.assertIn('long_business_summary', MARKET)
        self.assertIn('${txt(s.theme)} ${txt(s.fund_theme)} ${txt(s.style)} ${txt(s.fund_style)} ${txt(s.ucits)} ${txt(s.fund_ucits)}', MARKET)

    def test_ideas_and_stocks_are_separate_surfaces(self):
        self.assertIn("ideasLabel.textContent = 'Ideias'", STOCKS)
        self.assertIn("stocksButton.dataset.marketStockBrowser = '1'", STOCKS)
        self.assertIn("label.textContent = 'Ações'", STOCKS)
        self.assertIn("version: '1.4'", STOCKS)
        self.assertIn('stock?.theme, stock?.stock_theme, stock?.style', STOCKS)

    def test_stock_theme_results_keep_unscored_companies(self):
        self.assertNotIn('.filter(stock => number(stock?.score) != null)', STOCKS)
        self.assertIn('matches.slice(0, 100)', STOCKS)
        self.assertIn('long_business_summary', STOCKS)

    def test_stock_theme_presentation_has_static_css_owner(self):
        self.assertIn("market-stock-themes-tools.css?v=1.0", STOCKS)
        self.assertNotIn("document.createElement('style')", STOCKS)
        self.assertNotIn('style.textContent', STOCKS)
        self.assertIn('.market-stock-theme-grid{', STOCKS_CSS)
        self.assertIn('.market-analysis-tools__grid{', STOCKS_CSS)
        self.assertIn("market-stock-themes-tools.js?v=1.4", POLISH)
        self.assertNotIn("market-stock-themes-tools.js?v=1.0", POLISH)
        self.assertIn('"./market-stock-themes-tools.css"', SW)

if __name__=='__main__':
    unittest.main(verbosity=2)
