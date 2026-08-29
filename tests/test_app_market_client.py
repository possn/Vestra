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

    def test_app_has_one_quote_refresh_gate_for_manual_startup_and_foreground(self):
        app=read("app.js")
        self.assertEqual(app.count("let quoteRefreshPromise = null;"),1)
        self.assertEqual(app.count("async function refreshLiveQuotes(options = {})"),1)
        self.assertEqual(app.count("async function refreshLiveQuotesCore(options = {})"),1)
        self.assertIn("if (quoteRefreshPromise) return quoteRefreshPromise;",app)
        self.assertIn("refreshLiveQuotes({ manual: true })",app)
        self.assertIn("refreshLiveQuotes({ manual: false })",app)
        self.assertIn("autoRefreshQuotesIfStale()",app)
        self.assertIn('document.addEventListener("visibilitychange"',app)

    def test_active_refresh_uses_proven_individual_quote_path(self):
        app=read("app.js")
        self.assertIn("fetchQuoteWithFallback",app)
        self.assertIn("mapWithConcurrency(tickerList, 8, x => fetchQuoteWithFallback(x))",app)
        # The caller may request 8, but the transport owns the effective ceiling (4).
        client=read("app-market-client.js")
        self.assertIn("MAX_QUOTE_CONCURRENCY = 4",client)
        self.assertIn("Math.min(requested,MAX_QUOTE_CONCURRENCY",client)
        # Batch transport remains available for compatibility but is not wired into app.js.
        self.assertNotIn("fetchQuotesBatch(",app)
        self.assertIn('workerMode:"individual"',app)

    def test_auto_refresh_policy_is_stale_only_and_reuses_same_gate(self):
        app=read("app.js")
        self.assertIn("const STALE_MS = 30 * 60 * 1000",app)
        self.assertIn("const needsRefresh = (lastRefreshISO !== todayISO) || (msSinceRefresh > STALE_MS);",app)
        self.assertIn("if (!needsRefresh) return;",app)
        self.assertIn("refreshLiveQuotes({ manual: false })",app)
        self.assertIn("state.settings.lastQuoteRefreshTs   = Date.now();",app)

    def test_client_loads_before_app_and_is_cached(self):
        index=read("index.html")
        client_pos=index.index('src="app-market-client.js')
        errors_pos=index.index('src="app-quote-errors.js')
        app_pos=index.index('src="app.js')
        self.assertLess(client_pos,errors_pos)
        self.assertLess(errors_pos,app_pos)
        sw=read("sw.js")
        self.assertIn('./app-market-client.js',sw)
        self.assertIn('./app-quote-errors.js',sw)
        self.assertIn('request.destination === "document"',sw)
        self.assertIn('["script", "style", "worker", "manifest"]',sw)
        self.assertIn('networkFirst(request)',sw)

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
