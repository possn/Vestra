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

    def test_more_sector_select_stays_native_and_tappable(self):
        self.assertIn('function syncMoreSectorVisual()', self.source)
        self.assertIn("s.querySelector('[data-market-sector-select]')", self.source)
        self.assertIn("select.style.pointerEvents='auto'", self.source)
        self.assertNotIn("select.style.pointerEvents='none'", self.source)
        # Cleanup of stale DOM left by older cached builds is allowed, but the
        # control must not read or recreate the old recall mechanism.
        self.assertNotIn('dataset.marketSectorRecall=', self.source)
        self.assertNotIn('dataset.marketSectorRecall||', self.source)
        self.assertNotIn('[data-market-sector-recall]', self.source)
        self.assertNotIn("document.addEventListener('pointerdown'", self.source)

    def test_more_sector_clears_competing_canonical_active_state_before_bridge(self):
        self.assertIn("s.querySelectorAll('[data-market-sector].is-active').forEach", self.source)
        self.assertIn("if(node!==label)node.classList.remove('is-active')", self.source)
        sync = self.source.split('function syncMoreSectorVisual(){', 1)[1].split('function withMoreSectorBridge', 1)[0]
        self.assertLess(sync.index("classList.remove('is-active')"), sync.index("label.classList.toggle('is-active'"))

    def test_more_sector_bridge_is_transient_attribute_during_canonical_refresh(self):
        self.assertIn('function withMoreSectorBridge(callback)', self.source)
        self.assertIn("const label=select?.closest?.('.market-sector-more')", self.source)
        self.assertIn('label.dataset.marketSector=selected', self.source)
        self.assertIn('finally{delete label.dataset.marketSector;}', self.source)
        bridge = self.source.split('function withMoreSectorBridge(callback){', 1)[1].split('function refreshUi', 1)[0]
        self.assertNotIn("document.createElement('span')", bridge)
        self.assertNotIn('prepend(', bridge)
        self.assertIn('withMoreSectorBridge(()=>window.VestraMarketOpportunities?.refresh?.(activeLens))', self.source)
        self.assertIn('withMoreSectorBridge(()=>window.VestraMarketOpportunities?.selectLens?.(activeLens))', self.source)

    def test_more_sector_change_refreshes_without_click_interception(self):
        self.assertIn("document.addEventListener('change',e=>{", self.source)
        self.assertIn("e.target.matches?.('[data-market-sector-select]')", self.source)
        click_block = self.source.split("document.addEventListener('click',e=>{", 1)[1].split('});', 1)[0]
        self.assertNotIn('market-sector-more', click_block)
        self.assertNotIn('preventDefault', click_block.split("const sector=", 1)[1])

    def test_canonical_engine_still_owns_sector_filtering_and_lens_math(self):
        self.assertIn("section.querySelector('[data-market-sector].is-active')", self.opportunities)
        self.assertIn("if(sector!=='all')ranked=ranked.filter", self.opportunities)
        self.assertIn('function rankedCandidates(universe,lens,sector=', self.opportunities)
        self.assertIn('lensEligible(s,lens)', self.opportunities)
        self.assertIn('lensScore(b,lens)-lensScore(a,lens)', self.opportunities)
        self.assertIn("const rows=rankLens(universe,activeLens,{limit:12,sector:sec})", self.opportunities)
        self.assertIn("version:'2.9'", self.source)


if __name__ == '__main__':
    unittest.main(verbosity=2)
