from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
def read(p): return (ROOT/p).read_text(encoding="utf-8")

class AppMarketClientTests(unittest.TestCase):
    def test_client_owns_transport_fx_and_ios_safe_concurrency(self):
        s=read("app-market-client.js")
        for token in (
            "async function fetchQuote",
            "async function fetchQuotesBatch",
            "async function fetchFxRates",
            "async function mapWithConcurrency",
            "FX_FALLBACK_LOCAL",
            "MAX_QUOTE_CONCURRENCY = 4",
            "DEFAULT_QUOTE_TIMEOUT_MS = 12000",
            "async function fetchWithTimeout",
            "new AbortController()",
            "controller.abort()",
            "Tempo limite do Worker",
            "method:'POST'",
            "JSON.stringify({tickers:chunk})",
            "i+=80",
        ):
            self.assertIn(token,s)
        self.assertIn("Math.min(requested,MAX_QUOTE_CONCURRENCY",s)
        self.assertIn("`${base}/quotes`",s)
        self.assertIn("[404,405,501].includes(resp.status)",s)
        self.assertIn("unsupported=true",s)
        self.assertIn("window.VestraMarketClient",s)
        self.assertNotIn("AbortSignal.timeout",s)

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

    def test_quote_error_diagnostics_have_non_blocking_ios_bridge(self):
        q=read("app-quote-errors.js")
        self.assertIn("showQuoteErrorSheetFromModal",q)
        self.assertIn("closeQuoteErrorSheet",q)
        self.assertIn("MutationObserver",q)
        self.assertIn("-webkit-overflow-scrolling:touch",q)
        self.assertIn("document.body.classList.remove('modal-open')",q)
        self.assertIn("data-close=\"modalQuoteErrors\"",q)
        self.assertIn("pointer-events:auto",q)

if __name__=='__main__': unittest.main(verbosity=2)
