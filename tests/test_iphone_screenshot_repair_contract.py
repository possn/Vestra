"""iPhone screenshot regression contract: real DOM surfaces and retained data."""
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
CSS=(ROOT/"vestra-iphone-screenshot-repairs.css").read_text()
HTML=(ROOT/"index.html").read_text()
APP=(ROOT/"app.js").read_text()
MARKET=(ROOT/"market-opportunities.js").read_text()

class IphoneScreenshotRepairs(unittest.TestCase):
    def test_late_cache_busted_stylesheet_and_mobile_scope(self):
        self.assertIn("vestra-iphone-screenshot-repairs.css?v=20261109-iphone-four-fixes",HTML)
        self.assertLess(HTML.index("vestra-portfolio-holdings-editorial.css"),
                        HTML.index("vestra-iphone-screenshot-repairs.css"))
        self.assertIn("@media (max-width: 600px)",CSS)
    def test_legacy_pnl_financial_evidence_stays_present(self):
        self.assertIn("equityPnLContent",HTML)
        for key in ("grandTotalReturnPct","totalCost","totalRealized","totalDivAll",
                    "trueYieldPct","totalReturnPct"):
            self.assertIn(key,APP)
        self.assertIn('grid-template-columns:repeat(2,minmax(0,1fr))!important',CSS)
        self.assertIn('#equityPnLContent>div:first-child>div:nth-child(3)',CSS)
        self.assertIn('#equityPnLContent>div[style*="border-left:3px"]',CSS)
    def test_holdings_are_styled_without_modifying_amounts(self):
        self.assertIn('id="itemsList"',HTML)
        self.assertIn('#portfolioPositionsChapter #itemsList>.item',CSS)
        self.assertIn('.item__v',CSS)
        self.assertIn('min-height:52px!important',CSS)
    def test_smallcap_actual_dynamic_chip_has_contrast(self):
        self.assertIn("smallcapChip.dataset.smallcapPrebreakoutLens='1'",MARKET)
        self.assertIn('button[data-smallcap-prebreakout-lens]',CSS)
        self.assertIn('[aria-pressed="true"]',CSS)
        self.assertIn('-webkit-text-fill-color:#fff!important',CSS)
    def test_sentiment_score_and_reading_are_distinct_columns(self):
        self.assertIn('class="vi-market-reading-body"',HTML)
        self.assertIn('class="vi-sentiment-orb"',HTML)
        self.assertIn('grid-template-columns:96px minmax(0,1fr)!important',CSS)
        self.assertIn('.vi-market-reading-body>div:last-child',CSS)
        self.assertIn('gap:18px!important',CSS)

if __name__=="__main__":unittest.main()
