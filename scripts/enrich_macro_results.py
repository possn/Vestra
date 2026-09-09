#!/usr/bin/env python3
"""Attach verified official BLS result summaries and explicit metrics to macro events.

CPI/PPI releases contain several legitimate measures. Vestra therefore keeps the
release summary and, only where the BLS wording is explicit, stores four named
percent changes. It never collapses those measures into a generic ``actual`` and
never infers market consensus.
"""
from __future__ import annotations

import json
import os
import re
from datetime import date
from pathlib import Path

import requests
from lxml import html

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "macro-events.json"
UA = "Vestra/1.0 macro-results (+https://github.com/possn/Vestra)"
TIMEOUT = 20

BLS_RELEASES = {
    "CPI EUA": {
        "url": "https://www.bls.gov/news.release/cpi.nr0.htm",
        "paragraph_prefix": "The Consumer Price Index for All Urban Consumers",
        "metric_schema": "bls_cpi_v1",
    },
    "PPI EUA": {
        "url": "https://www.bls.gov/news.release/ppi.nr0.htm",
        "paragraph_prefix": "The Producer Price Index for final demand",
        "metric_schema": "bls_ppi_v1",
    },
}

_MONTH_NAMES = [
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
]
MONTH_INDEX = {name: index + 1 for index, name in enumerate(_MONTH_NAMES)}
MONTHS_RE = "|".join(name.title() for name in _MONTH_NAMES)
_RELEASE_DATE_RE = re.compile(
    rf"(?:embargoed\s+until|for\s+release).*?\b({MONTHS_RE})\s+(\d{{1,2}}),\s*(\d{{4}})",
    flags=re.I,
)

RESULT_FIELDS = (
    "result_summary", "result_status", "result_released_at", "source_url",
    "result_metric_schema", "result_metrics",
)

_UP_VERBS = r"increased|rose|advanced|moved up|edged up|inched up"
_DOWN_VERBS = r"decreased|fell|declined|dropped|moved down|edged down"


def _event_key(event: dict) -> tuple:
    return (
        str(event.get("date") or ""),
        str(event.get("date_end") or ""),
        str(event.get("short_title") or ""),
        str(event.get("source") or ""),
    )


def _normalise(value: str) -> str:
    return " ".join(str(value or "").split()).strip()


def _change_for_subject(text: str, subject: str) -> float | None:
    """Parse the first explicit change immediately following an exact subject."""
    segment = _normalise(text)
    match = re.search(
        rf"{subject}\s+(?:(was|were)\s+)?(unchanged|{_UP_VERBS}|{_DOWN_VERBS})(?:\s+([0-9]+(?:\.[0-9]+)?)\s*(?:-|\s)percent)?",
        segment,
        flags=re.I,
    )
    if not match:
        return None
    verb = match.group(2).lower()
    if verb == "unchanged":
        return 0.0
    if match.group(3) is None:
        return None
    value = float(match.group(3))
    return -value if re.fullmatch(_DOWN_VERBS, verb, flags=re.I) else value


def _paragraph_starting(paragraphs: list[str], prefix: str) -> str:
    key = prefix.lower()
    return next((value for value in paragraphs if value.lower().startswith(key)), "")


def _extract_cpi_metrics(paragraphs: list[str]) -> dict:
    headline = _paragraph_starting(paragraphs, "The Consumer Price Index for All Urban Consumers")
    core_month = _paragraph_starting(paragraphs, "The index for all items less food and energy")
    text = " ".join(paragraphs)
    metrics = {
        "headline_mom_pct": _change_for_subject(
            headline, r"The Consumer Price Index for All Urban Consumers \(CPI-U\)"
        ),
        "headline_yoy_pct": _change_for_subject(text, r"\bthe all items index"),
        "core_mom_pct": _change_for_subject(core_month, r"The index for all items less food and energy"),
        "core_yoy_pct": _change_for_subject(text, r"\bThe all items less food and energy index"),
    }
    return {key: value for key, value in metrics.items() if value is not None}


