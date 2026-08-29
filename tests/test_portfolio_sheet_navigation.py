from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

def read(path): return (ROOT/path).read_text(encoding="utf-8")

class PortfolioSheetNavigationTests(unittest.TestCase):
    def test_consolidated_navigation_is_the_only_active_sheet_nav(self):
        index=read("index.html")
        self.assertIn('portfolio-sheet-navigation.js?v=1.0',index)
        self.assertNotIn('portfolio-navigation-fix.js',index)
        self.assertNotIn('market-close-controller.js',index)

    def test_close_and_return_contracts_are_preserved(self):
        s=read("portfolio-sheet-navigation.js")
        for token in (
            "sh.dataset.tool='ticker-from-portfolio'",
            "sh.dataset.returnView='portfolio'",
            'reopenPortfolioAnalysis()',
            'closePortfolioToMarket()',
            'cleanupPortfolioChrome()',
            'market-close-persistent',
            'window.VestraNavigation',
            'openCompany',
        ): self.assertIn(token,s)
        self.assertEqual(s.count('new MutationObserver'),1)
        self.assertIn('window.VestraPortfolioSheetNavigation',s)

    def test_latest_navigation_request_wins_before_dossier_open(self):
        s=read("portfolio-sheet-navigation.js")
        hydrate=s.index("await Promise.resolve(hydrate(tk))")
        first_guard=s.index("if(request!==navigationSequence) return false;",hydrate)
        open_call=s.index("await Promise.resolve(api.openTicker(tk))",first_guard)
        self.assertLess(hydrate,first_guard)
        self.assertLess(first_guard,open_call)
        self.assertIn("const request=++navigationSequence",s)

    def test_ticker_decoration_stays_separate_and_delegates_navigation(self):
        routing=read("portfolio-dossier-routing.js")
        self.assertIn('tickerFrom',routing)
        self.assertIn('data-market-ticker',routing)
        self.assertIn("window.VestraNavigation",routing)
        self.assertIn("origin:'portfolio'",routing)
        self.assertNotIn('closePortfolioToMarket',routing)

if __name__=='__main__': unittest.main(verbosity=2)
