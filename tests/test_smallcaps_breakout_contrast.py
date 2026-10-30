from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class SmallCapLensTests(unittest.TestCase):
 def test_smallcaps_is_only_technical_lens(self):
  market=(ROOT/'market.js').read_text()
  opportunity=(ROOT/'market-opportunities.js').read_text()
  html=(ROOT/'index.html').read_text()
  self.assertNotIn('renderSmallCaps()',market)
  self.assertNotIn('data-market-mode="smallcaps"',html)
  self.assertIn("pre.insertAdjacentElement('afterend',chip)",opportunity)
  self.assertIn("selectLens('smallcap_breakout')",opportunity)
  self.assertIn("if(lens==='smallcap_breakout')return false",opportunity)
if __name__=='__main__':unittest.main()
