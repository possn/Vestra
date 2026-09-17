from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class MarketOpportunityLensesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / 'market-opportunity-lenses.js').read_text(encoding='utf-8')
        cls.css = (ROOT / 'market-opportunity-lenses.css').read_text(encoding='utf-8')
        cls.sw = (ROOT / 'sw.js').read_text(encoding='utf-8')

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
        self.assertIn("version:'3.0'", self.source)
        self.assertIn('"./market-opportunity-lenses.css"', self.sw)


if __name__ == '__main__':
    unittest.main(verbosity=2)
