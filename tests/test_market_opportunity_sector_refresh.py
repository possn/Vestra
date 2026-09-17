from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class MarketOpportunitySectorRefreshTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / 'market-opportunity-lenses.js').read_text(encoding='utf-8')
        cls.opportunities = (ROOT / 'market-opportunities.js').read_text(encoding='utf-8')
        cls.market = (ROOT / 'market.js').read_text(encoding='utf-8')

    def test_market_js_remains_the_canonical_sector_owner(self):
        self.assertIn("[data-market-sector]", self.market)
        self.assertIn("M.sector=sec.dataset.marketSector", self.market)
        self.assertIn("[data-market-sector-select]", self.market)
        self.assertIn("M.sector=e.target.value", self.market)
        self.assertNotIn('refreshAfterSectorSelection', self.source)
        self.assertNotIn("VestraMarketOpportunities?.refresh?.", self.source)

    def test_native_picker_change_is_deferred_before_canonical_commit(self):
        self.assertIn('function deferNativeSectorCommit(event)', self.source)
        self.assertIn('event.stopImmediatePropagation()', self.source)
        self.assertIn('requestAnimationFrame(()=>requestAnimationFrame(()=>', self.source)
        self.assertIn("new Event('change',{bubbles:true})", self.source)
        self.assertIn('select.dispatchEvent(commit)', self.source)
        self.assertIn("document.addEventListener('change',deferNativeSectorCommit,true)", self.source)

    def test_visual_bridge_keeps_native_select_tappable_without_owning_sector(self):
        self.assertIn("select.style.pointerEvents='auto'", self.source)
        self.assertNotIn("select.style.pointerEvents='none'", self.source)
        self.assertIn('delete label.dataset.marketSector', self.source)
        self.assertNotIn('label.dataset.marketSector=selected', self.source)

    def test_opportunity_engine_accepts_explicit_sector_override(self):
        self.assertIn("sectorOverride=''", self.opportunities)
        self.assertIn('opportunities(activeLens,sectorOverride)', self.opportunities)
        self.assertIn("if(sector!=='all')ranked=ranked.filter", self.opportunities)


if __name__ == '__main__':
    unittest.main(verbosity=2)
