"""Capital-first portfolio layout reuses canonical live values."""
from pathlib import Path
import unittest
R=Path(__file__).resolve().parents[1]
class PortfolioCompositionTests(unittest.TestCase):
 def test_real_hosts_and_responsive_css(self):
  html=(R/"index.html").read_text(encoding="utf-8")
  css=(R/"vestra-portfolio-v2.css").read_text(encoding="utf-8")
  part=css.split("Capital-first portfolio composition:",1)[1]
  for marker in ('id="portfolioTotalValue"','id="portfolioPositionCount"','id="portfolioTopClass"','id="portfolioIncomeStrip"','id="portfolioPositionsChapter"'):
   self.assertIn(marker,html)
  for rule in ("@media(min-width:900px)","grid-template-columns:minmax(0,2fr) repeat(2,minmax(0,1fr))","grid-column:1 / 2","@media(max-width:899px)","grid-column:1 / -1"):
   self.assertIn(rule,part)
  for forbidden in ("display:none","visibility:hidden","pointer-events:none"):
   self.assertNotIn(forbidden,part)
if __name__=="__main__":unittest.main()
