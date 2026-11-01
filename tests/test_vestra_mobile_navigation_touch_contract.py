"""Protect iPhone navigation targets across canonical Vestra routes."""
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class NavigationTouchContractTests(unittest.TestCase):
    def test_actual_navigation_dom_has_touch_contract(self):
        html=(ROOT/"index.html").read_text(encoding="utf-8")
        css=(ROOT/"vestra-navigation-v2.css").read_text(encoding="utf-8")
        section=css.split("Canonical iPhone navigation: predictable touch targets",1)[1]
        for anchor in ('class="bottomnav"', 'class="navbtn', 'id="btnSearchToggle"', 'id="btnFab"'):
            self.assertIn(anchor,html)
        for rule in (".bottomnav .navbtn", "#btnSearchToggle", "#btnFab", ".sidebar__close", "min-width:44px", "min-height:44px", ":focus-visible"):
            self.assertIn(rule,section)
        for forbidden in ("display:none","visibility:hidden","pointer-events:none","position:fixed"):
            self.assertNotIn(forbidden,section)
if __name__=="__main__": unittest.main()