def _extract_ppi_metrics(paragraphs: list[str]) -> dict:
    headline = _paragraph_starting(paragraphs, "The Producer Price Index for final demand")
    core_month = _paragraph_starting(paragraphs, "Prices for final demand less foods, energy, and trade services")
    text = " ".join(paragraphs)
    metrics = {
        "headline_mom_pct": _change_for_subject(headline, r"The Producer Price Index for final demand"),
        "headline_yoy_pct": _change_for_subject(text, r"\bthe index for final demand"),
        "core_mom_pct": _change_for_subject(core_month, r"Prices for final demand less foods, energy, and trade services"),
        "core_yoy_pct": _change_for_subject(text, r"\bthe index for final demand less foods, energy, and trade services"),
    }
    return {key: value for key, value in metrics.items() if value is not None}


def parse_bls_release(page: str, short_title: str) -> tuple[date, str, dict] | None:
    """Return exact release date, compact official summary and explicit metrics."""
    config = BLS_RELEASES.get(short_title)
    if not config or not page:
        return None
    try:
        tree = html.fromstring(page)
    except Exception:
        return None

    page_text = _normalise(tree.text_content())
    date_match = _RELEASE_DATE_RE.search(page_text[:5000])
    if not date_match:
        return None
    try:
        released = date(
            int(date_match.group(3)),
            MONTH_INDEX[date_match.group(1).lower()],
            int(date_match.group(2)),
        )
    except Exception:
        return None

    paragraphs = [_normalise(node.text_content()) for node in tree.xpath("//p")]
    paragraphs = [value for value in paragraphs if value]
    summary = _paragraph_starting(paragraphs, config["paragraph_prefix"])
    if not summary:
        return None

    metrics = _extract_cpi_metrics(paragraphs) if short_title == "CPI EUA" else _extract_ppi_metrics(paragraphs)
    return released, summary[:900], metrics


def _load(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def carry_forward_verified_results(payload: dict, previous: dict) -> int:
    """Keep previously verified results only for the exact same event identity."""
    old = {
        _event_key(event): event
        for event in (previous.get("events") or [])
        if isinstance(event, dict) and event.get("result_status") == "official_release_summary"
    }
    carried = 0
    for event in payload.get("events") or []:
        prior = old.get(_event_key(event))
        if not prior:
            continue
        for field in RESULT_FIELDS:
            if prior.get(field) not in (None, "", {}):
                event[field] = prior[field]
        carried += 1
    return carried


def enrich_bls_results(payload: dict, session: requests.Session, today: date | None = None) -> dict:
    today = today or date.today()
    fetched: dict[str, tuple[date, str, dict] | None] = {}
    matched = 0
    structured = 0
    for event in payload.get("events") or []:
        if not isinstance(event, dict) or event.get("source") != "bls":
            continue
        short_title = str(event.get("short_title") or "")
        config = BLS_RELEASES.get(short_title)
        if not config:
            continue
        try:
            event_date = date.fromisoformat(str(event.get("date") or ""))
        except Exception:
            continue
        if event_date > today:
            continue
        if short_title not in fetched:
            try:
                response = session.get(config["url"], timeout=TIMEOUT)
                response.raise_for_status()
                fetched[short_title] = parse_bls_release(response.text, short_title)
            except Exception:
                fetched[short_title] = None
        parsed = fetched[short_title]
        if not parsed or parsed[0] != event_date:
            continue
        event["result_summary"] = parsed[1]
        event["result_status"] = "official_release_summary"
        event["result_released_at"] = event_date.isoformat()
        event["source_url"] = config["url"]
        if parsed[2]:
            event["result_metric_schema"] = config["metric_schema"]
            event["result_metrics"] = parsed[2]
            structured += 1
        matched += 1
    return {"matched": matched, "structured": structured, "fetched": len(fetched)}


def main() -> int:
    payload = _load(OUTPUT)
    if not isinstance(payload.get("events"), list):
        raise RuntimeError("macro result enrichment: invalid or missing events snapshot")

    previous_path = os.environ.get("VESTRA_MACRO_PREVIOUS", "").strip()
    previous = _load(Path(previous_path)) if previous_path else {}
    carried = carry_forward_verified_results(payload, previous) if previous else 0

    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept-Language": "en-US,en;q=0.8"})
    stats = enrich_bls_results(payload, s)
    payload["result_enrichment"] = {
        "bls": {
            "state": "checked",
            "matched": stats["matched"],
            "structured": stats["structured"],
            "fetched_release_pages": stats["fetched"],
            "carried_forward": carried,
            "contract": "official named metrics only; no consensus inference and no generic Actual coercion",
        }
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(json.dumps(payload["result_enrichment"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
