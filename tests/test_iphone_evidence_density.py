"""Contract for the mobile editorial evidence strip (presentation only)."""
from pathlib import Path
import re
import unittest

ROOT=Path(__file__).resolve().parents[1]

class IPhoneEvidenceDensityTests(unittest.TestCase):
    def test_mobile_stylesheet_is_loaded_last(self):
        html=(ROOT/"index.html").read_text()
        self.assertIn("vestra-home-iphone-evidence-density.css?v=20261029",html)
        self.assertGreater(
            html.index("vestra-home-iphone-evidence-density.css"),
            html.index("vestra-home-first-look-order.css")
        )

    def test_three_evidence_values_remain_present_and_readable(self):
        css=(ROOT/"vestra-home-iphone-evidence-density.css").read_text()
        self.assertIn("@media (max-width: 760px)",css)
        self.assertIn("grid-template-columns:repeat(2,minmax(0,1fr))",css)
        self.assertIn(".vi-signal-strip>div:last-child",css)
        self.assertIn("grid-column:1/-1",css)
        self.assertIn("overflow-wrap:anywhere",css)
        self.assertIn("@media (max-width: 320px)",css)
        self.assertNotRegex(css,re.compile(r"\bdisplay\s*:\s*none\b"))
        self.assertNotIn("visibility:hidden",css)

if __name__=="__main__":
    unittest.main()
