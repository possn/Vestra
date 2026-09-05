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
        self.assertIn(".find(item=>txt(item?.symbol).toUpperCase()===ticker)", self.text)
        self.assertIn("symbol === ticker", self.text)
        self.assertNotIn("handleExactBatchQuotes(request, env, ctx)", self.text)

    def test_batch_has_per_ticker_deadline_not_whole_batch_tail_latency(self):
        self.assertIn("const BATCH_ITEM_DEADLINE_MS = 6500", self.text)
        self.assertIn("Promise.all(tickers.map(async ticker=>", self.text)
        self.assertIn("withDeadline(", self.text)
        self.assertIn("return [ticker,{ticker,error:error?.message || 'Erro ao obter cotação'}]", self.text)

    def test_batch_preserves_fx_crypto_and_gbpence_semantics(self):
        self.assertIn("function validQuoteTicker", self.text)
        self.assertIn("[A-Z0-9.\\-^=]", self.text)
        self.assertIn(".filter(validQuoteTicker)", self.text)
        self.assertIn("rawCurrency === 'GBp'", self.text)
        self.assertIn("return {price:value/100,currency:'GBP'}", self.text)
        # Learned-universe remains type-gated, but the exact quote transport must
        # not reject CURRENCY/CRYPTOCURRENCY before identity validation.
        self.assertNotIn("if (row && rawPrice && (!type || ALLOWED_TYPES.has(type)))", self.text)
        self.assertNotIn("if (meta && symbol === ticker && rawPrice && (!type || ALLOWED_TYPES.has(type)))", self.text)
        self.assertIn("if (type && !ALLOWED_TYPES.has(type)) return null", self.text)

    def test_health_exposes_batch_transport_contract(self):
        self.assertIn("quote_batch_transport:'exact_identity_parallel_v1'", self.text)
        self.assertIn("quote_batch_item_deadline_ms:BATCH_ITEM_DEADLINE_MS", self.text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
