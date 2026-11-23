from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class MarketSharedSurfacePalette(unittest.TestCase):
    def test_existing_light_panels_use_shared_tokens(self):
        css=(ROOT/"vestra-market-surfaces-v2.css").read_text()
        for name in ["--vestra-surface-ivory","--vestra-surface-ivory-ink","--vestra-surface-ivory-muted"]:
            self.assertIn("var("+name+")",css)
        # Light panels must consume tokens; the only literal ivory allowed is the
        # single documented search-field surface.
        self.assertLessEqual(css.count("#f0eee7"),1)
        self.assertNotIn("#47605f",css)
    def test_pwa_cache_generation(self):
        self.assertIn("vestra-market-surfaces-v2.css?v=",(ROOT/"index.html").read_text())
