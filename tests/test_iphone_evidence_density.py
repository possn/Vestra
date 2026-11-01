"""Contract: all three mobile Home evidence values remain visible."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]

class IPhoneEvidenceDensityTests(unittest.TestCase):
    def test_stylesheet_loaded_after_home_styles(self):
        html = (ROOT / "index.html").read_text()
        self.assertIn("vestra-home-iphone-evidence-density.css?v=20261101-live-pulse", html)
        self.assertGreater(html.index("vestra-home-iphone-evidence-density.css"), html.index("vestra-home-first-look-order.css"))

    def test_three_values_remain_readable(self):
        css = (ROOT / "vestra-home-iphone-evidence-density.css").read_text()
        self.assertIn("@media (max-width:760px)", css)
        self.assertIn("repeat(2,minmax(0,1fr))", css)
        self.assertIn(".vi-live-pulse>div:last-child", css)
        self.assertIn(".vi-live-pulse>div :is(small,strong,span)", css)
        self.assertNotIn(".vi-signal-strip", css)
        self.assertIn("grid-column:1/-1", css)
        self.assertIn("overflow-wrap:anywhere", css)
        self.assertIn("@media (max-width:320px)", css)
        self.assertNotIn("display:none", css)
        self.assertNotIn("visibility:hidden", css)


    def test_selector_matches_actual_three_live_home_signals(self):
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        home = html.split('<section id="vestraIntelligenceHome"', 1)[1].split('<div class="vi-back-to-intelligence">', 1)[0]
        pulse = re.search(r'<div class="vi-live-pulse"[^>]*>(.*?)</section>', home, re.S)
        self.assertIsNotNone(pulse, "Home must contain the live pulse targeted by CSS")
        self.assertEqual(pulse.group(1).count("<div>"), 3)
        for hook in ("data-vi-pulse-cnn", "data-vi-pulse-aaii", "data-vi-pulse-coverage"):
            self.assertIn(hook, pulse.group(1))

if __name__ == "__main__":
    unittest.main()
