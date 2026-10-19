import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class MobileContrastContractTests(unittest.TestCase):
    def test_stylesheet_is_loaded_after_legacy_overrides(self):
        html=(ROOT/"index.html").read_text()
        self.assertIn('vestra-mobile-contrast-fix.css?v=2',html)
        self.assertGreater(html.index("vestra-mobile-contrast-fix.css"),html.index("vestra-intelligence-balanced-v2.css"))
    def test_four_reported_regions_have_explicit_light_surface_ink(self):
        css=(ROOT/"vestra-mobile-contrast-fix.css").read_text()
        for selector in ("#viewAssets .portfolio-hero h2","#viewCashflow .flow-hero h2",
                         "#viewDashboard.vi-preview-active .v2-home-section-label",
                         "#viewMarket .market-rotation .market-perspective-head h4"):
            self.assertIn(selector,css)
        self.assertIn("-webkit-text-fill-color",css)
        self.assertIn("opacity:1!important",css)

if __name__=="__main__": unittest.main()
