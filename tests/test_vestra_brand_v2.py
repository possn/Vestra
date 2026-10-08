"""Contract for the Vestra brand refresh."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
class BrandV2Tests(unittest.TestCase):
    def test_brand_asset_is_wired_to_header_splash_and_icon(self):
        html=(ROOT/"index.html").read_text(encoding="utf-8")
        mark=(ROOT/"vestra-mark-v2.svg").read_text(encoding="utf-8")
        self.assertEqual(html.count('src="vestra-mark-v2.svg"'),2)
        self.assertIn('href="vestra-mark-v2.svg?v=2"',html)
        self.assertIn('viewBox="0 0 256 256"',mark)
        self.assertIn("<title id=\"title\">Vestra</title>",mark)
        self.assertIn('apple-touch-icon.png', html) # PWA bitmap migration is separate
if __name__=="__main__": unittest.main()
