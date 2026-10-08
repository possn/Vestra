"""Vestra minimal brand wiring contract."""
from pathlib import Path
import unittest
ROOT = Path(__file__).resolve().parents[1]
class MinimalBrandTests(unittest.TestCase):
    def test_splash_header_and_favicon(self):
        html=(ROOT/'index.html').read_text(encoding='utf-8')
        svg=(ROOT/'vestra-minimal-mark.svg').read_text(encoding='utf-8')
        self.assertEqual(html.count('src="vestra-minimal-mark.svg"'), 2)
        self.assertIn('href="vestra-minimal-mark.svg?v=1"',html)
        self.assertIn('viewBox="0 0 256 256"',svg)
        self.assertNotIn('linearGradient',svg)
        self.assertIn('apple-touch-icon.png',html)
if __name__=='__main__': unittest.main()
