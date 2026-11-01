"""Portfolio tools chapter preserves native disclosure and routes."""
from pathlib import Path
import unittest
R=Path(__file__).resolve().parents[1]
class PortfolioToolsEditorialTests(unittest.TestCase):
 def test_real_tools_and_layout_contract(self):
  html=(R/"index.html").read_text(encoding="utf-8")
  css=(R/"vestra-portfolio-v2.css").read_text(encoding="utf-8")
  section=css.split("Portfolio 2.0: analysis tools read as a distinct editorial chapter.",1)[1]
  for dom in ('<details class="portfolio-tools" id="portfolioToolsStrip">', "setView('dividends')", "setView('analysis')", 'id="portfolioSectorCard"', 'id="equityPnLContent"'):
   self.assertIn(dom,html)
  for rule in ('#portfolioToolsStrip>summary:focus-visible','min-height:64px','touch-action:manipulation','@media(max-width:600px)'):
   self.assertIn(rule,section)
  for disallowed in ('display:none','visibility:hidden','pointer-events:none'):
   self.assertNotIn(disallowed,section)
if __name__=="__main__":unittest.main()
