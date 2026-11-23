from pathlib import Path
import unittest
from _css_contrast import assert_contrast, tokens
ROOT=Path(__file__).resolve().parents[1]
class MarketLightSurfaceContrast(unittest.TestCase):
    def test_light_panels_own_dark_ink(self):
        css=(ROOT/"vestra-market-surfaces-v2.css").read_text()
        self.assertIn(".market-analysis-tools__head strong",css)
        self.assertIn(".market-section:has(.vestra-opportunity-lenses) .market-section__head h3",css)
        self.assertIn(".market-analysis-tools .market-tool-btn",css)
        pre="body:has(#viewMarket:not([hidden])) #viewMarket "
        ivory=tokens()["--vestra-surface-ivory"]
        # Analysis tools stay on the light surface; the opportunities section is
        # now deep petrol (#0b2926) with light ink. Each pairing is computed.
        assert_contrast(self,css,pre+".market-analysis-tools__head strong",ivory)
        lens=pre+".market-section:has(.vestra-opportunity-lenses) "
        assert_contrast(self,css,lens+".market-section__head h3","#0b2926")
        assert_contrast(self,css,lens+".market-section__head p","#0b2926")
        assert_contrast(self,css,"body:has(#viewMarket:not([hidden])) #viewMarket .market-analysis-tools .market-tool-btn","#153c35")
    def test_cache_generation(self):
        html=(ROOT/"index.html").read_text()
        self.assertIn("vestra-market-surfaces-v2.css?v=",html)
