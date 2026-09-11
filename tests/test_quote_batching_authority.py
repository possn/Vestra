from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


class QuoteBatchingAuthorityTests(unittest.TestCase):
    def test_market_client_is_the_single_quote_batching_authority(self):
        client = read("app-market-client.js")
        app = read("app.js")
        brief = read("market-company-brief.js")

        self.assertIn("async function fetchQuotesBatch", client)
        self.assertIn("BATCH_CHUNK_SIZE = 20", client)
        self.assertIn("BATCH_REQUEST_CONCURRENCY = 8", client)
        self.assertIn("queueQuote", client)
        self.assertIn("flushQuoteQueue", client)
        self.assertIn("/quotes?tickers=", client)
        self.assertIn("mapWithConcurrency(tickerList, 8, x => fetchQuoteWithFallback(x))", app)

        self.assertNotIn("quote-refresh-performance.js", brief)
        self.assertFalse((ROOT / "quote-refresh-performance.js").exists())

    def test_retired_fast_lane_cannot_reappear_as_a_parallel_transport_policy(self):
        brief = read("market-company-brief.js")
        client = read("app-market-client.js")

        self.assertNotIn("loadQuoteRefreshPerformance", brief)
        self.assertNotIn("window.mapWithConcurrency =", client)
        self.assertIn("window.VestraMarketClient=Object.freeze", client)


if __name__ == "__main__":
    unittest.main(verbosity=2)
