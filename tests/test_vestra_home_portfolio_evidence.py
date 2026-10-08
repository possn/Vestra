"""Home portfolio evidence reuses canonical calculation and preserves privacy."""
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
class HomePortfolioEvidenceTest(unittest.TestCase):
    def test_existing_snapshot_fail_closed_and_no_values(self):
        js=(ROOT/'vestra-intelligence-home.js').read_text()
        html=(ROOT/'index.html').read_text()
        self.assertIn('window.VestraDashboardPortfolioConcentration',js)
        self.assertIn('api.concentrationSnapshot(api.marketHoldings())',js)
        self.assertIn('snapshot.count <= 0',js)
        self.assertIn('data-vestra-portfolio-evidence',html)
        self.assertIn('concentração não confirmada',js)
        self.assertNotIn('snapshot.total.toLocaleString',js)
        self.assertIn("params.get('vestra2') === '1'",js)
if __name__=='__main__': unittest.main()
