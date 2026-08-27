from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
def read(p): return (ROOT/p).read_text(encoding="utf-8")

class AppMarketClientTests(unittest.TestCase):
    def test_client_owns_batch_transport_fx_and_concurrency(self):
        s=read("app-market-client.js")
        for token in (
            "async function fetchQuote",
            "async function fetchQuotesBatch",
            "async function fetchFxRates",
            "async function mapWithConcurrency",
            "FX_FALLBACK_LOCAL",
            "timeoutMs=7000",
            "AbortSignal.timeout(timeoutMs)",
            "method:'POST'",
            "JSON.stringify({tickers:chunk})",
            "i+=80",
        ):
            self.assertIn(token,s)
        self.assertIn("`${base}/quotes`",s)
        self.assertIn("[404,405,501].includes(resp.status)",s)
        self.assertIn("unsupported=true",s)
        self.assertIn("window.VestraMarketClient",s)

    def test_app_imports_client_without_duplicate_implementations(self):
        app=read("app.js")
        self.assertIn("window.VestraMarketClient",app)
        self.assertNotIn("async function fetchQuote(ticker, workerUrl)",app)
        self.assertNotIn("async function fetchQuotesBatch(tickers, workerUrl",app)
        self.assertNotIn("async function mapWithConcurrency(items, concurrency, fn)",app)
        self.assertIn("fetchFxRates(ccysNeeded, workerUrl, FX_FALLBACK_LOCAL)",app)
        self.assertIn("FX_FALLBACK_LOCAL[ccy] || 1",app)

    def test_client_loads_before_app_and_is_cached(self):
        index=read("index.html")
        self.assertLess(index.index('src="app-market-client.js'),index.index('src="app.js'))
        self.assertIn('app-market-client.js?v=1.1',index)
        self.assertIn('app.js?v=20260827v22',index)
        sw=read("sw.js")
        self.assertIn("Vestra Service Worker v10.11",sw)
        self.assertIn("vestra-cache-v125",sw)
        self.assertIn('./app-market-client.js',sw)

    def test_quote_error_sheet_does_not_use_generic_body_lock(self):
        app=read("app.js")
        self.assertIn("function closeQuoteErrorDetails()",app)
        self.assertIn("overflow-y:auto",app)
        self.assertIn("-webkit-overflow-scrolling:touch",app)
        self.assertIn("document.body.classList.remove('modal-open')",app)
        self.assertNotIn("openModal('modalQuoteErrors')",app)

if __name__=='__main__': unittest.main(verbosity=2)
