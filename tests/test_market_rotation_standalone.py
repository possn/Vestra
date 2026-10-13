from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
JS=(ROOT/"market.js").read_text(encoding="utf-8")

class IndependentRotationTests(unittest.TestCase):
    def test_rotation_is_outside_opportunities(self):
        discover=JS.split("function renderDiscover(){",1)[1].split("\n  function low52Stats",1)[0]
        self.assertNotIn("renderWeeklyRotation()",discover)
        self.assertIn("market-rotation-standalone",JS)
        self.assertIn("root.innerHTML = equityRotation +",JS)

    def test_rotation_is_not_gated_by_opportunity_filters(self):
        primary=JS.split("function renderPrimary(){",1)[1].split("\n  const marketSearchSuggestions",1)[0]
        self.assertIn("['discover','lows','smart','watch'].includes(M.mode)",primary)
        self.assertIn("renderWeeklyRotation()",primary)
        self.assertNotIn("M.sector==='all'?renderWeeklyRotation()",JS)

if __name__=="__main__":
    unittest.main()
