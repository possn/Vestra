from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class MarketOpportunityLensesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / 'market-opportunity-lenses.js').read_text(encoding='utf-8')
        cls.css = (ROOT / 'market-opportunity-lenses.css').read_text(encoding='utf-8')
        cls.sw = (ROOT / 'sw.js').read_text(encoding='utf-8')

    def test_single_technical_lens_row_and_factual_scanner_entry(self):
        index = (ROOT / 'index.html').read_text(encoding='utf-8')
        opportunities = (ROOT / 'market-opportunities.js').read_text(encoding='utf-8')
        self.assertIn('data-market-tool="scanner"', index)
        self.assertIn('<strong>Scanner</strong>', index)
        self.assertNotIn('<strong>Breakout Lab</strong>', index)
        self.assertIn("const pre=section.querySelector('[data-vestra-lens=", opportunities)
        self.assertNotIn("const pre=[...document.querySelectorAll('button')]", opportunities)
        self.assertIn("const smallcap=s.querySelector('[data-smallcap-prebreakout-lens]')", self.source)
        self.assertIn("s.querySelector('.vestra-technical-lenses')?.remove()", self.source)
        self.assertIn("section.classList.toggle('vestra-technical-empty'", opportunities)
        self.assertIn(".market-section.vestra-technical-empty .market-sector-grid", self.css)
        self.assertIn("color:#f1f4ee!important", self.css)

    def test_static_styles_have_single_css_owner(self):
        self.assertIn("market-opportunity-lenses.css?v=1.0", self.source)
        self.assertNotIn("document.createElement('style')", self.source)
        self.assertNotIn('style.textContent', self.source)
        self.assertIn('.vestra-opportunity-lenses{', self.css)
        self.assertIn('.vestra-opportunity-lenses button.is-active{', self.css)
        self.assertIn('.vestra-lens-empty{', self.css)

    def test_runtime_behavior_and_offline_reachability_are_preserved(self):
        self.assertIn("window.VestraMarketOpportunities?.selectLens?.(activeLens,moreSectorValue())", self.source)
        self.assertIn("function deferNativeSectorCommit(event)", self.source)
        self.assertIn("event.stopImmediatePropagation()", self.source)
        self.assertIn("requestAnimationFrame(()=>requestAnimationFrame(()=>", self.source)
        self.assertIn("deferredSectorEvents.add(commit)", self.source)
        self.assertIn("live.dispatchEvent(commit)", self.source)
        self.assertIn("document.addEventListener('change',deferNativeSectorCommit,true)", self.source)
        self.assertNotIn("window.VestraMarketOpportunities?.refresh?.(activeLens,selected)", self.source)
        self.assertNotIn("refreshAfterSectorSelection", self.source)
        self.assertIn("version:'3.2'", self.source)
        self.assertIn("const root=document.getElementById('marketPrimary');if(!root)return", self.source)
        self.assertIn("observer.observe(root,{childList:true,subtree:true})", self.source)
        self.assertNotIn("observe(document.body", self.source)
        self.assertIn('"./market-opportunity-lenses.css"', self.sw)


if __name__ == '__main__':
    unittest.main(verbosity=2)
