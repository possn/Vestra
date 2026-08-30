from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
def read(p): return (ROOT/p).read_text(encoding="utf-8")

class AppMarketClientTests(unittest.TestCase):
    def test_client_owns_transport_fx_and_ios_safe_coalescing(self):
        s=read("app-market-client.js")
        for token in (
            "async function fetchQuote",
            "async function fetchQuoteDirect",
            "async function fetchQuotesBatch",
            "async function fetchFxRates",
            "async function mapWithConcurrency",
            "FX_FALLBACK_LOCAL",
            "MAX_QUOTE_CONCURRENCY = 12",
            "DEFAULT_QUOTE_TIMEOUT_MS = 12000",
            "BATCH_QUOTE_TIMEOUT_MS = 12000",
            "BATCH_CHUNK_SIZE = 12",
            "DIRECT_FALLBACK_CONCURRENCY = 2",
            "QUOTE_CACHE_TTL_MS = 60 * 1000",
            "QUOTE_ERROR_TTL_MS = 20 * 1000",
            "FX_CACHE_TTL_MS = 4 * 60 * 60 * 1000",
            "quoteInflight",
            "quoteCache",
            "fxCache",
            "async function fetchWithTimeout",
            "new AbortController()",
            "controller.abort()",
            "Tempo limite do Worker",
            "method:'GET'",
            "/quotes?tickers=",
            "queueQuote",
            "flushQuoteQueue",
            "runDirectFallback",
        ):
            self.assertIn(token,s)
        self.assertIn("Math.min(requested,MAX_QUOTE_CONCURRENCY",s)
        self.assertIn("if(quoteInflight.has(key)) return quoteInflight.get(key)",s)
        self.assertIn("[404,405,501].includes(resp.status)",s)
        self.assertIn("batchSupport.set(base,false)",s)
        self.assertIn("window.VestraMarketClient",s)
        self.assertNotIn("AbortSignal.timeout",s)
        self.assertNotIn("method:'POST'",s)

    def test_worker_batch_endpoint_matches_client_contract(self):
        w=read("worker.js")
        self.assertIn('if (url.pathname === "/quotes")',w)
        self.assertIn('url.searchParams.get("tickers")',w)
        self.assertIn('.slice(0, 20)',w)
        self.assertIn('request.method !== "GET"',w)
        self.assertIn('out[tickers[i]]',w)
        self.assertIn('timeoutMs = 3500',w)
        self.assertIn('controller.abort()',w)

    def test_app_imports_client_without_duplicate_implementations(self):
        app=read("app.js")
        self.assertIn("window.VestraMarketClient",app)
        self.assertNotIn("async function fetchQuote(ticker, workerUrl)",app)
        self.assertNotIn("async function fetchQuotesBatch(tickers, workerUrl",app)
        self.assertNotIn("async function mapWithConcurrency(items, concurrency, fn)",app)
        self.assertIn("fetchFxRates(ccysNeeded, workerUrl, FX_FALLBACK_LOCAL)",app)

    def test_app_has_one_quote_refresh_gate_for_manual_startup_and_foreground(self):
        app=read("app.js")
        self.assertEqual(app.count("let quoteRefreshPromise = null;"),1)
        self.assertEqual(app.count("async function refreshLiveQuotes(options = {})"),1)
        self.assertEqual(app.count("async function refreshLiveQuotesCore(options = {})"),1)
        self.assertIn("if (quoteRefreshPromise) return quoteRefreshPromise;",app)

    def test_active_refresh_keeps_existing_fallback_and_sanity_path(self):
        app=read("app.js")
        self.assertIn("fetchQuoteWithFallback",app)
        self.assertIn("mapWithConcurrency(tickerList, 8, x => fetchQuoteWithFallback(x))",app)
        client=read("app-market-client.js")
        self.assertIn("MAX_QUOTE_CONCURRENCY = 12",client)
        self.assertNotIn("fetchQuotesBatch(",app)
        self.assertIn("Cotação suspeita rejeitada",app)

    def test_quote_engine_v2_prefers_authoritative_identity_and_tags_history(self):
        app=read("app.js")
        self.assertIn("Quote Engine v2: authoritative identity",app)
        self.assertIn("const exactIsinYahoo",app)
        self.assertIn("const usBroker = rawBroker.match",app)
        self.assertIn("authoritativeLegacyRepair",app)
        self.assertIn("quoteTicker: String(q.ticker",app)

    def test_auto_refresh_policy_is_stale_only_and_reuses_same_gate(self):
        app=read("app.js")
        self.assertIn("const STALE_MS = 30 * 60 * 1000",app)
        self.assertIn("if (!needsRefresh) return;",app)

    def test_client_loads_before_app_and_is_cached(self):
        index=read("index.html")
        self.assertLess(index.index('src="app-market-client.js'),index.index('src="app.js'))
        sw=read("sw.js")
        self.assertIn('./app-market-client.js',sw)
        self.assertIn('networkFirst(request)',sw)

    def test_quote_error_diagnostics_have_non_blocking_ios_bridge(self):
        q=read("app-quote-errors.js")
        self.assertIn("showQuoteErrorSheetFromModal",q)
        self.assertIn("closeQuoteErrorSheet",q)
        self.assertIn("MutationObserver",q)

if __name__=='__main__': unittest.main(verbosity=2)
