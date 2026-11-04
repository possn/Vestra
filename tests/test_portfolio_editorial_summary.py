"""Contract for a single editorial Portfolio summary with live canonical metrics."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
class PortfolioEditorialSummaryTests(unittest.TestCase):
    def test_final_css_layer_is_linked_after_contrast_and_mobile_home(self):
        html=(ROOT/"index.html").read_text(encoding="utf-8")
        link="vestra-portfolio-editorial-summary.css?v=20261104-unified-metrics"
        self.assertIn(link,html)
        self.assertLess(html.index("vestra-portfolio-contrast-p0.css"),html.index(link))
        self.assertLess(html.index("vestra-home-mobile-editorial.css"),html.index(link))
        self.assertLess(html.index(link),html.index("</head>"))

    def test_all_financial_fields_and_actions_preserved_in_original_dom(self):
        html=(ROOT/"index.html").read_text(encoding="utf-8")
        root=html.split('id="viewAssets"',1)[1].split('<!-- CASHFLOW',1)[0]
        for element in ("portfolioGlance","portfolioTotalValue","portfolioPositionCount",
                        "portfolioTopClass","portfolioIncomeValue","portfolioMonthlyValue",
                        "portfolioYieldValue","segAssets","segLiabs","btnAddItem",
                        "btnPortfolioFilters","qSearch","qClass","qSort",
                        "itemsList","portfolioToolsStrip"):
            with self.subTest(element=element):
                self.assertIn('id="'+element+'"',root)
        css=(ROOT/"vestra-portfolio-editorial-summary.css").read_text(encoding="utf-8")
        self.assertIn("@media (max-width:600px)",css)
        self.assertIn("@media (min-width:900px)",css)
        self.assertIn("grid-template-columns:repeat(3,minmax(0,1fr))",css)
        self.assertNotIn("display:none",css)
        self.assertNotIn("MutationObserver",css)

if __name__=="__main__":
    unittest.main()
