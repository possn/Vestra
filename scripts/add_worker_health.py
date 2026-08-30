#!/usr/bin/env python3
from pathlib import Path

path = Path('worker.js')
text = path.read_text(encoding='utf-8')
old = '''      if (url.pathname === "/" || url.pathname === "") {
        return new Response(JSON.stringify({
          service: "Vestra Market Proxy v4.2",
          endpoints: ["/quote?ticker=VWCE.DE", "/quotes?tickers=VWCE.DE,IWDA.L", "/market?ticker=MSFT"]
        }), { headers: { ...cors, "Content-Type": "application/json" } });
      }
'''
new = '''      if (url.pathname === "/health") {
        return new Response(JSON.stringify({
          service: "Vestra Market Proxy",
          version: "4.3",
          build_id: String(env?.BUILD_ID || "unknown"),
          capabilities: ["quote", "quotes", "market"],
          quote_cache_ttl_seconds: CACHE_TTL
        }), { headers: { ...cors, "Content-Type": "application/json", "Cache-Control": "no-store" } });
      }

      if (url.pathname === "/" || url.pathname === "") {
        return new Response(JSON.stringify({
          service: "Vestra Market Proxy v4.3",
          build_id: String(env?.BUILD_ID || "unknown"),
          endpoints: ["/health", "/quote?ticker=VWCE.DE", "/quotes?tickers=VWCE.DE,IWDA.L", "/market?ticker=MSFT"]
        }), { headers: { ...cors, "Content-Type": "application/json", "Cache-Control": "no-store" } });
      }
'''
if old not in text:
    raise SystemExit('expected Worker root block not found; refusing unsafe patch')
text = text.replace(old, new, 1)
text = text.replace(' * Versão 4.0 — quotes + live market detail + chart enrichment',
                    ' * Versão 4.3 — quotes + live market detail + deployment health')
path.write_text(text, encoding='utf-8')
print('worker.js health/build metadata patch applied')
