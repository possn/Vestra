from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class MarketLightSurfaceContrast(unittest.TestCase):
    def test_light_panels_own_dark_ink(self):
        css=(ROOT/"vestra-market-surfaces-v2.css").read_text()
        self.assertIn(".market-analysis-tools__head strong",css)
        self.assertIn(".market-section:has(.vestra-opportunity-lenses) .market-section__head h3",css)
        self.assertIn("color:#173037!important;-webkit-text-fill-color:#173037!important",css)
        self.assertIn(".market-analysis-tools .market-tool-btn",css)
    def test_cache_generation(self):
        html=(ROOT/"index.html").read_text()
        self.assertIn("vestra-market-surfaces-v2.css?v=3",html)
