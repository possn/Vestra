"""Vestra 2.0: single Home and unified navigation chrome contracts."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]

class CanonicalHomeTest(unittest.TestCase):
    def test_detail_mode_hides_duplicate_editorial_home(self):
        css = (ROOT / "vestra-intelligence.css").read_text(encoding="utf-8")
        self.assertIn('data-legacy-open="true"]) .v2-home-intro', css)
        self.assertIn('data-legacy-open="true"]) .v2-home-stage__aside', css)
        self.assertIn('data-legacy-open="true"]) .vi-back-to-intelligence', css)

    def test_detail_entry_scrolls_to_visible_context(self):
        js = (ROOT / "vestra-intelligence-home.js").read_text(encoding="utf-8")
        self.assertIn("document.querySelector('#viewDashboard .vi-back-to-intelligence')", js)
        self.assertNotIn("const legacy = document.querySelector('#viewDashboard .dashboard-welcome');", js)

    def test_unified_sidebar_and_cache_generation(self):
        nav = (ROOT / "vestra-navigation-v2.css").read_text(encoding="utf-8")
        html = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn('.sidebar{background:#0d2523!important', nav)
        self.assertIn('vestra-navigation-v2.css?v=6', html)
        self.assertIn('vestra-intelligence.css?v=19', html)
        self.assertIn('vestra-intelligence-home.js?v=12', html)

if __name__ == "__main__":
    unittest.main()
