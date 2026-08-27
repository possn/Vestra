from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
def read(p): return (ROOT/p).read_text(encoding="utf-8")

class AppMarketClientTests(unittest.TestCase):
    def test_client_owns_transport_fx_and_concurrency(self):
        s=read("app-market-client.js")
        for token in ("async function fetchQuote", "async function fetchFxRates", "async function mapWithConcurrency", "FX_FALLBACK_LOCAL", "timeoutMs=10000", "AbortSignal.timeout(timeoutMs)"):
            self.assertIn(token,s)
        self.assertIn("window.VestraMarketClient",s)

    def test_app_imports_client_without_duplicate_implementations(self):
        app=read("app.js")
        self.assertIn("window.VestraMarketClient",app)
        self.assertNotIn("async function fetchQuote(ticker, workerUrl)",app)
        self.assertNotIn("async function mapWithConcurrency(items, concurrency, fn)",app)
        self.assertIn("fetchFxRates(ccysNeeded, workerUrl, FX_FALLBACK_LOCAL)",app)
        self.assertIn("FX_FALLBACK_LOCAL[ccy] || 1",app)

    def test_client_loads_before_app_and_is_cached(self):
        index=read("index.html")
        self.assertLess(index.index('src="app-market-client.js'),index.index('src="app.js'))
        self.assertIn('app-market-client.js?v=1.0',index)
        sw=read("sw.js")
        self.assertIn("Vestra Service Worker v10.8",sw)
        self.assertIn("vestra-cache-v122",sw)
        self.assertIn('./app-market-client.js',sw)

if __name__=='__main__': unittest.main(verbosity=2)
