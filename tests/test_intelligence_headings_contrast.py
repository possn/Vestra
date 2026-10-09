from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class IntelligenceHeadingContrast(unittest.TestCase):
    def test_canonical_dark_surface_text_has_explicit_light_foreground(self):
        css = (ROOT / "vestra-intelligence.css").read_text()
        self.assertIn("#viewDashboard #vestraIntelligenceHome .vi-daily-heading h3", css)
        self.assertIn("color:#f5efe5!important;-webkit-text-fill-color:#f5efe5!important;", css)
        self.assertIn("color:#c1d3c8!important;-webkit-text-fill-color:#c1d3c8!important;", css)

    def test_cache_generation(self):
        html = (ROOT / "index.html").read_text()
        self.assertIn("vestra-intelligence.css?v=18", html)
