"""Merge recent U.S. Senate eFD PTR stock trades into data/politicians.json.

The House builder remains the resilient baseline. Senate enrichment is best-effort:
if the official eFD portal is unavailable or changes shape, the valid House snapshot
is preserved unchanged rather than publishing empty or stale replacement data.
"""
from __future__ import annotations

import datetime as dt
import json
import logging
import re
import time
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

ROOT = "https://efdsearch.senate.gov"
LANDING_URL = f"{ROOT}/search/home/"
SEARCH_URL = f"{ROOT}/search/"
REPORTS_URL = f"{ROOT}/search/report/data/"
OUT = Path(__file__).resolve().parents[1] / "data" / "politicians.json"
LOOKBACK_DAYS = 92
PAGE_SIZE = 100
MAX_PAGES = 10
TIMEOUT = 20

log = logging.getLogger("senate_efd")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

HEADERS = {
    "User-Agent": "Vestra research-tool finscanner-app@proton.me",
    "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
}


def iso_date(value: str) -> str:
    value = str(value or "").strip()
    for fmt in ("%m/%d/%Y", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(value[:10], fmt).date().isoformat()
        except ValueError:
            pass
    return ""


def slugify(value: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", str(value or "").lower()).strip("-")
    return s


def normalize_type(raw: str) -> str:
    s = str(raw or "").strip().lower()
    if "purchase" in s or s == "buy":
        return "buy"
    if "sale" in s or "sell" in s:
        return "sell"
    if "exchange" in s:
        return "exchange"
    return "trade"


def csrf_handshake(session: requests.Session) -> str:
    r = session.get(LANDING_URL, headers=HEADERS, timeout=TIMEOUT)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    node = soup.find(attrs={"name": "csrfmiddlewaretoken"})
    if not node or not node.get("value"):
        raise RuntimeError("Senate eFD CSRF token missing")
    token = str(node.get("value"))
    ack = session.post(
        LANDING_URL,
        data={"csrfmiddlewaretoken": token, "prohibition_agreement": "1"},
        headers={**HEADERS, "Referer": LANDING_URL},
        timeout=TIMEOUT,
    )
    ack.raise_for_status()
    return session.cookies.get("csrftoken") or session.cookies.get("csrf") or token


def fetch_report_rows(session: requests.Session, csrf: str) -> list[list]:
    cutoff = (dt.date.today() - dt.timedelta(days=LOOKBACK_DAYS)).strftime("%m/%d/%Y")
    rows: list[list] = []
    for page in range(MAX_PAGES):
        start = page * PAGE_SIZE
        r = session.post(
            REPORTS_URL,
            data={
                "start": str(start),
                "length": str(PAGE_SIZE),
                "report_types": "[11]",
                "submitted_start_date": f"{cutoff} 00:00:00",
                "csrfmiddlewaretoken": csrf,
            },
            headers={**HEADERS, "Referer": SEARCH_URL, "X-CSRFToken": csrf},
            timeout=TIMEOUT,
        )
        r.raise_for_status()
        payload = r.json()
        batch = payload.get("data") or []
        if not isinstance(batch, list) or not batch:
            break
        rows.extend(batch)
        if len(batch) < PAGE_SIZE:
            break
        time.sleep(0.15)
    return rows


def parse_report(session: requests.Session, row: list) -> list[dict]:
    if not isinstance(row, list) or len(row) < 5:
        return []
    first, last, _office, link_html, filed_raw = row[:5]
    member = " ".join(x for x in (str(first or "").strip(), str(last or "").strip()) if x).strip()
    if not member:
        return []
    link_node = BeautifulSoup(str(link_html or ""), "html.parser").find("a")
    href = link_node.get("href") if link_node else ""
    if not href:
        return []
    filing_url = urljoin(ROOT, href)
    filed = iso_date(str(filed_raw or ""))
    r = session.get(filing_url, headers={**HEADERS, "Referer": SEARCH_URL}, timeout=TIMEOUT)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    tbody = soup.find("tbody")
    if not tbody:
        return []

    cutoff = dt.date.today() - dt.timedelta(days=LOOKBACK_DAYS)
    out: list[dict] = []
    for tr in tbody.find_all("tr"):
        cols = [c.get_text(" ", strip=True) for c in tr.find_all("td")]
        if len(cols) < 8:
            continue
        tx_date = iso_date(cols[1])
        if not tx_date:
            continue
        try:
            if dt.date.fromisoformat(tx_date) < cutoff:
                continue
        except ValueError:
            continue
        ticker = str(cols[3] or "").strip().upper()
        if ticker in {"", "--", "N/A"} or not re.fullmatch(r"[A-Z0-9.\-]{1,12}", ticker):
            continue
        asset = cols[4] if len(cols) > 4 else ""
        tx_type = normalize_type(cols[6] if len(cols) > 6 else "")
        amount = cols[7] if len(cols) > 7 else "—"
        out.append({
            "ticker": ticker,
            "member": member,
            "member_slug": slugify(member),
            "chamber": "Senate",
            "party": "",
            "state": "",
            "type": tx_type,
            "amount": amount or "—",
            "transaction_date": tx_date,
            "disclosure_date": filed or tx_date,
            "asset": asset,
            "filing_url": filing_url,
        })
    return out


def trade_key(x: dict) -> tuple:
    return (
        str(x.get("member") or "").lower(),
        str(x.get("ticker") or "").upper(),
        str(x.get("transaction_date") or ""),
        str(x.get("disclosure_date") or ""),
        str(x.get("type") or "").lower(),
        str(x.get("amount") or x.get("amount_range") or ""),
        str(x.get("asset") or ""),
    )


def rebuild_members(trades: list[dict]) -> list[dict]:
    grouped: dict[tuple, list[dict]] = {}
    for t in trades:
        key = (str(t.get("member") or ""), str(t.get("chamber") or ""), str(t.get("state") or ""))
        if not key[0]:
            continue
        grouped.setdefault(key, []).append(t)
    members = []
    for (name, chamber, state), rows in grouped.items():
        members.append({
            "key": f"congress:{slugify(name)}",
            "name": name,
            "chamber": chamber,
            "party": next((str(x.get("party") or "") for x in rows if x.get("party")), ""),
            "state": state,
            "count": len(rows),
            "buys": sum(1 for x in rows if x.get("type") == "buy"),
            "sells": sum(1 for x in rows if x.get("type") == "sell"),
            "last": max(str(x.get("transaction_date") or "") for x in rows),
        })
    return sorted(members, key=lambda x: (-x["count"], x["name"]))


def main() -> None:
    payload = json.loads(OUT.read_text(encoding="utf-8"))
    house_trades = [x for x in (payload.get("trades") or []) if isinstance(x, dict)]
    try:
        session = requests.Session()
        session.headers.update(HEADERS)
        csrf = csrf_handshake(session)
        reports = fetch_report_rows(session, csrf)
        senate: list[dict] = []
        failures = 0
        for row in reports:
            try:
                senate.extend(parse_report(session, row))
            except Exception as exc:
                failures += 1
                log.warning("Senate PTR parse failed: %s", exc)
            time.sleep(0.08)
        if not senate:
            log.warning("Senate eFD returned no normalized stock trades; preserving House-only snapshot")
            return

        merged: dict[tuple, dict] = {trade_key(x): x for x in house_trades}
        for trade in senate:
            merged[trade_key(trade)] = trade
        trades = sorted(
            merged.values(),
            key=lambda x: (str(x.get("disclosure_date") or ""), str(x.get("transaction_date") or "")),
            reverse=True,
        )
        newest = max(str(x.get("disclosure_date") or "") for x in trades)
        payload["trades"] = trades
        payload["members"] = rebuild_members(trades)
        payload["coverage_chambers"] = sorted({str(x.get("chamber") or "") for x in trades if x.get("chamber")})
        payload["source"] = "U.S. House Clerk + Senate eFD"
        payload["source_origin"] = "Official public STOCK Act disclosures"
        payload["newest_disclosure"] = newest
        payload["source_last_updated"] = newest
        payload["data_current"] = True
        payload["senate_enrichment"] = {
            "reports_found": len(reports),
            "stock_trades": len(senate),
            "report_failures": failures,
        }
        OUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        log.info("Senate eFD merged: %d reports, %d stock trades, %d failures", len(reports), len(senate), failures)
    except Exception as exc:
        log.warning("Senate eFD unavailable; preserving House-only snapshot (%s: %s)", type(exc).__name__, exc)


if __name__ == "__main__":
    main()
