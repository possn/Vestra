from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
ROUTER = ROOT / "worker-router.js"


class QuoteBatchExactIdentityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.text = ROUTER.read_text(encoding="utf-8")

    def test_router_is_valid_javascript(self):
        subprocess.run(["node", "--check", str(ROUTER)], check=True, cwd=ROOT)

    def test_batch_route_uses_exact_provider_identity(self):
        self.assertIn("if (url.pathname === '/quotes' && request.method === 'GET') return handleExactBatchQuotes(request);", self.text)
        self.assertIn("const symbol = txt(row?.symbol).toUpperCase()", self.text)
        self.assertIn("symbol !== ticker", self.text)
        self.assertIn("symbol !== ticker) return null", self.text)
        self.assertNotIn("handleExactBatchQuotes(request, env, ctx)", self.text)

    def test_batch_is_one_multisymbol_request_first_not_twenty_parallel_requests(self):
        self.assertIn("async function fetchYahooBatchExactIdentity(tickers)", self.text)
        self.assertIn("const symbols = encodeURIComponent(requested.join(','))", self.text)
        self.assertIn("/v7/finance/quote?symbols=${symbols}", self.text)
        self.assertIn("const quotes = await fetchYahooBatchExactIdentity(tickers)", self.text)
        self.assertNotIn("Promise.all(tickers.map(async ticker=>", self.text)

    def test_missing_symbols_use_bounded_exact_chart_fallback(self):
        self.assertIn("const BATCH_ITEM_DEADLINE_MS = 6500", self.text)
        self.assertIn("const BATCH_CHART_FALLBACK_CONCURRENCY = 4", self.text)
        self.assertIn("async function fillMissingBatchQuotes(tickers, quotes)", self.text)
        self.assertIn("fetchYahooExactChartIdentity(ticker)", self.text)
        self.assertIn("withDeadline(", self.text)
        self.assertIn("await fillMissingBatchQuotes(tickers,quotes)", self.text)

    def test_batch_preserves_fx_crypto_and_gbpence_semantics(self):
        self.assertIn("function validQuoteTicker", self.text)
        self.assertIn("[A-Z0-9.\\-^=]", self.text)
        self.assertIn(".filter(validQuoteTicker)", self.text)
        self.assertIn("rawCurrency === 'GBp'", self.text)
        self.assertIn("return {price:value/100,currency:'GBP'}", self.text)
        self.assertIn("if (type && !ALLOWED_TYPES.has(type)) return null", self.text)

    def test_health_exposes_batch_transport_contract(self):
        self.assertIn("quote_batch_transport:'exact_identity_multisymbol_v2'", self.text)
        self.assertIn("quote_batch_item_deadline_ms:BATCH_ITEM_DEADLINE_MS", self.text)
        self.assertIn("quote_batch_chunk_size:20", self.text)
        self.assertIn("quote_batch_chart_fallback_concurrency:BATCH_CHART_FALLBACK_CONCURRENCY", self.text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
