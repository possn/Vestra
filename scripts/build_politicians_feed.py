"""Build Vestra's canonical congressional disclosure feed.

The browser never calls third-party Congress APIs directly. This job fetches
recent STOCK Act disclosures server-side, normalizes them, and publishes a
small data/politicians.json snapshot.

Provider policy:
1. Capitol Trades structured Next.js flight data (primary)
2. CongressInvests API (fallback only when its own data are fresh)

A source is accepted only when the newest disclosure is recent enough. This
prevents stale providers from advertising themselves as current indefinitely.
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import re
import time
from pathlib import Path
from urllib.parse import urlencode

import requests

log = logging.getLogger("politicians-feed")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "politicians.json"
DAYS = 92
MAX_STALE_DAYS = 60
TIMEOUT = 25
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36 Vestra/1.0",
    "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.7",
}

CAPITOL_URL = "https://www.capitoltrades.com/trades"
CONGRESSINVESTS_API = "https://congressinfor-production.up.railway.app"
PUSH_RE = re.compile(r'self\.__next_f\.push\((\[.*?\])\)</script>', re.S)
TRADE_NEEDLE = '{"_issuerId":'
TOTAL_PAGES_RE = re.compile(r'"totalPages":(\d+)')


def text(v) -> str:
    return str(v or "").strip()


def iso_date(v) -> str:
    s = text(v)
    return s[:10] if re.match(r"^\d{4}-\d{2}-\d{2}", s) else ""


def display_amount_from_value(v) -> str:
    try:
        n = float(v)
    except (TypeError, ValueError):
        return "—"
    if n <= 0:
        return "—"
    return f"≈ ${n:,.0f}"


def trade_key(x: dict) -> tuple:
    return (
        x["member"].casefold(), x["ticker"], x["transaction_date"],
        x.get("disclosure_date", ""), x.get("type", ""), x.get("amount", ""),
        x.get("asset", ""),
    )


def _extract_flight(html: str) -> str:
    parts: list[str] = []
    for raw in PUSH_RE.findall(html):
        try:
            chunk = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(chunk, list) and len(chunk) >= 2 and isinstance(chunk[1], str):
            parts.append(chunk[1])
    return "".join(parts)


def _capitol_normalize(obj: dict) -> dict | None:
    issuer = obj.get("issuer") or {}
    pol = obj.get("politician") or {}
    ticker = text(issuer.get("issuerTicker")).upper()
    member = " ".join(filter(None, [text(pol.get("nickname") or pol.get("firstName")), text(pol.get("lastName"))])).strip()
    tx_date = iso_date(obj.get("txDate"))
    disclosure = iso_date(obj.get("pubDate"))
    if not ticker or ticker == "N/A" or not member or not tx_date:
        return None
    raw_type = text(obj.get("txType")).lower()
    if "buy" in raw_type or "purchase" in raw_type:
        kind = "buy"
    elif "sell" in raw_type or "sale" in raw_type:
        kind = "sell"
    else:
        kind = raw_type or "trade"
    amount = text(obj.get("size") or obj.get("amount")) or display_amount_from_value(obj.get("value"))
    return {
        "ticker": ticker,
        "member": member,
        "chamber": text(pol.get("chamber")).capitalize(),
        "party": text(pol.get("party")).capitalize(),
        "state": text(pol.get("_stateId")).upper(),
        "type": kind,
        "amount": amount or "—",
        "transaction_date": tx_date,
        "disclosure_date": disclosure,
        "asset": text(issuer.get("issuerName")),
        "filing_url": "",
    }


def _capitol_page(page: int) -> tuple[list[dict], int | None]:
    query = urlencode({"page": page})
    r = requests.get(f"{CAPITOL_URL}?{query}", headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    flight = _extract_flight(r.text)
    total_m = TOTAL_PAGES_RE.search(flight)
    total_pages = int(total_m.group(1)) if total_m else None
    decoder = json.JSONDecoder()
    rows: list[dict] = []
    i = 0
    while True:
        j = flight.find(TRADE_NEEDLE, i)
        if j < 0:
            break
        try:
            obj, end = decoder.raw_decode(flight, j)
        except json.JSONDecodeError:
            i = j + len(TRADE_NEEDLE)
            continue
        i = end
        if not isinstance(obj, dict) or "_txId" not in obj:
            continue
        item = _capitol_normalize(obj)
        if item:
            rows.append(item)
    return rows, total_pages


def fetch_capitol_trades() -> tuple[list[dict], dict]:
    cutoff = dt.date.today() - dt.timedelta(days=DAYS)
    rows: list[dict] = []
    seen: set[tuple] = set()
    total_pages: int | None = None
    # Recent pages are newest first. Eight pages is normally hundreds of rows;
    # stop early once a page is entirely older than our lookback.
    for page in range(1, 9):
        page_rows, page_count = _capitol_page(page)
        if total_pages is None:
            total_pages = page_count
        if not page_rows:
            break
        page_has_recent = False
        for item in page_rows:
            d = iso_date(item.get("disclosure_date")) or iso_date(item.get("transaction_date"))
            if d and dt.date.fromisoformat(d) < cutoff:
                continue
            page_has_recent = True
            key = trade_key(item)
            if key in seen:
                continue
            seen.add(key)
            rows.append(item)
        if not page_has_recent:
            break
        if total_pages is not None and page >= total_pages:
            break
        time.sleep(0.25)
    rows.sort(key=lambda x: (x.get("disclosure_date") or x["transaction_date"], x["transaction_date"]), reverse=True)
    return rows, {"provider": "Capitol Trades", "last_updated": rows[0].get("disclosure_date") if rows else ""}


def _congressinvests_normalize(raw: dict) -> dict | None:
    ticker = text(raw.get("ticker")).upper()
    member = text(raw.get("member") or raw.get("politician") or raw.get("representative"))
    tx_date = iso_date(raw.get("tx_date") or raw.get("transaction_date") or raw.get("date"))
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
        "party": text(raw.get("party")),
        "state": text(raw.get("state")),
        "type": kind,
        "amount": text(raw.get("amount") or raw.get("amount_range")) or "—",
        "transaction_date": tx_date,
        "disclosure_date": iso_date(raw.get("disclosed") or raw.get("disclosure_date") or raw.get("filing_date")),
        "asset": text(raw.get("asset") or raw.get("security")),
        "filing_url": text(raw.get("link") or raw.get("filing_url") or raw.get("filing_portal")),
    }


def fetch_congressinvests() -> tuple[list[dict], dict]:
    rows: list[dict] = []
    seen: set[tuple] = set()
    offset = 0
    metadata: dict = {}
    for _page in range(6):
        r = requests.get(
            f"{CONGRESSINVESTS_API}/trades/recent",
            params={"days": DAYS, "limit": 500, "offset": offset},
            headers={"User-Agent": HEADERS["User-Agent"], "Accept": "application/json"},
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
            item = _congressinvests_normalize(raw)
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
    return rows, {"provider": "CongressInvests API", "last_updated": text(metadata.get("last_updated"))}


def newest_disclosure(trades: list[dict]) -> str:
    vals = [iso_date(x.get("disclosure_date")) or iso_date(x.get("transaction_date")) for x in trades]
    vals = [v for v in vals if v]
    return max(vals) if vals else ""


def is_fresh(trades: list[dict]) -> bool:
    newest = newest_disclosure(trades)
    if not newest:
        return False
    age = (dt.date.today() - dt.date.fromisoformat(newest)).days
    return age <= MAX_STALE_DAYS


def build_members(trades: list[dict]) -> list[dict]:
    by_name: dict[str, dict] = {}
    for x in trades:
        key = x["member"].strip()
        m = by_name.setdefault(key, {
            "key": "congress:" + "-".join("".join(c.lower() if c.isalnum() else " " for c in key).split()),
            "name": key,
            "chamber": x.get("chamber", ""),
            "party": x.get("party", ""),
            "state": x.get("state", ""),
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


def choose_provider() -> tuple[list[dict], dict]:
    errors: list[str] = []
    for name, fetcher in (("Capitol Trades", fetch_capitol_trades), ("CongressInvests API", fetch_congressinvests)):
        try:
            trades, meta = fetcher()
            newest = newest_disclosure(trades)
            if len(trades) < 10:
                raise RuntimeError(f"only {len(trades)} trades")
            if not is_fresh(trades):
                raise RuntimeError(f"stale newest disclosure {newest or 'unknown'}")
            log.info("politicians provider %s accepted: %d trades, newest %s", name, len(trades), newest)
            return trades, meta
        except Exception as exc:
            errors.append(f"{name}: {exc}")
            log.warning("politicians provider %s rejected: %s", name, exc)
    raise RuntimeError("; ".join(errors))


def main() -> None:
    try:
        trades, meta = choose_provider()
    except Exception as exc:
        if OUT.exists():
            # Do not silently stamp a stale file as current. Keep the old snapshot
            # untouched; the frontend shows its generated/data dates honestly.
            log.warning("no fresh politicians provider (%s); preserving previous snapshot", exc)
            return
        raise
    members = build_members(trades)
    provider = text(meta.get("provider")) or "Congress disclosure provider"
    payload = {
        "schema_version": 2,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source": provider,
        "source_origin": "Public STOCK Act disclosures; House Clerk and Senate eFD",
        "window_days": DAYS,
        "source_last_updated": text(meta.get("last_updated")) or newest_disclosure(trades),
        "newest_disclosure": newest_disclosure(trades),
        "data_current": True,
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
