from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PortfolioSectorExplorerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.js = (ROOT / "portfolio-sector-explorer.js").read_text(encoding="utf-8")
        cls.css = (ROOT / "portfolio-sector-explorer.css").read_text(encoding="utf-8")
        cls.ui = (ROOT / "vestra-portfolio-ui.js").read_text(encoding="utf-8")
        cls.index = (ROOT / "index.html").read_text(encoding="utf-8")

    def test_explorer_is_lazy_loaded_only_from_portfolio_ui(self):
        self.assertNotIn('src="portfolio-sector-explorer.js', self.index)
        self.assertIn("portfolio-sector-explorer.js?v=1.0", self.ui)
        self.assertIn("if(window.VestraPortfolioSectorExplorer)", self.ui)
        self.assertIn("void ensureSectorExplorer();", self.ui)
        self.assertIn("version:'1.3'", self.ui)
        self.assertIn("vestra-portfolio-ui.js?v=1.3", self.index)

    def test_equities_only_and_sector_grouping_contract(self):
        self.assertIn("function isOwnedEquity(asset, stock)", self.js)
        self.assertIn("['ETF','FUND','MUTUALFUND','CRYPTO']", self.js)
        self.assertIn("sector: t(stock?.sector) || 'Sem sector'", self.js)
        self.assertIn("groups.get(key).push(row)", self.js)
        self.assertIn("weight:total>0?value/total*100:0", self.js)

    def test_position_metrics_use_real_portfolio_values(self):
        for token in (
            "const value = n(asset.value) ?? n(asset.marketValueEUR) ?? 0",
            "const cost = n(asset.costBasis)",
            "const q = n(asset.qty)",
            "value - cost",
            "gain / cost * 100",
            "cost / q",
        ):
            self.assertIn(token, self.js)

    def test_first_buy_date_requires_exact_isin_or_ticker_identity(self):
        self.assertIn("if (assetIsin && eventIsin) return assetIsin === eventIsin;", self.js)
        self.assertIn("eventIds.some(id => ids.has(id))", self.js)
        self.assertNotIn("replace(/\\.[A-Z]+$/", self.js)
        self.assertIn("e?.type === 'BUY'", self.js)

    def test_stock_row_opens_canonical_portfolio_dossier(self):
        self.assertIn("data-market-ticker=", self.js)
        self.assertIn("esc(r.ticker)", self.js)
        self.assertIn("nav.openCompany(tk,{origin:'portfolio',sourceNode})", self.js)
        self.assertIn("window.VestraMarketLoader?.ensure?.()", self.js)

    def test_mobile_layout_is_explicit(self):
        self.assertIn("@media(max-width:720px)", self.css)
        self.assertIn("@media(max-width:430px)", self.css)
        self.assertIn(".vpse-position-meta", self.css)


if __name__ == "__main__":
    unittest.main(verbosity=2)
