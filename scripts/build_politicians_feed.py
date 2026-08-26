"""Build Vestra's canonical congressional disclosure feed.

The browser never calls third-party Congress APIs directly. This job fetches
recent STOCK Act disclosures server-side, normalizes them, and publishes a
small data/politicians.json snapshot. If the source is temporarily unavailable,
the previous valid snapshot is preserved rather than replaced with an empty file.
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import time
from pathlib import Path

import requests

log = logging.getLogger("politicians-feed")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "politicians.json"
API = "https://congressinfor-production.up.railway.app"
DAYS = 92
PAGE_SIZE = 500
MAX_PAGES = 6
TIMEOUT = 20
HEADERS = {
    "User-Agent": "Vestra research-tool finscanner-app@proton.me",
    "Accept": "application/json",
}


def text(v) -> str:
    return str(v or "").strip()


def normalize_trade(raw: dict) -> dict | None:
    ticker = text(raw.get("ticker")).upper()
    member = text(raw.get("member") or raw.get("politician") or raw.get("representative"))
    tx_date = text(raw.get("tx_date") or raw.get("transaction_date") or raw.get("date"))
    if not ticker or not member or not tx_date:
        return None
    kind = text(raw.get("trade_type") or raw.get("type") or raw.get("transaction_type")).lower()
    if "buy" in kind or "purchase" in kind:
        kind = "buy"
    elif "sell" in kind or "sale" in kind:
        kind = "sell"
    else:
        kind = kind or "trade"
    return {
        "ticker": ticker,
        "member": member,
        "chamber": text(raw.get("chamber")),
        "type": kind,
        "amount": text(raw.get("amount") or raw.get("amount_range")) or "—",
        "transaction_date": tx_date,
        "disclosure_date": text(raw.get("disclosed") or raw.get("disclosure_date") or raw.get("filing_date")),
        "asset": text(raw.get("asset") or raw.get("security")),
        "filing_url": text(raw.get("link") or raw.get("filing_url") or raw.get("filing_portal")),
    }


def trade_key(x: dict) -> tuple:
    return (
        x["member"].casefold(), x["ticker"], x["transaction_date"],
        x.get("disclosure_date", ""), x.get("type", ""), x.get("amount", ""),
        x.get("asset", ""),
    )


def fetch_recent() -> tuple[list[dict], dict]:
    rows: list[dict] = []
    seen: set[tuple] = set()
    metadata: dict = {}
    offset = 0
    for page in range(MAX_PAGES):
        r = requests.get(
            f"{API}/trades/recent",
            params={"days": DAYS, "limit": PAGE_SIZE, "offset": offset},
            headers=HEADERS,
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        payload = r.json()
        raw_rows = payload.get("trades", []) if isinstance(payload, dict) else payload
        if not isinstance(raw_rows, list):
            raise RuntimeError("CongressInvests returned an unexpected payload")
        metadata = payload if isinstance(payload, dict) else metadata
        for raw in raw_rows:
            if not isinstance(raw, dict):
                continue
            item = normalize_trade(raw)
            if not item:
                continue
            key = trade_key(item)
            if key in seen:
                continue
            seen.add(key)
            rows.append(item)
        if not raw_rows or not (isinstance(payload, dict) and payload.get("has_more")):
            break
        offset += len(raw_rows)
        time.sleep(0.15)
    rows.sort(key=lambda x: (x.get("disclosure_date") or x["transaction_date"], x["transaction_date"]), reverse=True)
    return rows, metadata


def build_members(trades: list[dict]) -> list[dict]:
    by_name: dict[str, dict] = {}
    for x in trades:
        key = x["member"].strip()
        m = by_name.setdefault(key, {
            "key": "congress:" + "-".join("".join(c.lower() if c.isalnum() else " " for c in key).split()),
            "name": key,
            "chamber": x.get("chamber", ""),
            "count": 0,
            "buys": 0,
            "sells": 0,
            "last": "",
        })
        m["count"] += 1
        if x.get("type") == "buy":
            m["buys"] += 1
        elif x.get("type") == "sell":
            m["sells"] += 1
        latest = x.get("disclosure_date") or x.get("transaction_date") or ""
        if latest > m["last"]:
            m["last"] = latest
    return sorted(by_name.values(), key=lambda x: (-x["count"], x["name"]))


def main() -> None:
    try:
        trades, meta = fetch_recent()
    except Exception as exc:
        if OUT.exists():
            log.warning("politicians source unavailable (%s); preserving previous snapshot", exc)
            return
        raise
    if len(trades) < 10:
        if OUT.exists():
            log.warning("politicians source returned only %d rows; preserving previous snapshot", len(trades))
            return
        raise RuntimeError(f"politicians feed too small: {len(trades)}")
    members = build_members(trades)
    payload = {
        "schema_version": 1,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source": "CongressInvests API",
        "source_origin": "House Clerk + Senate eFD STOCK Act disclosures",
        "window_days": DAYS,
        "source_last_updated": text(meta.get("last_updated")) if isinstance(meta, dict) else "",
        "data_current": bool(meta.get("data_current", True)) if isinstance(meta, dict) else True,
        "members": members,
        "trades": trades,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    tmp.replace(OUT)
    log.info("politicians: %d trades, %d members", len(trades), len(members))


if __name__ == "__main__":
    main()
