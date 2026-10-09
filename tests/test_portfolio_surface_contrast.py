from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class PortfolioSurfaceContrast(unittest.TestCase):
    def test_dark_hero_and_light_kpi_ink_are_separate(self):
        css=(ROOT/"vestra-portfolio-v2.css").read_text()
        self.assertIn("#viewAssets .portfolio-glance__stat strong,",css)
        self.assertIn("color:#18343a!important;-webkit-text-fill-color:#18343a!important",css)
        self.assertIn("#viewAssets .portfolio-glance__main strong",css)
        self.assertIn("color:#fff!important;-webkit-text-fill-color:#fff!important",css)
        self.assertIn("#viewAssets .portfolio-income-strip>div:first-child strong",css)
    def test_generation(self):
        self.assertIn("vestra-portfolio-v2.css?v=4",(ROOT/"index.html").read_text())
