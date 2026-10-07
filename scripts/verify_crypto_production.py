#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen

DEFAULT_BASE = "https://delicate-bar-cc80.pedrossnunes.workers.dev"
DEFAULT_ORIGIN = "https://possn.github.io"
TICKERS = ("BTC-USD", "ETH-USD", "SOL-USD")


def finite(value: Any) -> bool:
    try:
        x = float(value)
    except (TypeError, ValueError):
        return False
    return math.isfinite(x)


def positive(value: Any) -> bool:
    return finite(value) and float(value) > 0


def get_json(url: str, origin: str, timeout: float) -> tuple[int, dict[str, Any]]:
    req = Request(url, headers={
        "Accept": "application/json",
        "Origin": origin,
        "User-Agent": "Vestra-Crypto-Production-Smoke/1.0",
    })
    with urlopen(req, timeout=timeout) as response:
        payload = json.loads(response.read().decode("utf-8"))
        return int(response.status), payload


def validate_quotes(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for ticker in TICKERS:
        row = payload.get(ticker)
        if not isinstance(row, dict):
            errors.append(f"{ticker}: missing row")
            continue
        if not positive(row.get("price")):
            errors.append(f"{ticker}: missing positive price")
        if not finite(row.get("change_pct")):
            errors.append(f"{ticker}: missing 24h change_pct")
        if not positive(row.get("fifty_two_week_high")):
            errors.append(f"{ticker}: missing fifty_two_week_high")
        if not positive(row.get("fifty_two_week_low")):
            errors.append(f"{ticker}: missing fifty_two_week_low")
        high = row.get("fifty_two_week_high")
        low = row.get("fifty_two_week_low")
        if positive(high) and positive(low) and float(high) < float(low):
            errors.append(f"{ticker}: invalid 52w range")
    return errors


def validate_intelligence(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    global_data = payload.get("global") if isinstance(payload.get("global"), dict) else {}
    fear = payload.get("fear_greed") if isinstance(payload.get("fear_greed"), dict) else {}
    deriv = payload.get("derivatives") if isinstance(payload.get("derivatives"), dict) else {}
    btc = deriv.get("btc") if isinstance(deriv.get("btc"), dict) else {}
    eth = deriv.get("eth") if isinstance(deriv.get("eth"), dict) else {}

    if not positive(global_data.get("total_market_cap_usd")):
        errors.append("global: missing total_market_cap_usd")
    if not positive(global_data.get("total_volume_24h_usd")):
        errors.append("global: missing total_volume_24h_usd")
    dominance = global_data.get("btc_dominance_pct")
    if not finite(dominance) or not (0 < float(dominance) < 100):
        errors.append("global: invalid btc_dominance_pct")
    if not global_data.get("source"):
        errors.append("global: missing source attribution")

    fear_value = fear.get("value")
    if not finite(fear_value) or not (0 <= float(fear_value) <= 100):
        errors.append("fear_greed: invalid value")
    history = fear.get("history_30d")
    if not isinstance(history, list) or len(history) < 7:
        errors.append("fear_greed: insufficient history_30d")

    if not deriv.get("source"):
        errors.append("derivatives: missing source attribution")
    if not finite(btc.get("funding_rate_pct")):
        errors.append("derivatives: missing BTC funding")
    if not finite(eth.get("funding_rate_pct")):
        errors.append("derivatives: missing ETH funding")
    if not finite(btc.get("open_interest_change_7d_pct")):
        errors.append("derivatives: missing BTC OI 7d")
    if not finite(eth.get("open_interest_change_7d_pct")):
        errors.append("derivatives: missing ETH OI 7d")
    return errors


def probe(base: str, origin: str, timeout: float) -> tuple[list[str], dict[str, Any]]:
    joined = ",".join(TICKERS)
    q_status, quotes = get_json(f"{base}/quotes?{urlencode({'tickers': joined})}", origin, timeout)
    i_status, intel = get_json(f"{base}/crypto-intelligence", origin, timeout)

    errors: list[str] = []
    if q_status != 200:
        errors.append(f"/quotes HTTP {q_status}")
    if i_status != 200:
        errors.append(f"/crypto-intelligence HTTP {i_status}")
    errors.extend(validate_quotes(quotes))
    errors.extend(validate_intelligence(intel))

    summary = {
        "quotes": {
            ticker: {
                key: (quotes.get(ticker) or {}).get(key)
                for key in ("price", "change_pct", "fifty_two_week_high", "fifty_two_week_low", "source")
            }
            for ticker in TICKERS
        },
        "global": {
            key: (intel.get("global") or {}).get(key)
            for key in ("btc_dominance_pct", "total_market_cap_usd", "total_volume_24h_usd", "source")
        },
        "fear_greed": {
            key: (intel.get("fear_greed") or {}).get(key)
            for key in ("value", "change_7d", "change_30d", "source")
        },
        "derivatives": {
            "source": (intel.get("derivatives") or {}).get("source"),
            "btc": {
                key: ((intel.get("derivatives") or {}).get("btc") or {}).get(key)
                for key in ("funding_rate_pct", "open_interest_change_7d_pct")
            },
            "eth": {
                key: ((intel.get("derivatives") or {}).get("eth") or {}).get(key)
                for key in ("funding_rate_pct", "open_interest_change_7d_pct")
            },
        },
    }
    return errors, summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default=DEFAULT_BASE)
    parser.add_argument("--origin", default=DEFAULT_ORIGIN)
    parser.add_argument("--attempts", type=int, default=12)
    parser.add_argument("--delay", type=float, default=30.0)
    parser.add_argument("--timeout", type=float, default=15.0)
    args = parser.parse_args()

    base = args.url.rstrip("/")
    last_errors: list[str] = []
    last_summary: dict[str, Any] = {}

    for attempt in range(1, max(1, args.attempts) + 1):
        try:
            last_errors, last_summary = probe(base, args.origin, args.timeout)
        except Exception as exc:
            last_errors = [f"request failure: {exc!r}"]
            last_summary = {}

        print(f"Attempt {attempt}/{args.attempts}")
        print(json.dumps(last_summary, indent=2, ensure_ascii=False, default=str))
        if not last_errors:
            print("PASS: Crypto production data is complete.")
            return 0
        print("FAIL:", " | ".join(last_errors), file=sys.stderr)
        if attempt < args.attempts:
            time.sleep(max(0.0, args.delay))

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
