from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class MarketOpportunitySectorRefreshTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / 'market-opportunity-lenses.js').read_text(encoding='utf-8')
        cls.opportunities = (ROOT / 'market-opportunities.js').read_text(encoding='utf-8')
        cls.market = (ROOT / 'market.js').read_text(encoding='utf-8')

    def test_market_js_is_the_single_canonical_sector_owner(self):
        self.assertIn("const sec=e.target.closest('[data-market-sector]')", self.market)
        self.assertIn("M.sector=sec.dataset.marketSector||'all'", self.market)
        self.assertIn("if(e.target.matches('[data-market-sector-select]') && e.target.value){ M.sector=e.target.value; renderPrimary(); }", self.market)
        self.assertNotIn('refreshAfterSectorSelection', self.source)
        self.assertNotIn("window.VestraMarketOpportunities?.refresh?.(activeLens,selected)", self.source)
        self.assertNotIn("const sector=e.target.closest?.('[data-market-sector]')", self.source)

    def test_more_sector_select_stays_native_and_tappable(self):
        self.assertIn('function syncMoreSectorVisual()', self.source)
        self.assertIn("s.querySelector('[data-market-sector-select]')", self.source)
        self.assertIn("select.style.pointerEvents='auto'", self.source)
        self.assertNotIn("select.style.pointerEvents='none'", self.source)
        self.assertNotIn('dataset.marketSectorRecall=', self.source)
        self.assertNotIn('[data-market-sector-recall]', self.source)
        self.assertNotIn("document.addEventListener('pointerdown'", self.source)

    def test_native_change_is_deferred_to_one_canonical_commit(self):
        self.assertIn('const deferredSectorEvents=new WeakSet()', self.source)
        self.assertIn('function deferNativeSectorCommit(event)', self.source)
        self.assertIn("select?.matches?.('[data-market-sector-select]')", self.source)
        self.assertIn('deferredSectorEvents.has(event)', self.source)
        self.assertIn('event.stopImmediatePropagation()', self.source)
        self.assertIn('requestAnimationFrame(()=>requestAnimationFrame(()=>', self.source)
        self.assertIn("const commit=new Event('change',{bubbles:true})", self.source)
        self.assertIn('deferredSectorEvents.add(commit)', self.source)
        self.assertIn('select.dispatchEvent(commit)', self.source)
        self.assertIn("document.addEventListener('change',deferNativeSectorCommit,true)", self.source)

    def test_more_sector_visual_bridge_never_claims_canonical_sector_ownership(self):
        self.assertIn("s.querySelectorAll('[data-market-sector].is-active').forEach", self.source)
        self.assertIn("if(node!==label)node.classList.remove('is-active')", self.source)
        self.assertIn('delete label.dataset.marketSector', self.source)
        self.assertIn('delete label.dataset.marketSectorRecall', self.source)
        self.assertNotIn('label.dataset.marketSector=selected', self.source)
        self.assertNotIn('function withMoreSectorBridge', self.source)

    def test_canonical_opportunity_engine_accepts_explicit_sector_override(self):
        self.assertIn("function opportunities(lens=activeLens,sectorOverride='')", self.opportunities)
        self.assertIn("function selectLens(lens,sectorOverride='')", self.opportunities)
        self.assertIn('return opportunities(activeLens,sectorOverride)', self.opportunities)
        self.assertIn("if(sector!=='all')ranked=ranked.filter", self.opportunities)
        self.assertIn("version:'3.0'", self.source)


if __name__ == '__main__':
    unittest.main(verbosity=2)
