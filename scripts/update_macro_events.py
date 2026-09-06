#!/usr/bin/env python3
"""Refresh Vestra's compact macro calendar from official sources.

Runtime browser code never calls these sources directly. This script runs in CI,
validates each source independently, and updates data/macro-events.json. A failed
source keeps its previously validated future events instead of deleting them.
"""
from __future__ import annotations

import json
import re
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

import pandas as pd
import requests
from lxml import html

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "macro-events.json"
UA = "Vestra/1.0 macro-calendar (+https://github.com/possn/Vestra)"
TIMEOUT = 25

SOURCES = {
    "fed": ("Federal Reserve FOMC calendar", "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"),
    "bls": ("U.S. Bureau of Labor Statistics release calendar", "https://www.bls.gov/schedule/news_release/bls.ics"),
    "bea": ("U.S. Bureau of Economic Analysis release schedule", "https://www.bea.gov/news/schedule"),
    "ecb": ("ECB Governing Council calendar", "https://www.ecb.europa.eu/press/calendars/mgcgc/html/index.en.html"),
    "census": ("U.S. Census Bureau economic indicator release calendar", "https://www.census.gov/economic-indicators/calendar-listview.html"),
}

MONTHS = {
    "January": 1, "February": 2, "March": 3, "April": 4, "May": 5, "June": 6,
    "July": 7, "August": 8, "September": 9, "October": 10, "November": 11, "December": 12,
}


def session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept-Language": "en-US,en;q=0.8"})
    return s


def fetch_text(s: requests.Session, url: str) -> str:
    r = s.get(url, timeout=TIMEOUT)
    r.raise_for_status()
    return r.text


def iso(d: date) -> str:
    return d.isoformat()


def reference_month(raw: str) -> str:
    match = re.search(r"\bfor\s+([A-Z][a-z]+\s+\d{4})\b", raw)
    return match.group(1) if match else ""


def bls_events(s: requests.Session) -> list[dict]:
    text = fetch_text(s, SOURCES["bls"][1]).replace("\r\n", "\n")
    # RFC5545 line unfolding.
    text = re.sub(r"\n[ \t]", "", text)
    blocks = re.findall(r"BEGIN:VEVENT\n(.*?)\nEND:VEVENT", text, flags=re.S)
    out: list[dict] = []
    mapping = [
        ("Consumer Price Index", "CPI EUA", "inflation", "high"),
        ("Producer Price Index", "PPI EUA", "inflation", "high"),
        ("Employment Situation", "NFP EUA", "labour", "critical"),
        ("Job Openings and Labor Turnover Survey", "JOLTS", "labour", "high"),
    ]
    for block in blocks:
        summary_m = re.search(r"^SUMMARY(?:;[^:]*)?:(.+)$", block, flags=re.M)
        start_m = re.search(r"^DTSTART(?:;[^:]*)?:(\d{8})(?:T(\d{4,6}))?", block, flags=re.M)
        if not summary_m or not start_m:
            continue
        summary = summary_m.group(1).replace("\\,", ",").strip()
        chosen = next((item for item in mapping if item[0].lower() in summary.lower()), None)
        if not chosen:
            continue
        d = datetime.strptime(start_m.group(1), "%Y%m%d").date()
        hm = start_m.group(2) or ""
        time_local = f"{hm[:2]}:{hm[2:4]} ET" if len(hm) >= 4 else None
        needle, short_title, category, importance = chosen
        ref = reference_month(summary)
        if short_title == "NFP EUA":
            title = f"Payrolls / NFP EUA · {ref}" if ref else "Payrolls / NFP EUA"
        else:
            title = f"{short_title} · {ref}" if ref else short_title
        event = {
            "date": iso(d), "title": title, "short_title": short_title,
            "category": category, "region": "EUA", "importance": importance, "source": "bls",
        }
        if time_local:
            event["time_local"] = time_local
        out.append(event)
    return out


