"""Manifest icon backwards compatibility."""
import json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class ManifestBrandTests(unittest.TestCase):
    def test_new_svg_with_png_fallbacks(self):
        manifest=json.loads((ROOT/'manifest.webmanifest').read_text())
        icons=manifest['icons']
        self.assertEqual(icons[0]['src'],'vestra-icon-v2.svg')
        for old in ('icon192.png','icon512.png','icon192-maskable.png','icon512-maskable.png'):
            self.assertIn(old,[i['src'] for i in icons])
        mark=(ROOT/'vestra-icon-v2.svg').read_text()
        self.assertIn('viewBox="0 0 512 512"',mark)
        self.assertIn('#f7f5f1',mark)
if __name__=='__main__': unittest.main()
