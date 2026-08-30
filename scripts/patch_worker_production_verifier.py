from pathlib import Path


def once(text, old, new, label):
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected one match, got {count}")
    return text.replace(old, new, 1)

p = Path('scripts/verify_worker_deployment.py')
s = p.read_text(encoding='utf-8')
s = once(s, 'import math\nimport sys', 'import math\nimport re\nimport sys', 're import')
s = once(s, 'from dataclasses import dataclass\nfrom typing import Any', 'from dataclasses import dataclass\nfrom pathlib import Path\nfrom typing import Any', 'Path import')
s = once(s, 'DEFAULT_TICKERS = ["MSFT", "AAPL"]\n', '''DEFAULT_TICKERS = ["MSFT", "AAPL"]
ROOT = Path(__file__).resolve().parents[1]
WORKER_SOURCE = ROOT / "worker.js"


def source_worker_contract() -> dict[str, Any]:
    text = WORKER_SOURCE.read_text(encoding="utf-8")
    version = re.search(r"Versão\\s+([0-9.]+)", text)
    quote_ttl = re.search(r"const QUOTE_CACHE_TTL\\s*=\\s*(\\d+)", text)
    market_ttl = re.search(r"const MARKET_CACHE_TTL\\s*=\\s*(\\d+)", text)
    return {
        "version": version.group(1) if version else None,
        "quote_cache_ttl_seconds": int(quote_ttl.group(1)) if quote_ttl else None,
        "market_cache_ttl_seconds": int(market_ttl.group(1)) if market_ttl else None,
    }
''', 'source contract')
s = once(s, '    checks: list[Check] = []\n    report: dict[str, Any] = {"worker": base, "origin": args.origin, "checks": []}\n', '''    checks: list[Check] = []
    report: dict[str, Any] = {"worker": base, "origin": args.origin, "checks": []}
    contract = source_worker_contract()
    report["source_contract"] = contract
''', 'contract init')
s = once(s, '''            health_ok = health_resp.ok and isinstance(health, dict)
            checks.append(Check("GET /health", health_ok, f"HTTP {health_resp.status_code}, {health_ms} ms"))
            report["health"] = health
''', '''            health_ok = health_resp.ok and isinstance(health, dict)
            checks.append(Check("GET /health", health_ok, f"HTTP {health_resp.status_code}, {health_ms} ms"))
            report["health"] = health
            if health_ok:
                checks.append(Check(
                    "deployed/source Worker version",
                    health.get("version") == contract.get("version"),
                    f"deployed={health.get('version')!r}, source={contract.get('version')!r}",
                ))
                for key, label in (
                    ("quote_cache_ttl_seconds", "quote cache TTL"),
                    ("market_cache_ttl_seconds", "market cache TTL"),
                ):
                    expected = contract.get(key)
                    checks.append(Check(label, health.get(key) == expected, f"deployed={health.get(key)!r}, source={expected!r}"))
''', 'health contract checks')
old_market = '''    probe = tickers[0]
    try:
        url = f"{base}/market?{urlencode({'ticker': probe})}"
        resp, payload, elapsed = get_json(session, url, origin=args.origin, timeout=args.timeout)
        ok = resp.ok and isinstance(payload, dict)
        checks.append(Check(f"GET /market {probe}", ok, f"HTTP {resp.status_code}, {elapsed} ms"))
    except Exception as exc:
        checks.append(Check(f"GET /market {probe}", False, repr(exc)))
'''
new_market = '''    probe = tickers[0]
    try:
        url = f"{base}/market?{urlencode({'ticker': probe})}"
        resp1, market1, elapsed1 = get_json(session, url, origin=args.origin, timeout=args.timeout)
        time.sleep(1.0)
        resp2, market2, elapsed2 = get_json(session, url, origin=args.origin, timeout=args.timeout)
        ok = resp1.ok and resp2.ok and isinstance(market1, dict) and isinstance(market2, dict)
        checks.append(Check(f"GET /market {probe}", ok, f"HTTP {resp2.status_code}, {elapsed2} ms"))
        quote = single_quotes.get(probe.upper()) or {}
        q_price = float(quote["price"]) if finite_positive(quote.get("price")) else None
        m_price = float(market2["current_price"]) if finite_positive(market2.get("current_price")) else None
        if q_price is not None and m_price is not None:
            rel = abs(q_price - m_price) / max(abs(q_price), abs(m_price), 1e-9)
            checks.append(Check(
                f"quote/market price equivalence {probe.upper()}",
                rel <= 0.01,
                f"quote={q_price}, market={m_price}, rel_diff={rel:.4%}",
            ))
        else:
            checks.append(Check(f"quote/market price equivalence {probe.upper()}", False, "missing positive price"))
        cache_hit = isinstance(market2, dict) and market2.get("_cached") is True
        has_quote_ts = isinstance(market2, dict) and bool(market2.get("quote_updated"))
        checks.append(Check(
            "cached /market fresh quote overlay",
            cache_hit and has_quote_ts,
            f"cached={market2.get('_cached') if isinstance(market2, dict) else None}, quote_updated={market2.get('quote_updated') if isinstance(market2, dict) else None!r}",
        ))
        report["market_probe"] = {"first": market1, "second": market2, "first_ms": elapsed1, "second_ms": elapsed2}
    except Exception as exc:
        checks.append(Check(f"GET /market {probe}", False, repr(exc)))
'''
s = once(s, old_market, new_market, 'market probe')
p.write_text(s, encoding='utf-8')

w = Path('.github/workflows/verify-cloudflare-worker.yml')
y = w.read_text(encoding='utf-8')
y = once(y, '''  push:
    branches:
      - audit/cloudflare-worker-20260830
    paths:
      - 'scripts/verify_worker_deployment.py'
      - '.github/workflows/verify-cloudflare-worker.yml'
      - 'docs/CLOUDFLARE_DEPLOYMENT.md'
''', '''  push:
    branches:
      - main
    paths:
      - 'worker.js'
      - 'scripts/verify_worker_deployment.py'
      - '.github/workflows/verify-cloudflare-worker.yml'
''', 'workflow trigger')
y = once(y, '''        run: |
          python scripts/verify_worker_deployment.py --url "$VESTRA_WORKER_URL" --ticker MSFT --ticker AAPL
''', '''        run: |
          for attempt in 1 2 3 4 5; do
            if python scripts/verify_worker_deployment.py --url "$VESTRA_WORKER_URL" --ticker MSFT --ticker AAPL; then
              exit 0
            fi
            echo "Production not aligned yet (attempt ${attempt}/5); waiting 15s for Cloudflare deployment..."
            sleep 15
          done
          exit 1
''', 'workflow retries')
w.write_text(y, encoding='utf-8')
