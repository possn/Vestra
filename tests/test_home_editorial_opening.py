"""Vestra 2.0: mobile-first Home headline is editorial, without hiding any live content."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class HomeEditorialOpeningTests(unittest.TestCase):
    def test_css_targets_real_live_home_and_keeps_sections_accessible(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        css = (ROOT / "vestra-home-first-look-order.css").read_text(encoding="utf-8")
        segment = css.split("Home 2.0 — editorial opening", 1)[1]
        self.assertIn('class="vi-home-overview"', html)
        self.assertIn('class="vi-headline"', html)
        self.assertIn('class="vi-deck"', html)
        self.assertIn(".vi-home-overview .vi-headline", segment)
        self.assertIn("font-size:clamp(2.15rem,9.4vw,3.65rem)", segment)
        self.assertIn("@media(max-width:760px)", segment)
        for forbidden in ("display:none", "visibility:hidden", "pointer-events:none"):
            self.assertNotIn(forbidden, segment)
        for section in ("vi-context-chapter", "vi-priorities", "vi-risk-reading"):
            self.assertIn(section, html)

if __name__ == "__main__":
    unittest.main()
