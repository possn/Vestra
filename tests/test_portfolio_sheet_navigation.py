from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

def read(path): return (ROOT/path).read_text(encoding="utf-8")

class PortfolioSheetNavigationTests(unittest.TestCase):
    def test_consolidated_navigation_is_the_only_active_sheet_nav(self):
        index=read("index.html")
        self.assertIn('portfolio-sheet-navigation.js?v=1.3',index)
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

    def test_latest_navigation_request_opens_before_background_hydration(self):
        s=read("portfolio-sheet-navigation.js")
        self.assertNotIn("await Promise.resolve(hydrate(tk))",s)
        prepare=s.index("prepareDossierOrigin(origin);")
        open_call=s.index("const result=api.openTicker(tk);",prepare)
        visible_origin=s.index("applyDossierOrigin(origin);",open_call)
        await_result=s.index("await Promise.resolve(result);",visible_origin)
        guard=s.index("if(request!==navigationSequence) return false;",await_result)
        self.assertLess(prepare,open_call)
        self.assertLess(open_call,visible_origin)
        self.assertLess(visible_origin,await_result)
        self.assertLess(await_result,guard)
        self.assertIn("const request=++navigationSequence",s)
        self.assertIn("if(!api.__lazyDossiersInstalled)",s)
        self.assertIn("hydrateOpenDossier",s)

    def test_ticker_decoration_stays_separate_and_delegates_navigation(self):
        routing=read("portfolio-dossier-routing.js")
        self.assertIn('tickerFrom',routing)
        self.assertIn('data-market-ticker',routing)
        self.assertIn("window.VestraNavigation",routing)
        self.assertIn("origin:'portfolio'",routing)
        self.assertNotIn('closePortfolioToMarket',routing)

if __name__=='__main__': unittest.main(verbosity=2)
