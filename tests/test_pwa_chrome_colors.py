import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class PwaChromeColors(unittest.TestCase):
    def test_shell_matches_canonical_topbar(self):
        manifest=json.loads((ROOT/"manifest.webmanifest").read_text())
        html=(ROOT/"index.html").read_text()
        self.assertEqual(manifest["theme_color"],"#081a1a")
        self.assertEqual(manifest["background_color"],"#081a1a")
        self.assertIn('<meta content="#081a1a" name="theme-color"/>',html)
