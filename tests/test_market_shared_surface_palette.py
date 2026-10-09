from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class MarketSharedSurfacePalette(unittest.TestCase):
    def test_existing_light_panels_use_shared_tokens(self):
        css=(ROOT/"vestra-market-surfaces-v2.css").read_text()
        for name in ["--vestra-surface-ivory","--vestra-surface-ivory-ink","--vestra-surface-ivory-muted"]:
            self.assertIn("var("+name+")",css)
        for old in ["#f0eee7","#173037","#47605f"]:
            self.assertNotIn(old,css)
    def test_pwa_cache_generation(self):
        self.assertIn("vestra-market-surfaces-v2.css?v=4",(ROOT/"index.html").read_text())
