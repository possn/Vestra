from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class DossierClosePortfolioOwnershipTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.controls = (ROOT / 'market-dossier-controls.js').read_text(encoding='utf-8')
        cls.navigation = (ROOT / 'portfolio-sheet-navigation.js').read_text(encoding='utf-8')
        cls.company = (ROOT / 'market-company-brief.js').read_text(encoding='utf-8')

    def test_generic_close_yields_to_portfolio_return_owner_before_mutation(self):
        return_view = "const returnView = String(sheet.dataset.returnView || '').trim();"
        guard = "if (returnView === 'portfolio' || sheet.dataset.tool === 'ticker-from-portfolio') return false;"
        hide = 'sheet.hidden = true;'
        clear_return = "sheet.dataset.returnView = '';"

        self.assertIn(return_view, self.controls)
        self.assertIn(guard, self.controls)
        self.assertIn(hide, self.controls)
        self.assertIn(clear_return, self.controls)
        self.assertLess(self.controls.index(return_view), self.controls.index(guard))
        self.assertLess(self.controls.index(guard), self.controls.index(hide))
        self.assertLess(self.controls.index(guard), self.controls.index(clear_return))

    def test_portfolio_navigation_remains_the_specialized_close_owner(self):
        self.assertIn("if(sh.dataset.ticker && sh.dataset.returnView==='portfolio')", self.navigation)
        self.assertIn('reopenPortfolioAnalysis();', self.navigation)
        self.assertIn('e.stopImmediatePropagation();', self.navigation)

    def test_loader_and_runtime_versions_match(self):
        self.assertIn("version: '1.8'", self.controls)
        self.assertIn('market-dossier-controls.js?v=1.8', self.company)


if __name__ == '__main__':
    unittest.main(verbosity=2)
