from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class MarketSearchAndDiscoveryContrast(unittest.TestCase):
 def test_targeted_market_foregrounds(self):
  css=(ROOT/"vestra-market-surfaces-v2.css").read_text()
  for selector in [".market-search input::placeholder",".market-search__icon",".market-discover-section .ux453-opp .market-row__ticker",".market-discover-section .ux453-opp .market-row__name",".market-discover-section .ux453-opp .market-row__description",".market-discover-section .ux453-opp .ux453-entry strong"]:
   self.assertIn(selector,css)
  self.assertIn("vestra-market-surfaces-v2.css?v=7",(ROOT/"index.html").read_text())
 def test_discovery_markup_owners(self):
  js=(ROOT/"market-opportunities.js").read_text()
  for cls in ["ux453-opp","market-row__ticker","market-row__name","ux453-entry","ux453-why__row"]:
   self.assertIn(cls,js)
