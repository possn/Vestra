from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
def read(p): return (ROOT/p).read_text(encoding="utf-8")
class QuoteErrorClassifierTests(unittest.TestCase):
    def test_classifier_has_actionable_buckets(self):
        s=read("app-quote-errors.js")
        for token in ("Sem dados Yahoo","Ticker / identidade","Delisted / ignorado","Rede / Worker","Sanity de preço","summarizeQuoteErrors"):
            self.assertIn(token,s)
    def test_app_uses_classifier_only_for_diagnostics(self):
        app=read("app.js")
        self.assertIn("window.VestraQuoteErrors",app)
        self.assertIn("Categoria:</b>",app)
        self.assertIn("summarizeQuoteErrors(errors || [])",app)
        self.assertNotIn("classifyQuoteError(asset",app)
    def test_quote_modal_bridge_is_event_driven(self):
        app=read("app.js")
        module=read("app-quote-errors.js")
        self.assertIn('vestra:modal-opened',app)
        self.assertIn("window.addEventListener('vestra:modal-opened'",module)
        self.assertNotIn('new MutationObserver',module)
        self.assertNotIn("document.addEventListener('click',forceCloseQuoteErrorsModal,true)",module)
        self.assertIn("modal.querySelectorAll('[data-close=\"modalQuoteErrors\"]')",module)
        self.assertIn("version:'1.4'",module)

    def test_module_load_order_and_cache(self):
        idx=read("index.html")
        self.assertLess(idx.index('src="app-quote-errors.js'),idx.index('src="app.js'))
        sw=read("sw.js")
        self.assertIn('const CACHE_NAME = "vestra-cache-',sw)
        self.assertIn("staleWhileRevalidate",sw)
        self.assertIn('./app-quote-errors.js',sw)
        self.assertIn('./market-live-overlay.js',sw)
if __name__=='__main__': unittest.main(verbosity=2)
