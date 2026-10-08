"""Reuse the existing market signal without a second market fetch."""
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class HomeBarometerTests(unittest.TestCase):
    def test_uses_existing_barometer_only(self):
        js=(ROOT/'vestra-intelligence-home.js').read_text()
        html=(ROOT/'index.html').read_text()
        self.assertIn("vestra:dashboard-signal-updated",js)
        self.assertIn("market-sentiment",js)
        self.assertIn("vestraMarketSentimentCard",js)
        self.assertIn("data-vestra-market-status",html)
        self.assertIn("value < 0 || value > 100",js)
        self.assertNotIn('/market?ticker=',js)
        self.assertIn("params.get('vestra2') !== '0'",js)
        self.assertIn("if (!enabled) return;",js)
        self.assertIn('data-vestra-go="dashboard"',html)
if __name__=='__main__': unittest.main()
