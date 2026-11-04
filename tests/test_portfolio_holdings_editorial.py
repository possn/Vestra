"""Vestra 2.0 portfolio position ledger retains the live financial controls."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

class PortfolioHoldingsEditorialTests(unittest.TestCase):
    def test_stylesheet_loaded_after_portfolio_summary(self):
        html=(ROOT/"index.html").read_text(encoding="utf-8")
        path="vestra-portfolio-holdings-editorial.css?v=20261104-ledger"
        self.assertIn(path,html)
        self.assertLess(html.index("vestra-portfolio-editorial-summary.css"),html.index(path))
        self.assertLess(html.index(path),html.index("</head>"))

    def test_hydrated_holding_nodes_and_tools_are_kept(self):
        html=(ROOT/"index.html").read_text(encoding="utf-8")
        assets=html.split('id="viewAssets"',1)[1].split('<!-- CASHFLOW',1)[0]
        for ident in ("portfolioPositionsChapter","itemsList","btnPortfolioFilters",
                      "portfolioFilterPanel","qSearch","qSort","qClass",
                      "btnRefreshQuotes","quoteErrorsInline","btnItemsToggle",
                      "portfolioToolsStrip","portfolioSectorCard"):
            with self.subTest(ident=ident):
                self.assertIn('id="'+ident+'"',assets)
        css=(ROOT/"vestra-portfolio-holdings-editorial.css").read_text(encoding="utf-8")
        self.assertIn("@media (max-width:600px)",css)
        self.assertIn("#itemsList>.item",css)
        self.assertIn("focus-visible",css)
        self.assertNotIn("MutationObserver",css)
        self.assertNotIn("display:none",css)

if __name__=="__main__":
    unittest.main()
