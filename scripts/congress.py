"""US Congressional stock-trade context for Vestra dossiers.

The market build no longer calls Bargo (or any third-party Congress API) on a
per-build basis. A dedicated scheduled job builds data/politicians.json from
fresh disclosure sources, prioritising the official U.S. House Clerk archive.
This module only reads that validated local snapshot and maps it onto the Vestra
US universe.

Congress activity is contextual evidence only; it never changes the core
fundamental company score.
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import re
from pathlib import Path

log = logging.getLogger("congress")

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = ROOT / "data" / "politicians.json"
MAX_STALE_DAYS = 60
MAX_PER_TICKER = 100


def _amount_mid(range_str: str | None) -> float | None:
    if not range_str:
        return None
    nums = re.findall(r"\$?([\d,.]+)\s*([KMB])?", str(range_str), re.IGNORECASE)
    vals: list[float] = []
    for num, unit in nums[:2]:
        try:
            value = float(num.replace(",", ""))
        except ValueError:
            continue
        unit = unit.upper()
        if unit == "K":
            value *= 1e3
        elif unit == "M":
            value *= 1e6
        elif unit == "B":
            value *= 1e9
        vals.append(value)
    return (sum(vals) / len(vals)) if vals else None


def _slug(name: str) -> str:
    return "-".join(re.sub(r"[^a-z0-9]+", " ", str(name or "").lower()).split())


def _is_fresh(payload: dict) -> bool:
    if int(payload.get("schema_version") or 0) < 2:
        return False
    newest = str(payload.get("newest_disclosure") or payload.get("source_last_updated") or "")[:10]
    try:
        age = (dt.date.today() - dt.date.fromisoformat(newest)).days
    except (TypeError, ValueError):
        return False
    return age <= MAX_STALE_DAYS


def _load_snapshot() -> dict | None:
    if not SNAPSHOT.exists():
        log.warning("congress: canonical politicians snapshot missing")
        return None
    try:
        payload = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    except Exception as exc:
        log.warning("congress: invalid politicians snapshot (%s: %s)", type(exc).__name__, exc)
        return None
    if not isinstance(payload, dict) or not _is_fresh(payload):
        log.warning("congress: politicians snapshot is stale or invalid; contextual layer omitted")
        return None
    trades = payload.get("trades")
    if not isinstance(trades, list):
        log.warning("congress: politicians snapshot has no trade list")
        return None
    return payload


def _normalize_one(x: dict) -> tuple[str, dict] | None:
    ticker = str(x.get("ticker") or "").strip().upper()
    transaction_date = str(x.get("transaction_date") or "").strip()
    member = str(x.get("member") or "Membro do Congresso").strip()
    if not ticker or not transaction_date:
        return None
    raw_type = str(x.get("type") or "trade").lower()
    if "purchase" in raw_type or "buy" in raw_type:
        tx_type = "buy"
    elif "sale" in raw_type or "sell" in raw_type:
        tx_type = "sell"
    else:
        tx_type = raw_type or "trade"
    amount_range = x.get("amount") or x.get("amount_range") or "—"
    trade = {
        "member": member,
        "member_slug": _slug(member),
        "chamber": str(x.get("chamber") or "").lower(),
        "state": x.get("state") or "",
        "party": x.get("party") or "",
        "type": tx_type,
        "amount_range": amount_range,
        "transaction_date": transaction_date,
        "disclosure_date": x.get("disclosure_date") or None,
        "value_mid": _amount_mid(str(amount_range)),
        "asset": x.get("asset") or "",
        "filing_portal": x.get("filing_url") or "",
    }
    return ticker, trade


def _trade_key(ticker: str, trade: dict) -> tuple:
    return (
        str(trade.get("member") or "").lower(),
        ticker,
        str(trade.get("transaction_date") or ""),
        str(trade.get("disclosure_date") or ""),
        str(trade.get("type") or "").lower(),
        str(trade.get("amount_range") or ""),
        str(trade.get("asset") or ""),
    )


def fetch_congress_for_universe(us_tickers: list[str]) -> dict[str, list[dict]]:
    """Map the already-validated canonical snapshot onto Vestra's US universe."""
    universe = {str(t).split(".")[0].upper() for t in us_tickers if t}
    if not universe:
        return {}
    payload = _load_snapshot()
    if not payload:
        return {}

    grouped: dict[str, list[dict]] = {}
    seen: set[tuple] = set()
    source_rows = 0
    for item in payload.get("trades") or []:
        if not isinstance(item, dict):
            continue
        normalized = _normalize_one(item)
        if not normalized:
            continue
        source_rows += 1
        ticker, trade = normalized
        if ticker not in universe:
            continue
        key = _trade_key(ticker, trade)
        if key in seen:
            continue
        seen.add(key)
        grouped.setdefault(ticker, []).append(trade)

    for ticker, trades in grouped.items():
        trades.sort(
            key=lambda x: str(x.get("disclosure_date") or x.get("transaction_date") or ""),
            reverse=True,
        )
        grouped[ticker] = trades[:MAX_PER_TICKER]

    log.info(
        "congress: mapped %d canonical disclosures from %s onto %d Vestra tickers",
        source_rows,
        payload.get("source") or "politicians snapshot",
        len(grouped),
    )
    return grouped
