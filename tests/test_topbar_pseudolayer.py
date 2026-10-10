"""Topbar pseudo-layer must not obscure the global dark brand chrome."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class HeaderChromeTest(unittest.TestCase):
    def test_pseudo_background_inherits_header(self):
        css = (ROOT / "styles.css").read_text(encoding="utf-8")
        start = css.index(".topbar::before {")
        block = css[start:css.index("}", start)]
        self.assertIn("background: inherit;", block)
        self.assertNotIn("background: var(--topbar-bg)", block)

    def test_stylesheet_cache_busted(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertRegex(html, r"styles[.]css[?]v=[a-zA-Z0-9._-]+")

if __name__ == "__main__":
    unittest.main()
