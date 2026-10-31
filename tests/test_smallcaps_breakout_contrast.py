import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class SmallCapLens(unittest.TestCase):
 def test_no_inventory_and_research_lens(self):
  m=(ROOT/'market.js').read_text()
  o=(ROOT/'market-opportunities.js').read_text()
  h=(ROOT/'index.html').read_text()
  self.assertNotIn('renderSmallCaps()',m)
  self.assertNotIn('data-market-mode="smallcaps"',h)
  self.assertIn("selectLens('smallcap_breakout')",o)
  self.assertIn("if(lens==='smallcap_breakout')return breakoutSetup(s,'smallcap_breakout')!=null",o)
  self.assertIn('smallcapFeed=new Map()',o)
  self.assertIn('loadSmallcapFeed()',o)
if __name__=='__main__':unittest.main()
