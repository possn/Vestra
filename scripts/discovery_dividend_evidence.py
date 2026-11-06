"""Audited dividend cash evidence for prospective Discovery *diagnostics*.

The optional data/verified_dividend_events.json is empty/absent by default.
Never infer paid dividends from dividend_yield, trailing rates or forecasts.
Cash attribution is intentionally separate from the ranking return: an
incomplete event ledger cannot establish total shareholder return.

Example file:
{"schema_version":1,"events":[
 {"ticker":"EXAMPLE","ex_date":"2026-01-07","payment_date":"2026-01-28",
  "amount_per_share":0.15,"currency":"EUR","source_url":"https://issuer.example/notice",
  "status":"confirmed"}
]}
Do not add example events to production data.
"""
from __future__ import annotations

import datetime as dt
import math
from urllib.parse import urlparse

try:
    from scripts.score_forward_validation import split_price_basis_factor
except ModuleNotFoundError:
    from score_forward_validation import split_price_basis_factor


def load_verified_ledger(path):
    """Absent is an empty ledger; malformed existing evidence must stop publication."""
    import json
    from pathlib import Path
    target = Path(path)
    if not target.exists():
        return None
    try:
        loaded = json.loads(target.read_text(encoding="utf-8"))
        if loaded is None:
            raise ValueError("Existing verified dividend ledger cannot be null")
        return loaded
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Corrupt verified dividend ledger: {target}") from exc


def validated_events(payload):
    """Reject the entire ledger on malformed/provisional/ambiguous entries."""
    if payload is None:
        return []
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ValueError("Verified dividend ledger must have schema_version 1")
    events = payload.get("events")
    if not isinstance(events, list):
        raise ValueError("Verified dividend ledger requires events array")
    out = []
    seen = set()
    for i, event in enumerate(events, 1):
        if not isinstance(event, dict):
            raise ValueError(f"Event {i}: expected object")
        ticker = str(event.get("ticker") or "").strip().upper()
        currency = str(event.get("currency") or "").strip().upper()
        source = str(event.get("source_url") or "").strip()
        try:
            ex_date = dt.date.fromisoformat(str(event.get("ex_date")))
            payment_date = dt.date.fromisoformat(str(event.get("payment_date")))
            amount = float(event.get("amount_per_share"))
        except (ValueError, TypeError) as error:
            raise ValueError(f"Event {i}: invalid dividend fields") from error
        if not ticker or not currency or len(currency) != 3:
            raise ValueError(f"Event {i}: ticker and ISO currency are mandatory")
        if not math.isfinite(amount) or amount <= 0 or payment_date < ex_date:
            raise ValueError(f"Event {i}: invalid amount or chronological dates")
        parsed = urlparse(source)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError(f"Event {i}: HTTPS source evidence required")
        if event.get("status") != "confirmed":
            raise ValueError(f"Event {i}: unconfirmed dividend")
        key = (ticker, ex_date, payment_date, amount, currency)
        if key in seen:
            raise ValueError(f"Event {i}: duplicate dividend")
        seen.add(key)
        out.append({
            "ticker": ticker, "ex_date": ex_date, "payment_date": payment_date,
            "amount_per_share": amount, "currency": currency,
            "source_url": source,
        })
    return out


def documented_dividend_cash(ticker, start, end, price_currency, events):
    """Return paid cash per terminal share for verified events in this window.

    Entitlement must arise after the snapshot and cash must have been paid by
    evaluation date. If share currency is absent, never silently apply FX.
    The split factor maps per-event cash onto the terminal share basis.
    """
    begin = dt.date.fromisoformat(str(start))
    finish = dt.date.fromisoformat(str(end))
    target = str(ticker or "").strip().upper()
    currency = str(price_currency or "").strip().upper()
    total = 0.0
    used = []
    for item in events:
        if item["ticker"] != target or not (begin < item["ex_date"] <= finish):
            continue
        if item["payment_date"] > finish:
            continue
        if not currency or item["currency"] != currency:
            raise ValueError(f"{target}: dividend and price currency cannot be reconciled")
        factor = split_price_basis_factor(target, item["ex_date"], finish)
        total += item["amount_per_share"] * factor
        used.append(item["source_url"])
    return {"cash_per_terminal_share": round(total, 10), "event_count": len(used),
            "source_urls": sorted(set(used))}
