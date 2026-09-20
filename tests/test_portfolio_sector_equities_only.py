from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.js").read_text(encoding="utf-8")
INDEX = (ROOT / "index.html").read_text(encoding="utf-8")


class PortfolioSectorEquityOnlyTests(unittest.TestCase):
    def test_sector_box_uses_strict_equity_predicate(self):
        self.assertIn("function isPortfolioEquityAsset(asset)", APP)
        self.assertIn('quoteType === "EQUITY" || quoteType === "ETF"', APP)
        self.assertIn('quoteType === "CRYPTOCURRENCY" || quoteType === "MUTUALFUND" || quoteType === "FUND"', APP)
        self.assertIn('cls === "acoes/etfs"', APP)
        self.assertIn("const eligible = (state.assets || []).filter(isPortfolioEquityAsset);", APP)

    def test_sector_box_does_not_use_total_portfolio_denominator(self):
        start = APP.index("function renderPortfolioSectorBox()")
        end = APP.index("\nfunction renderItems()", start)
        block = APP[start:end]
        self.assertIn("const equityTotal =", block)
        self.assertIn("pctEquities:", block)
        self.assertNotIn("portfolioTotal =", block)
        self.assertIn("% ações + ETFs", block)

    def test_sector_labels_are_real_business_sectors(self):
        for label in (
            "Tecnologia", "Saúde", "Financeiro / Bancos", "Consumo discricionário",
            "Consumo básico", "Industriais", "Materiais", "Comunicação / Serviços",
            "Energia", "Utilities", "Imobiliário",
        ):
            self.assertIn(label, APP)
        self.assertIn('return "ETF diversificado";', APP)

    def test_real_market_metadata_has_priority_over_static_fallback(self):
        start = APP.index("function portfolioEquitySector(asset)")
        end = APP.index("\nfunction renderPortfolioSectorBox()", start)
        block = APP[start:end]
        self.assertLess(block.index("meta.sector"), block.index("getTickerMeta(asset)"))

    def test_broker_aliases_and_high_confidence_themes_are_preserved(self):
        self.assertIn('"NFC": ["NFC.DE", "NFLX"]', APP)
        self.assertIn('"UT8": ["UBER"]', APP)
        self.assertIn('"OMV.VI": ["OMV.DE"]', APP)
        self.assertIn('"NSIS-B.CO": "Materiais"', APP)
        self.assertIn('"ADPT": "Saúde"', APP)
        self.assertIn('physical (?:gold|silver|platinum|palladium)', APP)
        self.assertIn('const thematic = inferPortfolioSectorTheme(asset);', APP)

    def test_legacy_sector_chart_uses_same_equity_only_universe(self):
        start = APP.index("function renderPortfolioCharts()")
        end = APP.index("\nfunction ", start + 20)
        block = APP[start:end]
        self.assertIn("state.assets.filter(isPortfolioEquityAsset)", block)
        self.assertIn("portfolioEquitySector(a)", block)

    def test_ui_copy_makes_scope_explicit_and_app_version_rolls_forward(self):
        self.assertIn("Só ações e ETFs · peso e valor por sector.", INDEX)
        self.assertIn("app.js?v=20260920v8", INDEX)


if __name__ == "__main__":
    unittest.main(verbosity=2)
