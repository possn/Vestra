from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class MarketSearchAndDiscoveryContrast(unittest.TestCase):
 def test_targeted_market_foregrounds(self):
  css=(ROOT/"vestra-market-surfaces-v2.css").read_text()
  for selector in [".market-search input::placeholder",".market-search__icon",".market-discover-section .ux453-opp .market-row__ticker",".market-discover-section .ux453-opp .market-row__name",".market-discover-section .ux453-opp .market-row__description",".market-discover-section .ux453-opp .ux453-entry strong"]:
   self.assertIn(selector,css)
  self.assertIn("vestra-market-surfaces-v2.css?v=9",(ROOT/"index.html").read_text())
 def test_discovery_markup_owners(self):
  js=(ROOT/"market-opportunities.js").read_text()
  for cls in ["ux453-opp","market-row__ticker","market-row__name","ux453-entry","ux453-why__row"]:
   self.assertIn(cls,js)

 def test_search_has_single_canonical_contrast_rule(self):
  css=(ROOT/"vestra-market-surfaces-v2.css").read_text()
  prefix="body:has(#viewMarket:not([hidden])) #viewMarket "
  for selector in [".market-search input{", ".market-search input::placeholder{", ".market-search__icon{"]:
   self.assertEqual(css.count(prefix+selector),1,selector)
  self.assertIn("background:#f0eee7;color:#173037",css)
  self.assertIn("color:#536965;opacity:1",css)
  self.assertIn("color:#49645e;opacity:1",css)
