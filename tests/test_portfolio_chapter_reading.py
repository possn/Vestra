"""Portfolio visual contract for chapter navigation, canonical totals and positions."""
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class PortfolioChapterReadingTests(unittest.TestCase):
 def test_real_hosts_and_accessible_visual_rules(self):
  html=(ROOT/"index.html").read_text(encoding="utf-8")
  css=(ROOT/"vestra-portfolio-v2.css").read_text(encoding="utf-8")
  scoped=css.split("V2.0 portfolio: chapter rhythm",1)[1]
  for marker in ('class="portfolio-chapter-nav"', 'id="portfolioGlance"', 'id="portfolioPositionsChapter"', 'id="portfolioToolsStrip"', 'id="btnPortfolioFilters"', 'id="portfolioTotalValue"'):
   self.assertIn(marker,html)
  for style in (".portfolio-chapter-nav a:focus-visible", "outline:2px", ".portfolio-glance__stat strong", "overflow-wrap:anywhere", "min-height:44px", "@media(max-width:600px)"):
   self.assertIn(style,scoped)
  for hidden in ("display:none","visibility:hidden","pointer-events:none"):
   self.assertNotIn(hidden,scoped)
if __name__=="__main__":unittest.main()
