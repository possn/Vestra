from pathlib import Path

p=Path('scripts/fundamentals.py')
s=p.read_text(encoding='utf-8')

old='''_cooldown_lock = threading.Lock()\n_cooldown_until = 0.0\n_cooldown_strikes = 0\n'''
new='''_cooldown_lock = threading.Lock()\n_cooldown_until = 0.0\n_cooldown_strikes = 0\n_last_rate_limit_hit = 0.0\n'''
assert old in s
s=s.replace(old,new,1)

old='''def _wait_for_cooldown():\n    with _cooldown_lock:\n        remaining = _cooldown_until - time.time()\n    if remaining > 0:\n        time.sleep(remaining)\n\n\ndef _register_rate_limit_hit():\n    global _cooldown_until, _cooldown_strikes\n    with _cooldown_lock:\n        _cooldown_strikes += 1\n        # Escalating cooldown: 20s, 40s, 80s, ... capped at 5 minutes so a\n        # very long block doesn't eat the whole Actions run budget either.\n        backoff = min(300, 20 * (2 ** (_cooldown_strikes - 1)))\n        candidate = time.time() + backoff\n        if candidate > _cooldown_until:\n            _cooldown_until = candidate\n            log.warning("Yahoo rate-limit detected — pausing all fetch workers for %ds (strike %d)", backoff, _cooldown_strikes)\n'''
new='''def _wait_for_cooldown():\n    global _cooldown_strikes\n    now = time.time()\n    with _cooldown_lock:\n        # A throttle burst must not poison the rest of the whole pipeline. If\n        # Yahoo has been quiet for two minutes, treat a future 429 as a fresh\n        # incident instead of resuming at the maximum backoff forever.\n        if _last_rate_limit_hit and now - _last_rate_limit_hit > 120:\n            _cooldown_strikes = 0\n        remaining = _cooldown_until - now\n    if remaining > 0:\n        time.sleep(remaining)\n\n\ndef _register_rate_limit_hit():\n    global _cooldown_until, _cooldown_strikes, _last_rate_limit_hit\n    with _cooldown_lock:\n        _last_rate_limit_hit = time.time()\n        _cooldown_strikes += 1\n        # 10s, 20s, 40s, then 60s maximum. The previous 300s ceiling, combined\n        # with thousands of sequential retries, could hold an Actions build for\n        # hours after a single broad Yahoo throttle event.\n        backoff = min(60, 10 * (2 ** (_cooldown_strikes - 1)))\n        candidate = _last_rate_limit_hit + backoff\n        if candidate > _cooldown_until:\n            _cooldown_until = candidate\n            log.warning("Yahoo rate-limit detected — pausing fetch workers for %ds (strike %d)", backoff, _cooldown_strikes)\n'''
assert old in s
s=s.replace(old,new,1)

old='''    for attempt in range(max(0, int(retries))):\n        failed = [tk for tk in tickers if getattr(results_by_ticker.get(tk), "error", None)]\n        if not failed:\n            break\n        # Exponential backoff between retry passes (not just the per-worker\n        # cooldown above) — a pass that hit a rate-limit wall needs more\n        # than a couple seconds before trying the same tickers again.\n        backoff = min(120, 8 * (2 ** attempt))\n'''
new='''    for attempt in range(max(0, int(retries))):\n        failed = [tk for tk in tickers if getattr(results_by_ticker.get(tk), "error", None)]\n        if not failed:\n            break\n        failure_ratio = len(failed) / max(1, len(tickers))\n        # A broad Yahoo throttle is not repaired by retrying hundreds/thousands\n        # of names sequentially. Portfolio positions are fetched separately in\n        # run.py with their own small retry pool; for the generic universe fail\n        # fast when the first pass is broadly blocked and let the coverage guard\n        # reject publication rather than monopolising the runner for hours.\n        if len(tickers) > 250 and failure_ratio >= 0.25:\n            log.warning("Broad Yahoo failure: %d/%d (%.1f%%). Skipping bulk retry pass to keep build bounded.", len(failed), len(tickers), failure_ratio * 100)\n            break\n        # Exponential backoff between retry passes. Keep this bounded because\n        # the shared cooldown already handles the immediate throttle window.\n        backoff = min(45, 6 * (2 ** attempt))\n'''
assert old in s
s=s.replace(old,new,1)

p.write_text(s,encoding='utf-8')
