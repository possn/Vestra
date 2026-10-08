"""Minimal palette regression contract."""
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class MinimalPaletteTests(unittest.TestCase):
    def test_preview_only_and_brand_asset_remains(self):
        css=(ROOT/'vestra-intelligence.css').read_text(encoding='utf-8')
        html=(ROOT/'index.html').read_text(encoding='utf-8')
        self.assertIn('/* Vestra 2.0 minimal brand palette',css)
        self.assertIn('[data-vestra-intelligence="1"][data-theme="dark"]',css)
        self.assertIn('--vi-accent: #827769;',css)
        self.assertIn('src="vestra-minimal-mark.svg"',html)
        self.assertIn('id="vestraIntelligenceHome"',html)
if __name__=='__main__': unittest.main()
