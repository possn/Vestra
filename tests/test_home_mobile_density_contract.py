"""Home cards stay compact on iPhone without hiding live modules."""
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
CSS=(ROOT/"vestra-home-mobile-editorial.css").read_text(encoding="utf-8")
HTML=(ROOT/"index.html").read_text(encoding="utf-8")
class MobileHomeDensityContract(unittest.TestCase):
    def test_scoped_mobile_density_and_cache_bust(self):
        self.assertIn("@media (max-width:760px)", CSS)
        self.assertIn("vestra-home-mobile-editorial.css?v=20261108-compact-cards", HTML)
        self.assertIn(".vi-market-reading .vi-market-reading-body", CSS)
        self.assertIn(".vi-news-reading .vi-editorial-tile", CSS)
        self.assertIn(".vi-events-reading .vi-editorial-rail", CSS)
        self.assertIn(".vi-shell>.vi-priorities .vi-action", CSS)
    def test_cards_preserve_visibility_and_touch_targets(self):
        section=CSS.split("/* Vestra 2.0 — dense iPhone editorial surface.")[1]
        self.assertNotIn("display:none", section.replace(" ",""))
        self.assertNotIn("visibility:hidden", section.replace(" ",""))
        self.assertNotIn("line-clamp", section)
        self.assertIn("min-height:44px!important",section)
if __name__=="__main__":unittest.main()
