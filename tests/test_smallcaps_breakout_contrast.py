from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class BreakoutTitleContrast(unittest.TestCase):
    def test_breakout_lens_keeps_contrast(self):
        code=(ROOT/"market-opportunities.js").read_text()
        self.assertIn("section.classList.toggle('vestra-breakout-contrast',activeLens==='breakout')",code)
    def test_small_caps_uses_closable_tool_not_inventory(self):
        code=(ROOT/"market.js").read_text()
        html=(ROOT/"index.html").read_text()
        self.assertIn("function renderSmallCapBreakout()",code)
        self.assertIn("if(tool==='smallcap-breakout') c.innerHTML=renderSmallCapBreakout()",code)
        self.assertIn('data-market-tool="smallcap-breakout"',html)
        self.assertNotIn("renderSmallCaps()",code)
        self.assertIn("data-market-close",code)
if __name__=="__main__":unittest.main()