def fed_events(s: requests.Session) -> list[dict]:
    page = fetch_text(s, SOURCES["fed"][1])
    txt = " ".join(html.fromstring(page).text_content().split())
    today = date.today()
    out: list[dict] = []
    months = "|".join(MONTHS)
    for year in range(today.year, today.year + 3):
        match = re.search(rf"{year}\s+FOMC Meetings(.*?)(?={(year + 1)}\s+FOMC Meetings|Note:|$)", txt, flags=re.I)
        if not match:
            continue
        section = match.group(1)
        for m in re.finditer(rf"\b({months})\s+(\d{{1,2}})-(\d{{1,2}})(\*)?", section):
            month = MONTHS[m.group(1)]
            start = date(year, month, int(m.group(2)))
            end = date(year, month, int(m.group(3)))
            projections = bool(m.group(4))
            out.append({
                "date": iso(start), "date_end": iso(end),
                "title": "FOMC · reunião + projeções económicas" if projections else "FOMC · reunião de política monetária",
                "short_title": "FOMC", "category": "central_bank", "region": "EUA",
                "importance": "critical", "source": "fed",
            })
    return out


def ecb_events(s: requests.Session) -> list[dict]:
    page = fetch_text(s, SOURCES["ecb"][1])
    txt = "\n".join(line.strip() for line in html.fromstring(page).text_content().splitlines() if line.strip())
    lines = txt.splitlines()
    out: list[dict] = []
    pending_day1: date | None = None
    for idx, line in enumerate(lines):
        if not re.fullmatch(r"\d{2}/\d{2}/\d{4}", line):
            continue
        d = datetime.strptime(line, "%d/%m/%Y").date()
        desc = " ".join(lines[idx + 1: idx + 4]).lower()
        if "governing council" not in desc or "monetary policy meeting" not in desc:
            continue
        if "day 1" in desc:
            pending_day1 = d
            continue
        if "day 2" in desc:
            start = pending_day1 if pending_day1 and 0 <= (d - pending_day1).days <= 2 else d - timedelta(days=1)
            out.append({
                "date": iso(start), "date_end": iso(d), "title": "BCE · reunião de política monetária",
                "short_title": "BCE", "category": "central_bank", "region": "Eurozona",
                "importance": "high", "source": "ecb",
            })
            pending_day1 = None
    return out


def _table_rows(url: str) -> list[list[str]]:
    tables = pd.read_html(url)
    rows: list[list[str]] = []
    for df in tables:
        for values in df.astype(str).values.tolist():
            rows.append([str(v).strip() for v in values])
    return rows


def bea_events(_: requests.Session) -> list[dict]:
    rows = _table_rows(SOURCES["bea"][1])
    out: list[dict] = []
    today = date.today()
    for row in rows:
        joined = " | ".join(row)
        lower = joined.lower()
        if "personal income and outlays" not in lower and "gdp" not in lower:
            continue
        date_m = re.search(r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2})\b", joined)
        time_m = re.search(r"\b(\d{1,2}:\d{2})\s*(AM|PM)\b", joined, flags=re.I)
        if not date_m:
            continue
        month = MONTHS[date_m.group(1)]
        d = date(today.year, month, int(date_m.group(2)))
        # Schedule page is year-scoped; around year-end future January belongs next year.
        if d < today - timedelta(days=45):
            d = date(today.year + 1, month, int(date_m.group(2)))
        if "personal income and outlays" in lower:
            short, category, importance = "PCE EUA", "inflation", "high"
            ref = re.search(r"Personal Income and Outlays,\s*([^|]+)", joined, flags=re.I)
            title = f"PCE EUA · {ref.group(1).strip()}" if ref else "PCE EUA"
        else:
            short, category, importance = "GDP EUA", "growth", "high"
            ref = re.search(r"GDP[^,]*,?\s*([^|]+)", joined, flags=re.I)
            title = f"GDP EUA · {ref.group(1).strip()}" if ref and len(ref.group(1).strip()) < 80 else "GDP EUA"
        event = {
            "date": iso(d), "title": title, "short_title": short, "category": category,
            "region": "EUA", "importance": importance, "source": "bea",
        }
        if time_m:
            event["time_local"] = f"{time_m.group(1)} {time_m.group(2).upper()} ET"
        out.append(event)
    return out


