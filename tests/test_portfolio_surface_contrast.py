from pathlib import Path
import unittest
from _css_contrast import assert_contrast, tokens
ROOT=Path(__file__).resolve().parents[1]
class PortfolioSurfaceContrast(unittest.TestCase):
    def test_dark_hero_and_light_kpi_ink_are_separate(self):
        css=(ROOT/"vestra-portfolio-v2.css").read_text()
        t=tokens()
        dark=t["--vestra-surface-petrol"]; light=t["--vestra-surface-ivory"]
        self.assertIn("#viewAssets .portfolio-glance__stat strong,",css)
        self.assertIn("#viewAssets .portfolio-income-strip>div:first-child strong",css)
        assert_contrast(self,css,"#viewAssets .portfolio-glance__main strong",dark)
        assert_contrast(self,css,"#viewAssets .portfolio-glance__stat strong",light)
        assert_contrast(self,css,"#viewAssets .portfolio-income-strip>div:first-child strong",light)
    def test_generation(self):
        self.assertIn("vestra-portfolio-v2.css?v=",(ROOT/"index.html").read_text())
