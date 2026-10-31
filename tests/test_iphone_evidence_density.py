"""Contract: all three mobile Home evidence values remain visible."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class IPhoneEvidenceDensityTests(unittest.TestCase):
    def test_stylesheet_loaded_after_home_styles(self):
        html = (ROOT / "index.html").read_text()
        self.assertIn("vestra-home-iphone-evidence-density.css?v=20261031", html)
        self.assertGreater(html.index("vestra-home-iphone-evidence-density.css"), html.index("vestra-home-first-look-order.css"))

    def test_three_values_remain_readable(self):
        css = (ROOT / "vestra-home-iphone-evidence-density.css").read_text()
        self.assertIn("@media (max-width:760px)", css)
        self.assertIn("repeat(2,minmax(0,1fr))", css)
        self.assertIn(".vi-signal-strip>div:last-child", css)
        self.assertIn("grid-column:1/-1", css)
        self.assertIn("overflow-wrap:anywhere", css)
        self.assertIn("@media (max-width:320px)", css)
        self.assertNotIn("display:none", css)
        self.assertNotIn("visibility:hidden", css)

if __name__ == "__main__":
    unittest.main()
