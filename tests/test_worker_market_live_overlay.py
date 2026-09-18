from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class WorkerMarketLiveOverlayTests(unittest.TestCase):
    def test_market_cache_preserves_long_fundamental_ttl_but_refreshes_quote_fields(self):
        worker = read("worker.js")
        self.assertIn("const QUOTE_CACHE_TTL = 60", worker)
        self.assertIn("const MARKET_CACHE_TTL = 1800", worker)
        start = worker.index("async function fetchYahooMarketDetail")
        end = worker.index("\n\n\nfunction normalizeCongressTrade", start)
        block = worker[start:end]
        self.assertIn("const quote = await fetchYahooQuote(canonical, ctx)", block)
        self.assertIn("data.current_price = current", block)
        self.assertIn("data.market_cap", block)
        self.assertIn("data.analyst_price_target_upside_pct", block)
        self.assertIn("data.fcf_yield", block)
        self.assertIn("data.quote_updated = quote.updated", block)
        self.assertIn("market_cache_ttl_seconds: MARKET_CACHE_TTL", worker)

    def test_worker_market_payload_declares_exact_provider_identity(self):
        worker = read("worker.js")
        self.assertIn("quote47:", worker)
        self.assertIn("market46:", worker)
        self.assertIn("provider_symbol:", worker)
        self.assertIn("retrieval_ticker:", worker)
        self.assertIn("String(quote?.provider_symbol || canonical)", worker)

    def test_sparse_market_detail_uses_statement_and_chart_fallbacks(self):
        worker = read("worker.js")
        self.assertIn("'annualDilutedAverageShares','quarterlyDilutedAverageShares'", worker)
        self.assertIn("const dilutedShares = firstFinite(", worker)
        self.assertIn("current * dilutedShares", worker)
        self.assertIn("marketCap/equityAnnual", worker)
        self.assertIn("niAnnual/equityAnnual*100", worker)
        self.assertIn("historyHigh", worker)
        self.assertIn("historyLow", worker)
        self.assertIn("Math.max(...highValues)", worker)
        self.assertIn("Math.min(...lowValues)", worker)

    def test_global_live_overlay_rejects_mismatched_identity(self):
        overlay = read("market-live-overlay.js")
        self.assertIn("stock?._remoteGlobal || stock?.identity_verified === true", overlay)
        self.assertIn("provider !== ticker || canonical !== ticker || retrieval !== ticker", overlay)
        self.assertIn("version: '1.2'", overlay)

    def test_frontend_live_badge_uses_quote_timestamp_before_fundamental_timestamp(self):
        overlay = read("market-live-overlay.js")
        compact = "".join(overlay.split())
        self.assertIn("_liveUpdated:live.quote_updated||live.updated||newDate().toISOString()", compact)


if __name__ == "__main__":
    unittest.main(verbosity=2)
