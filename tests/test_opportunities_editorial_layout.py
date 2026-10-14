from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
HTML=(ROOT/'index.html').read_text(encoding='utf-8')
CSS=(ROOT/'vestra-opportunities-editorial-v2.css').read_text(encoding='utf-8')
class EditorialOpportunityLayoutTests(unittest.TestCase):
    def test_new_surface_loads_after_shared_market(self):
        self.assertIn('vestra-opportunities-editorial-v2.css?v=1',HTML)
        self.assertLess(HTML.index('vestra-market-surfaces-v2.css?v=11'),HTML.index('vestra-opportunities-editorial-v2.css?v=1'))
    def test_scoped_to_opportunities_and_preserves_all_controls(self):
        self.assertIn('#viewMarket .market-section:has(.vestra-opportunity-lenses)',CSS)
        self.assertIn('.market-row.ux453-opp',CSS)
        self.assertIn('.ux453-entry',CSS)
        self.assertNotIn('display:none',CSS.replace(' ',''))
if __name__=='__main__':unittest.main()
