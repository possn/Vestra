"""US Congressional stock trade disclosures, fetched server-side.

The Vestra market build uses Bargo's public Congress REST API as a recent
STOCK Act aggregation layer. The source itself derives records from the House
Clerk and Senate eFD disclosure systems. Congress data are contextual evidence,
not part of the core Vestra company score.

Important constraints:
- disclosures are delayed by law and are not real-time trades;
- amounts are disclosed as ranges, never exact transaction values;
- the free feed is a rolling recent window and is rate-limited;
- failures must degrade to an empty contextual layer, never fail the company
  fundamentals/scoring pipeline.
"""
from __future__ import annotations

import datetime
import logging
import re
import time

import requests

log = logging.getLogger("congress")

HEADERS = {
    "User-Agent": "Vestra research-tool finscanner-app@proton.me",
    "Accept": "application/json",
}
API_BASE = "https://www.bargo.ai/free-apis/congress/v1"
REQUEST_TIMEOUT = 15
LOOKBACK_DAYS = 92
PAGE_SIZE = 100
# Stay comfortably inside the keyless daily request allowance. A maximum of ten
# pages gives a useful recent cross-Congress sample without making one request
# per ticker (the previous implementation could attempt >1,000 requests).
MAX_PAGES = 10


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


def _normalize_one(x: dict) -> tuple[str, dict] | None:
    ticker = str(x.get("ticker") or "").strip().upper()
    if not ticker:
        return None
    raw_type = str(x.get("type") or x.get("transaction_type") or "").lower()
    if "purchase" in raw_type or "buy" in raw_type:
        tx_type = "buy"
    elif "sale" in raw_type or "sell" in raw_type:
        tx_type = "sell"
    else:
        tx_type = raw_type or "trade"
    amount_range = x.get("amount_range") or x.get("amount") or "—"
    transaction_date = x.get("transaction_date") or x.get("date")
    if not transaction_date:
        return None
    trade = {
        "member": x.get("member") or x.get("representative") or x.get("name") or "Membro do Congresso",
        "member_slug": x.get("member_slug") or x.get("slug") or "",
        "chamber": str(x.get("chamber") or "").lower(),
        "state": x.get("state") or "",
        "party": x.get("party") or "",
        "type": tx_type,
        "amount_range": amount_range,
        "transaction_date": transaction_date,
        "disclosure_date": x.get("disclosure_date") or x.get("filed_date") or x.get("filing_date"),
        "value_mid": _amount_mid(amount_range),
        "asset": x.get("asset") or x.get("security") or "",
        "filing_portal": x.get("filing_portal") or "",
    }
    # Bargo publishes these fields when available. They are useful context but
    # remain descriptive and never feed the core company score.
    for source_key, target_key in (
        ("est_price", "estimated_trade_price"),
        ("recent_price", "recent_price"),
        ("perf_pct", "performance_pct"),
        ("outcome", "performance_outcome"),
    ):
        value = x.get(source_key)
        if value is not None:
            trade[target_key] = value
    return ticker, trade


def _trade_key(trade: dict) -> tuple:
    return (
        str(trade.get("member") or "").lower(),
        str(trade.get("ticker") or "").upper(),
        str(trade.get("transaction_date") or ""),
        str(trade.get("disclosure_date") or ""),
        str(trade.get("type") or "").lower(),
        str(trade.get("amount_range") or ""),
    )


def fetch_congress_for_universe(us_tickers: list[str]) -> dict[str, list[dict]]:
    """Fetch one recent global feed, then map it onto Vestra's US universe.

    This replaces the old N-tickers/N-requests strategy. It is faster, respects
    free-tier limits, and avoids treating a transient per-ticker 403 as proof
    that the whole source has been retired.
    """
    universe = {str(t).split(".")[0].upper() for t in us_tickers if t}
    if not universe:
        return {}

    from_date = (datetime.date.today() - datetime.timedelta(days=LOOKBACK_DAYS)).isoformat()
    grouped: dict[str, list[dict]] = {}
    seen: set[tuple] = set()
    fetched_rows = 0

    for page in range(MAX_PAGES):
        try:
            resp = requests.get(
                f"{API_BASE}/trades",
                headers=HEADERS,
                params={"from": from_date, "limit": PAGE_SIZE, "page": page},
                timeout=REQUEST_TIMEOUT,
            )
            if resp.status_code == 429:
                log.warning("Congress feed rate-limited on page %d; keeping %d rows already fetched", page, fetched_rows)
                break
            resp.raise_for_status()
            payload = resp.json()
            raw = payload if isinstance(payload, list) else (payload.get("trades") or payload.get("data") or [])
            if not isinstance(raw, list) or not raw:
                break

            fetched_rows += len(raw)
            for item in raw:
                if not isinstance(item, dict):
                    continue
                normalized = _normalize_one(item)
                if not normalized:
                    continue
                ticker, trade = normalized
                if ticker not in universe:
                    continue
                trade_with_ticker = {"ticker": ticker, **trade}
                key = _trade_key(trade_with_ticker)
                if key in seen:
                    continue
                seen.add(key)
                # stocks.json stores each trade under its ticker, so the ticker is
                # redundant inside the nested record and can be omitted there.
                grouped.setdefault(ticker, []).append(trade)

            # The API returns newest first. If a short page is returned, there is
            # no next full page to retrieve.
            if len(raw) < PAGE_SIZE:
                break
            time.sleep(0.12)
        except Exception as exc:
            log.warning("Congress global feed page %d failed (%s: %s)", page, type(exc).__name__, exc)
            break

    for ticker, trades in grouped.items():
        trades.sort(key=lambda x: str(x.get("disclosure_date") or x.get("transaction_date") or ""), reverse=True)
        grouped[ticker] = trades[:100]

    log.info(
        "congress: fetched %d recent disclosures; %d Vestra tickers had matching STOCK Act activity",
        fetched_rows,
        len(grouped),
    )
    return grouped
