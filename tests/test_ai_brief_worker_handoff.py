from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class AiBriefWorkerHandoffTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.frontend = (ROOT / "vestra-ai-brief.js").read_text(encoding="utf-8")
        cls.router = (ROOT / "worker-router.js").read_text(encoding="utf-8")
        cls.worker_ai = (ROOT / "worker-ai-brief.js").read_text(encoding="utf-8")
        cls.wrangler = (ROOT / "wrangler.toml").read_text(encoding="utf-8")

    def test_frontend_uses_canonical_worker_fallback_and_session_header(self):
        self.assertIn("CANONICAL_WORKER_URL='https://delicate-bar-cc80.pedrossnunes.workers.dev'", self.frontend)
        self.assertIn("window.VestraRuntimeBridge?.canonicalWorkerUrl", self.frontend)
        self.assertIn("'x-vestra-session':aiSession()", self.frontend)
        self.assertIn("method:'POST'", self.frontend)
        self.assertIn("/ai-brief", self.frontend)

    def test_router_owns_post_route_before_market_worker(self):
        ai_route = self.router.index("if (url.pathname === '/ai-brief')")
        delegate = self.router.index("return marketWorker.fetch(request,env,ctx);")
        self.assertLess(ai_route, delegate)
        self.assertIn("'ai_brief'", self.router)
        self.assertIn("ai_brief_provider:'workers_ai'", self.router)

    def test_cloudflare_bindings_are_declared(self):
        self.assertIn('[ai]\nbinding = "AI"', self.wrangler)
        self.assertIn('name = "AI_BRIEF_RATE_LIMITER"', self.wrangler)
        self.assertIn('period = 60', self.wrangler)

    def test_ai_boundary_is_evidence_only_and_fail_closed(self):
        self.assertIn("Usa EXCLUSIVAMENTE os dados fornecidos", self.worker_ai)
        self.assertIn("Não dês instruções de comprar, vender", self.worker_ai)
        self.assertIn("Campos null ou vazios", self.worker_ai)
        self.assertIn("const forbidden=", self.worker_ai)
        self.assertNotIn("OPENAI_API_KEY", self.worker_ai)
        self.assertNotIn("ANTHROPIC_API_KEY", self.worker_ai)


if __name__ == "__main__":
    unittest.main()
