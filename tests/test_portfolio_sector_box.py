from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PortfolioSectorBoxTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = (ROOT / "index.html").read_text(encoding="utf-8")
        cls.app = (ROOT / "app.js").read_text(encoding="utf-8")
        cls.styles = (ROOT / "styles.css").read_text(encoding="utf-8")

    def test_main_portfolio_contains_sector_holdings_box(self):
        self.assertIn('id="portfolioSectorCard"', self.index)
        self.assertIn('id="portfolioSectorSummary"', self.index)
        self.assertIn('Sectores da carteira', self.index)
        self.assertIn('Peso, valor e activos dentro de cada sector.', self.index)

    def test_sector_box_is_rendered_with_portfolio_items(self):
        self.assertIn("function renderPortfolioSectorBox()", self.app)
        self.assertIn("renderPortfolioSectorBox();", self.app)
        self.assertIn("getTickerMeta(asset)?.sector", self.app)
        self.assertIn("pctAnalysed", self.app)
        self.assertIn("pctPortfolio", self.app)
        self.assertIn("calcGainLoss(asset)", self.app)

    def test_sector_assets_keep_dossier_navigation(self):
        self.assertIn('data-sector-research=', self.app)
        self.assertIn("window.VestraMarketLoader?.ensure?.()", self.app)
        self.assertIn("api?.openPortfolioAsset", self.app)

    def test_liabilities_hide_sector_box(self):
        self.assertIn("if (showingLiabs)", self.app)
        self.assertIn("card.hidden = true", self.app)

    def test_sector_box_has_mobile_contract(self):
        self.assertIn(".portfolio-sector-group", self.styles)
        self.assertIn(".portfolio-sector-asset", self.styles)
        self.assertIn("@media(max-width:640px)", self.styles)


if __name__ == "__main__":
    unittest.main(verbosity=2)
