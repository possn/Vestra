from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class MarketOpportunitySectorRefreshTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / 'market-opportunity-lenses.js').read_text(encoding='utf-8')
        cls.opportunities = (ROOT / 'market-opportunities.js').read_text(encoding='utf-8')

    def test_sector_click_refreshes_canonical_opportunity_ranking(self):
        self.assertIn("[data-market-sector]", self.source)
        self.assertIn('refreshAfterSectorSelection()', self.source)
        self.assertIn('requestAnimationFrame(()=>{', self.source)
        self.assertIn('window.VestraMarketOpportunities?.refresh?.(activeLens)', self.source)

    def test_refresh_runs_after_sector_owner_updates_active_class(self):
        click_block = self.source.split("document.addEventListener('click',e=>{", 1)[1].split('});', 1)[0]
        self.assertIn("e.target.closest?.('[data-market-sector]')", click_block)
        self.assertIn('refreshAfterSectorSelection()', click_block)
        self.assertNotIn('classList.toggle', click_block)

    def test_canonical_engine_still_owns_sector_filtering_and_lens_math(self):
        self.assertIn("section.querySelector('[data-market-sector].is-active')", self.opportunities)
        self.assertIn("if(sector!=='all')ranked=ranked.filter", self.opportunities)
        self.assertIn('function rankedCandidates(universe,lens,sector=', self.opportunities)
        self.assertIn('lensEligible(s,lens)', self.opportunities)
        self.assertIn('lensScore(b,lens)-lensScore(a,lens)', self.opportunities)
        self.assertIn("const rows=rankLens(universe,activeLens,{limit:12,sector:sec})", self.opportunities)
        self.assertIn("version:'2.1'", self.source)


if __name__ == '__main__':
    unittest.main(verbosity=2)
