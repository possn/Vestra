#!/usr/bin/env python3
"""Transport hardening for the Vestra macro calendar.

Keeps update_macro_events.py as the canonical schema/fail-closed pipeline while
making BLS/Census HTML retrieval use the same explicit Vestra HTTP session.
"""
from __future__ import annotations

import re
from datetime import date, datetime
from io import StringIO

import pandas as pd

import update_macro_events as base


def table_rows_from_session(session, url: str) -> list[list[str]]:
    page = base.fetch_text(session, url)
    tables = pd.read_html(StringIO(page))
    rows: list[list[str]] = []
    for frame in tables:
        for values in frame.astype(str).values.tolist():
            rows.append([str(value).strip() for value in values])
    return rows


def census_events(session) -> list[dict]:
    rows = table_rows_from_session(session, base.SOURCES["census"][1])
    out: list[dict] = []
    months = "|".join(base.MONTHS)
    for row in rows:
        joined = " | ".join(row)
        if "Advance Monthly Sales for Retail and Food Services" not in joined:
            continue
        match = re.search(
            rf"\b({months})\s+(\d{{1,2}}),\s*(\d{{4}})\b",
            joined,
        )
        if not match:
            continue
        release_date = date(int(match.group(3)), base.MONTHS[match.group(1)], int(match.group(2)))
        time_match = re.search(r"\b(\d{1,2}:\d{2})\s*(AM|PM)\b", joined, flags=re.I)
        reference_period = ""
        for cell in reversed(row):
            if re.search(rf"\b({months})\s+\d{{4}}\b", cell):
                reference_period = cell
                break
        event = {
            "date": release_date.isoformat(),
            "title": f"Retail Sales EUA · {reference_period}" if reference_period else "Retail Sales EUA",
            "short_title": "Retail Sales",
            "category": "activity",
            "region": "EUA",
            "importance": "high",
            "source": "census",
        }
        if time_match:
            event["time_local"] = f"{time_match.group(1)} {time_match.group(2).upper()} ET"
        out.append(event)
    return out


def _parse_bls_table_date(raw: str) -> date | None:
    text = str(raw).strip()
    # Annual BLS list-view rows use e.g. "Friday, October 2, 2026".
    text = re.sub(r"^[A-Za-z]+,\s*", "", text)
    for fmt in ("%B %d, %Y", "%b %d, %Y"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    return None


def _bls_html_events(session) -> list[dict]:
    today = date.today()
    mapping = [
        ("Consumer Price Index", "CPI EUA", "inflation", "high"),
        ("Producer Price Index", "PPI EUA", "inflation", "high"),
        ("Employment Situation", "NFP EUA", "labour", "critical"),
        ("Job Openings and Labor Turnover Survey", "JOLTS", "labour", "high"),
    ]
    out: list[dict] = []
    for year in (today.year, today.year + 1):
        url = f"https://www.bls.gov/schedule/{year}/"
        try:
            rows = table_rows_from_session(session, url)
        except Exception:
            continue
        for row in rows:
            joined = " | ".join(row)
            chosen = next((entry for entry in mapping if entry[0].lower() in joined.lower()), None)
            if not chosen:
                continue
            release_date = next((_parse_bls_table_date(cell) for cell in row if _parse_bls_table_date(cell)), None)
            if not release_date:
                # Some table layouts combine the date with other cells.
                date_match = re.search(
                    r"(?:Monday|Tuesday|Wednesday|Thursday|Friday),\s+"
                    r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+"
                    r"(\d{1,2}),\s*(\d{4})",
                    joined,
                )
                if date_match:
                    release_date = date(int(date_match.group(3)), base.MONTHS[date_match.group(1)], int(date_match.group(2)))
            if not release_date:
                continue
            time_match = re.search(r"\b(\d{1,2}:\d{2})\s*(AM|PM)\b", joined, flags=re.I)
            _needle, short_title, category, importance = chosen
            reference = base.reference_month(joined)
            if short_title == "NFP EUA":
                title = f"Payrolls / NFP EUA · {reference}" if reference else "Payrolls / NFP EUA"
            else:
                title = f"{short_title} · {reference}" if reference else short_title
            event = {
                "date": release_date.isoformat(),
                "title": title,
                "short_title": short_title,
                "category": category,
                "region": "EUA",
                "importance": importance,
                "source": "bls",
            }
            if time_match:
                event["time_local"] = f"{time_match.group(1)} {time_match.group(2).upper()} ET"
            out.append(event)
    return out


def bls_events(session) -> list[dict]:
    try:
        events = base.bls_events(session)
        if events:
            return events
    except Exception as ics_error:
        try:
            events = _bls_html_events(session)
            if events:
                return events
        except Exception:
            pass
        raise ics_error
    events = _bls_html_events(session)
    if not events:
        raise RuntimeError("BLS official ICS and HTML calendars returned no usable events")
    return events


def install() -> None:
    base.ADAPTERS["bls"] = bls_events
    base.ADAPTERS["census"] = census_events


def main() -> int:
    install()
    return base.main()


if __name__ == "__main__":
    raise SystemExit(main())
