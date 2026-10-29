from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]

class BreakoutTitleContrast(unittest.TestCase):
    def test_actual_breakout_lens_marks_section_and_uses_light_ink(self):
        code=(ROOT/"market-opportunities.js").read_text(encoding="utf-8")
        css=(ROOT/"vestra-smallcaps-contrast.css").read_text(encoding="utf-8")
        self.assertIn("section.classList.toggle('vestra-breakout-contrast',activeLens==='breakout')",code)
        self.assertIn(".market-section.vestra-breakout-contrast .market-section__head",css)
        self.assertIn("-webkit-text-fill-color:#f7f5ed!important",css)
        self.assertIn("-webkit-text-fill-color:#c4d9d1!important",css)
    def test_small_caps_render_real_index_not_predicted_breakouts(self):
        code=(ROOT/"market.js").read_text(encoding="utf-8")
        self.assertIn("M.mode==='smallcaps'?renderSmallCaps()",code)
        self.assertIn("cap>=100_000_000 && cap<=2_000_000_000",code)
        self.assertIn("não são breakouts confirmados",code)

if __name__=="__main__":
    unittest.main()
