from pathlib import Path
import json
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PortfolioSectorBoxTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.index = (ROOT / "index.html").read_text(encoding="utf-8")
        cls.app = (ROOT / "app.js").read_text(encoding="utf-8")
        cls.styles = (ROOT / "styles.css").read_text(encoding="utf-8")
        cls.sectors = json.loads((ROOT / "data" / "portfolio-sectors.json").read_text(encoding="utf-8"))["tickers"]

    def test_main_portfolio_contains_sector_holdings_box(self):
        self.assertIn('id="portfolioSectorCard"', self.index)
        self.assertIn('id="portfolioSectorSummary"', self.index)
        self.assertIn('Sectores da carteira', self.index)
        self.assertIn('Só ações e ETFs · peso e valor por sector.', self.index)

    def test_sector_box_is_rendered_with_portfolio_items(self):
        self.assertIn("function renderPortfolioSectorBox()", self.app)
        self.assertIn("renderPortfolioSectorBox();", self.app)
        self.assertIn("isPortfolioEquityAsset", self.app)
        self.assertIn("portfolioEquitySector", self.app)
        self.assertIn("pctEquities", self.app)
        self.assertNotIn("pctAnalysed", self.app)
        self.assertIn("calcGainLoss(asset)", self.app)
        self.assertIn('fetch("data/portfolio-sectors.json"', self.app)
        self.assertIn("portfolioSectorTickerCandidates", self.app)
        self.assertIn('a.sector === "Sector por identificar"', self.app)
        self.assertIn("portfolio-sector-more", self.app)

    def test_known_user_tickers_keep_correct_offline_fallbacks(self):
        self.assertIn('"NESN.SW": {s:"Consumo Básico"', self.app)
        self.assertIn('"GOOGL": {s:"Comunicações"', self.app)
        self.assertIn('"TSLA": {s:"Consumo Cíclico"', self.app)

    def test_generated_sector_map_classifies_reported_positions(self):
        expected = {
            "NESN.SW": "Consumer Defensive",
            "GOOGL": "Communication Services",
            "TSLA": "Consumer Cyclical",
            "ELE.MC": "Utilities",
            "GSK.L": "Healthcare",
            "EDP.LS": "Utilities",
            "VIE.PA": "Industrials",
        }
        for ticker, sector in expected.items():
            with self.subTest(ticker=ticker):
                self.assertEqual(self.sectors[ticker]["sector"], sector)

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
        self.assertIn(".portfolio-sector-distribution", self.styles)
        self.assertIn(".portfolio-sector-more", self.styles)
        self.assertIn("@media(max-width:640px)", self.styles)


if __name__ == "__main__":
    unittest.main(verbosity=2)