def census_events(_: requests.Session) -> list[dict]:
    rows = _table_rows(SOURCES["census"][1])
    out: list[dict] = []
    for row in rows:
        joined = " | ".join(row)
        if "Advance Monthly Sales for Retail and Food Services" not in joined:
            continue
        dmatch = re.search(r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),\s*(\d{4})\b", joined)
        if not dmatch:
            continue
        d = date(int(dmatch.group(3)), MONTHS[dmatch.group(1)], int(dmatch.group(2)))
        tmatch = re.search(r"\b(\d{1,2}:\d{2})\s*(AM|PM)\b", joined, flags=re.I)
        period = ""
        for cell in reversed(row):
            if re.search(r"\b(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b", cell):
                period = cell
                break
        event = {
            "date": iso(d), "title": f"Retail Sales EUA · {period}" if period else "Retail Sales EUA",
            "short_title": "Retail Sales", "category": "activity", "region": "EUA",
            "importance": "high", "source": "census",
        }
        if tmatch:
            event["time_local"] = f"{tmatch.group(1)} {tmatch.group(2).upper()} ET"
        out.append(event)
    return out


ADAPTERS: dict[str, Callable[[requests.Session], list[dict]]] = {
    "bls": bls_events,
    "fed": fed_events,
    "ecb": ecb_events,
    "bea": bea_events,
    "census": census_events,
}


def validate_events(source: str, events: list[dict], today: date) -> list[dict]:
    valid: list[dict] = []
    seen = set()
    for event in events:
        if event.get("source") != source:
            continue
        try:
            d = date.fromisoformat(str(event["date"]))
        except Exception:
            continue
        if d < today - timedelta(days=14) or d > today + timedelta(days=550):
            continue
        key = (event.get("date"), event.get("date_end"), event.get("short_title"), event.get("source"))
        if key in seen:
            continue
        seen.add(key)
        valid.append(event)
    future = [e for e in valid if date.fromisoformat(e["date"]) >= today]
    if not future:
        raise RuntimeError(f"{source}: no plausible future events")
    return sorted(valid, key=lambda e: (e["date"], e.get("short_title", "")))


def load_previous() -> dict:
    try:
        return json.loads(OUTPUT.read_text(encoding="utf-8"))
    except Exception:
        return {"events": []}


def main() -> int:
    today = date.today()
    previous = load_previous()
    previous_events = previous.get("events") if isinstance(previous.get("events"), list) else []
    s = session()
    merged: list[dict] = []
    statuses: dict[str, dict] = {}

    for source, adapter in ADAPTERS.items():
        try:
            fresh = validate_events(source, adapter(s), today)
            merged.extend(fresh)
            statuses[source] = {"state": "fresh", "count": len(fresh)}
        except Exception as exc:
            fallback = [e for e in previous_events if e.get("source") == source]
            fallback = [e for e in fallback if str(e.get("date", "")) >= iso(today - timedelta(days=14))]
            if not fallback:
                raise RuntimeError(f"{source} refresh failed and no validated fallback exists: {exc}") from exc
            merged.extend(fallback)
            statuses[source] = {"state": "fallback", "count": len(fallback), "error": str(exc)[:240]}

    dedup = {}
    for event in merged:
        key = (event.get("date"), event.get("date_end"), event.get("short_title"), event.get("source"))
        dedup[key] = event
    events = sorted(dedup.values(), key=lambda e: (e.get("date", ""), e.get("short_title", "")))

    payload = {
        "schema_version": 2,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "window": "official schedules; refreshed automatically with per-source fail-closed fallback",
        "sources": {key: label for key, (label, _) in SOURCES.items()},
        "source_status": statuses,
        "events": events,
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(json.dumps({"events": len(events), "sources": statuses}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
