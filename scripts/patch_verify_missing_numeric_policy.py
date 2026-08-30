from pathlib import Path

p=Path('scripts/verify_worker_deployment.py')
s=p.read_text(encoding='utf-8')
old='''    market_ttl = re.search(r"const MARKET_CACHE_TTL\\s*=\\s*(\\d+)", text)\n    return {\n        "version": version.group(1) if version else None,\n        "quote_cache_ttl_seconds": int(quote_ttl.group(1)) if quote_ttl else None,\n        "market_cache_ttl_seconds": int(market_ttl.group(1)) if market_ttl else None,\n    }\n'''
new='''    market_ttl = re.search(r"const MARKET_CACHE_TTL\\s*=\\s*(\\d+)", text)\n    missing_policy = re.search(r'missing_numeric_policy:\\s*"([^"]+)"', text)\n    return {\n        "version": version.group(1) if version else None,\n        "quote_cache_ttl_seconds": int(quote_ttl.group(1)) if quote_ttl else None,\n        "market_cache_ttl_seconds": int(market_ttl.group(1)) if market_ttl else None,\n        "missing_numeric_policy": missing_policy.group(1) if missing_policy else None,\n    }\n'''
if s.count(old)!=1: raise SystemExit('source contract anchor mismatch')
s=s.replace(old,new,1)
old2='''                for key, label in (\n                    ("quote_cache_ttl_seconds", "quote cache TTL"),\n                    ("market_cache_ttl_seconds", "market cache TTL"),\n                ):\n                    expected = contract.get(key)\n                    checks.append(Check(\n                        label,\n                        health.get(key) == expected,\n                        f"deployed={health.get(key)!r}, source={expected!r}",\n                    ))\n'''
new2='''                for key, label in (\n                    ("quote_cache_ttl_seconds", "quote cache TTL"),\n                    ("market_cache_ttl_seconds", "market cache TTL"),\n                    ("missing_numeric_policy", "missing numeric policy"),\n                ):\n                    expected = contract.get(key)\n                    checks.append(Check(\n                        label,\n                        health.get(key) == expected,\n                        f"deployed={health.get(key)!r}, source={expected!r}",\n                    ))\n'''
if s.count(old2)!=1: raise SystemExit('health contract anchor mismatch')
s=s.replace(old2,new2,1)
p.write_text(s,encoding='utf-8')
