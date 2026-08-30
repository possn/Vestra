from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, got {count}")
    return text.replace(old, new, 1)


worker_path = Path("worker.js")
worker = worker_path.read_text(encoding="utf-8")
worker = replace_once(
    worker,
    " * Versão 4.3 — quotes + live market detail + deployment health",
    " * Versão 4.4 — fresh quote overlay + cached market fundamentals",
    "worker header",
)
old_cache = '''  const cacheUrl = `https://cache.internal/market41:${canonical}`;
  const cached = await cache.match(cacheUrl);
  if (cached) {
    const data = await cached.json();
    data._cached = true;
    return data;
  }
'''
new_cache = '''  const cacheUrl = `https://cache.internal/market41:${canonical}`;
  const cached = await cache.match(cacheUrl);
  if (cached) {
    const data = await cached.json();
    // Fundamentals may stay cached for 30 minutes, but price-sensitive fields must
    // inherit the 60-second quote freshness contract. This prevents /market from
    // showing an older price than /quote in an open dossier.
    try {
      const quote = await fetchYahooQuote(canonical, ctx);
      const current = Number(quote?.price);
      if (Number.isFinite(current) && current > 0) {
        data.current_price = current;
        if (quote.currency) data.currency = quote.currency;
        if (quote.exchange) data.exchange = quote.exchange;
        if (quote.quote_type) data.quote_type = quote.quote_type;
        for (const [targetKey, quoteKey] of [
          ['market_cap','market_cap'],
          ['trailing_pe','trailing_pe'],
          ['forward_pe','forward_pe'],
          ['price_to_book','price_to_book'],
          ['fifty_two_week_high','fifty_two_week_high'],
          ['fifty_two_week_low','fifty_two_week_low'],
        ]) {
          const value = Number(quote?.[quoteKey]);
          if (Number.isFinite(value)) data[targetKey] = value;
        }
        const target = Number(data.analyst_price_target_mean);
        if (Number.isFinite(target)) data.analyst_price_target_upside_pct = ((target / current) - 1) * 100;
        const fcf = Number(data.free_cash_flow);
        const marketCap = Number(data.market_cap);
        if (Number.isFinite(fcf) && Number.isFinite(marketCap) && marketCap > 0) data.fcf_yield = (fcf / marketCap) * 100;
        data.quote_updated = quote.updated || new Date().toISOString();
      }
    } catch (_) {}
    data._cached = true;
    return data;
  }
'''
worker = replace_once(worker, old_cache, new_cache, "market cache hit")
worker = replace_once(
    worker,
    "    updated: new Date().toISOString(),\n    source: qs ? 'Yahoo Finance quoteSummary + fundamentals-timeseries + chart' : 'Yahoo Finance fundamentals-timeseries + quote/chart'",
    "    updated: new Date().toISOString(),\n    quote_updated: quote.updated || new Date().toISOString(),\n    source: qs ? 'Yahoo Finance quoteSummary + fundamentals-timeseries + chart' : 'Yahoo Finance fundamentals-timeseries + quote/chart'",
    "market timestamps",
)
worker = replace_once(worker, '          version: "4.3",', '          version: "4.4",', "health version")
worker = replace_once(
    worker,
    "          quote_cache_ttl_seconds: QUOTE_CACHE_TTL\n",
    "          quote_cache_ttl_seconds: QUOTE_CACHE_TTL,\n          market_cache_ttl_seconds: MARKET_CACHE_TTL\n",
    "health cache metadata",
)
worker = replace_once(worker, '          service: "Vestra Market Proxy v4.3",', '          service: "Vestra Market Proxy v4.4",', "root version")
worker_path.write_text(worker, encoding="utf-8")

market_path = Path("market.js")
market = market_path.read_text(encoding="utf-8")
market = replace_once(
    market,
    "Object.assign(s,merge,{_liveUpdated:live.updated||new Date().toISOString()});",
    "Object.assign(s,merge,{_liveUpdated:live.quote_updated||live.updated||new Date().toISOString()});",
    "frontend live timestamp",
)
market_path.write_text(market, encoding="utf-8")

index_path = Path("index.html")
index = index_path.read_text(encoding="utf-8")
index = replace_once(index, "market.js?v=20260821v5", "market.js?v=20260830v1", "market cache buster")
index_path.write_text(index, encoding="utf-8")

test_path = Path("tests/test_worker_market_live_overlay.py")
test_path.write_text('''from pathlib import Path
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
        end = worker.index("\\n\\n\\nfunction normalizeCongressTrade", start)
        block = worker[start:end]
        self.assertIn("const quote = await fetchYahooQuote(canonical, ctx)", block)
        self.assertIn("data.current_price = current", block)
        self.assertIn("data.market_cap", block)
        self.assertIn("data.analyst_price_target_upside_pct", block)
        self.assertIn("data.fcf_yield", block)
        self.assertIn("data.quote_updated = quote.updated", block)
        self.assertIn("market_cache_ttl_seconds: MARKET_CACHE_TTL", worker)

    def test_frontend_live_badge_uses_quote_timestamp_before_fundamental_timestamp(self):
        market = read("market.js")
        self.assertIn("_liveUpdated:live.quote_updated||live.updated", market)


if __name__ == "__main__":
    unittest.main(verbosity=2)
''', encoding="utf-8")
