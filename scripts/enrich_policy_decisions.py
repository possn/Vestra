#!/usr/bin/env python3
"""Normalize central-bank calendar events to decision day and enrich ECB decisions.

The official calendars describe two-day Governing Council/FOMC meetings. For an
investor-facing catalyst calendar the actionable event is the decision, published
on day 2. This module therefore preserves the meeting start as context while
placing the event on decision day. ECB results are attached only from the exact
official monetary-policy release for that date.
"""
from __future__ import annotations

import json
import os
import re
from datetime import date
from pathlib import Path
from urllib.parse import urljoin

import requests
from lxml import html

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "macro-events.json"
UA = "Vestra/1.0 policy-decisions (+https://github.com/possn/Vestra)"
TIMEOUT = 20
ECB_INDEX = "https://www.ecb.europa.eu/press/govcdec/mopo/html/index.en.html"
ECB_SCHEMA = "ecb_rates_v1"
ECB_METRIC_KEYS = (
    "deposit_facility_pct",
    "main_refinancing_pct",
    "marginal_lending_pct",
)
RESULT_FIELDS = (
    "result_summary", "result_status", "result_released_at", "source_url",
    "result_metric_schema", "result_metrics",
)


def _load(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def normalize_decision_days(payload: dict) -> int:
    """Move multi-day ECB/FOMC entries to their official decision day."""
    changed = 0
    for event in payload.get("events") or []:
        if not isinstance(event, dict) or event.get("source") not in {"ecb", "fed"}:
            continue
        start = str(event.get("date") or "")
        end = str(event.get("date_end") or "")
        if not end:
            continue
        try:
            date.fromisoformat(start)
            date.fromisoformat(end)
        except Exception:
            continue
        event["meeting_start"] = start
        event["date"] = end
        event.pop("date_end", None)
        if event.get("source") == "ecb":
            event["title"] = "BCE · decisão de política monetária"
            event["short_title"] = "BCE"
            event["time_local"] = "14:15 CET"
        else:
            event["title"] = "FOMC · decisão de política monetária"
            event["short_title"] = "FOMC"
            event["time_local"] = "2:00 PM ET"
        changed += 1
    return changed


def _event_key(event: dict) -> tuple[str, str, str]:
    return (
        str(event.get("date") or ""),
        str(event.get("short_title") or ""),
        str(event.get("source") or ""),
    )


def carry_forward_ecb_results(payload: dict, previous: dict) -> int:
    old = {
        _event_key(event): event
        for event in (previous.get("events") or [])
        if isinstance(event, dict)
        and event.get("source") == "ecb"
        and event.get("result_metric_schema") == ECB_SCHEMA
        and event.get("result_status") == "official_release_summary"
    }
    carried = 0
    for event in payload.get("events") or []:
        if not isinstance(event, dict) or event.get("source") != "ecb":
            continue
        prior = old.get(_event_key(event))
        if not prior:
            continue
        for field in RESULT_FIELDS:
            if prior.get(field) not in (None, "", {}):
                event[field] = prior[field]
        carried += 1
    return carried


def find_ecb_release_url(index_page: str, event_date: date) -> str:
    """Return the exact ECB monetary-policy release URL encoded for event_date."""
    stamp = event_date.strftime("%y%m%d")
    try:
        tree = html.fromstring(index_page)
    except Exception:
        return ""
    for href in tree.xpath("//a/@href"):
        raw = str(href or "")
        if re.search(rf"ecb\.mp{stamp}~[A-Za-z0-9]+\.en\.html(?:$|[?#])", raw):
            return urljoin(ECB_INDEX, raw)
    return ""


def parse_ecb_release(page: str) -> tuple[str, dict] | None:
    """Extract the three explicitly named key ECB interest rates."""
    try:
        tree = html.fromstring(page)
    except Exception:
        return None
    paragraphs = [" ".join(node.text_content().split()) for node in tree.xpath("//p")]
    paragraphs = [p for p in paragraphs if p]
    rate_paragraph = next((
        p for p in paragraphs
        if "deposit facility" in p.lower()
        and "main refinancing operations" in p.lower()
        and "marginal lending facility" in p.lower()
    ), "")
    if not rate_paragraph:
        return None
    values = re.findall(r"(?<!\d)(\d+(?:[.,]\d+)?)\s*%", rate_paragraph)
    if len(values) < 3:
        return None
    rates = [float(value.replace(",", ".")) for value in values[-3:]]
    metrics = dict(zip(ECB_METRIC_KEYS, rates))
    summary = (
        f"Taxa de depósito {rates[0]:.2f}% · "
        f"Refinanciamento principal {rates[1]:.2f}% · "
        f"Facilidade marginal {rates[2]:.2f}%"
    )
    return summary, metrics


def enrich_ecb_results(payload: dict, session: requests.Session, today: date | None = None) -> dict:
    today = today or date.today()
    candidates = []
    for event in payload.get("events") or []:
        if not isinstance(event, dict) or event.get("source") != "ecb":
            continue
        try:
            event_date = date.fromisoformat(str(event.get("date") or ""))
        except Exception:
            continue
        if event_date <= today:
            candidates.append((event, event_date))
    if not candidates:
        return {"matched": 0, "fetched_index": 0, "fetched_releases": 0}

    try:
        response = session.get(ECB_INDEX, timeout=TIMEOUT)
        response.raise_for_status()
        index_page = response.text
    except Exception:
        return {"matched": 0, "fetched_index": 1, "fetched_releases": 0}

    matched = 0
    fetched_releases = 0
    for event, event_date in candidates:
        release_url = find_ecb_release_url(index_page, event_date)
        if not release_url:
            continue
        try:
            response = session.get(release_url, timeout=TIMEOUT)
            response.raise_for_status()
            fetched_releases += 1
            parsed = parse_ecb_release(response.text)
        except Exception:
            parsed = None
        if not parsed:
            continue
        event["result_summary"] = parsed[0]
        event["result_status"] = "official_release_summary"
        event["result_released_at"] = event_date.isoformat()
        event["source_url"] = release_url
        event["result_metric_schema"] = ECB_SCHEMA
        event["result_metrics"] = parsed[1]
        matched += 1
    return {"matched": matched, "fetched_index": 1, "fetched_releases": fetched_releases}


def main() -> int:
    payload = _load(OUTPUT)
    if not isinstance(payload.get("events"), list):
        raise RuntimeError("policy decision enrichment: invalid or missing events snapshot")

    normalized = normalize_decision_days(payload)
    previous_path = os.environ.get("VESTRA_MACRO_PREVIOUS", "").strip()
    previous = _load(Path(previous_path)) if previous_path else {}
    if previous:
        normalize_decision_days(previous)
    carried = carry_forward_ecb_results(payload, previous) if previous else 0

    session = requests.Session()
    session.headers.update({"User-Agent": UA, "Accept-Language": "en-US,en;q=0.8"})
    stats = enrich_ecb_results(payload, session)
    payload.setdefault("result_enrichment", {})["ecb"] = {
        "state": "checked",
        "matched": stats["matched"],
        "fetched_index": stats["fetched_index"],
        "fetched_releases": stats["fetched_releases"],
        "carried_forward": carried,
        "decision_day_normalized": normalized,
        "contract": "decision-day only; exact official ECB release; three named policy rates",
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(json.dumps(payload["result_enrichment"]["ecb"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
