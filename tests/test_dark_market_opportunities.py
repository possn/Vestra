from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
CSS=(ROOT/'vestra-market-surfaces-v2.css').read_text(encoding='utf-8')
HTML=(ROOT/'index.html').read_text(encoding='utf-8')
class MarketDarkOpportunities(unittest.TestCase):
    def test_dark_override_is_last_and_scoped(self):
        marker='/* Vestra 2.0: deep-petrol Opportunities'
        self.assertIn(marker,CSS)
        dark=CSS.split(marker,1)[1]
        self.assertIn('.market-section:has(.vestra-opportunity-lenses)',dark)
        self.assertIn('background:#0b2926!important',dark)
        self.assertIn('background:#123b35!important',dark)
        self.assertIn('color:#f4f0e7!important',dark)
        self.assertIn('vestra-low52-contrast',dark)
    def test_cache_bump(self):
        self.assertIn('vestra-market-surfaces-v2.css?v=13-iphone-density',HTML)
if __name__=='__main__':unittest.main()
