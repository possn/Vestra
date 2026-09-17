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
        self.assertIn('window.VestraMarketOpportunities?.refresh?.(activeLens,moreSectorValue())', self.source)

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

    def test_more_sector_clears_competing_canonical_active_state(self):
        self.assertIn("s.querySelectorAll('[data-market-sector].is-active').forEach", self.source)
        self.assertIn("if(node!==label)node.classList.remove('is-active')", self.source)
        sync = self.source.split('function syncMoreSectorVisual(){', 1)[1].split('function refreshUi', 1)[0]
        self.assertLess(sync.index("classList.remove('is-active')"), sync.index("label.classList.toggle('is-active'"))

    def test_more_sector_is_passed_explicitly_without_dom_bridge(self):
        self.assertIn('function moreSectorValue()', self.source)
        self.assertIn("querySelector('[data-market-sector-select]')?.value", self.source)
        self.assertIn('window.VestraMarketOpportunities?.refresh?.(activeLens,moreSectorValue())', self.source)
        self.assertIn('window.VestraMarketOpportunities?.selectLens?.(activeLens,moreSectorValue())', self.source)
        self.assertNotIn('function withMoreSectorBridge', self.source)
        self.assertNotIn('label.dataset.marketSector=selected', self.source)

    def test_more_sector_change_refreshes_without_click_interception(self):
        self.assertIn("document.addEventListener('change',e=>{", self.source)
        self.assertIn("e.target.matches?.('[data-market-sector-select]')", self.source)
        click_block = self.source.split("document.addEventListener('click',e=>{", 1)[1].split('});', 1)[0]
        self.assertNotIn('market-sector-more', click_block)
        self.assertNotIn('preventDefault', click_block.split("const sector=", 1)[1])

    def test_canonical_engine_accepts_explicit_sector_override_and_owns_filtering(self):
        self.assertIn("function opportunities(lens=activeLens,sectorOverride='')", self.opportunities)
        self.assertIn("const sec=t(sectorOverride)||t(active?.dataset.marketSector)||'all'", self.opportunities)
        self.assertIn("function selectLens(lens,sectorOverride='')", self.opportunities)
        self.assertIn('return opportunities(activeLens,sectorOverride)', self.opportunities)
        self.assertIn("if(sector!=='all')ranked=ranked.filter", self.opportunities)
        self.assertIn('function rankedCandidates(universe,lens,sector=', self.opportunities)
        self.assertIn('lensEligible(s,lens)', self.opportunities)
        self.assertIn('lensScore(b,lens)-lensScore(a,lens)', self.opportunities)
        self.assertIn("const rows=rankLens(universe,activeLens,{limit:12,sector:sec})", self.opportunities)
        self.assertIn("version:'2.9'", self.source)


if __name__ == '__main__':
    unittest.main(verbosity=2)
