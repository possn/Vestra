#!/usr/bin/env python3
"""Attach compact official result summaries to matching Vestra macro events.

This is deliberately separate from the schedule refresher. It never invents an
"actual" value: CPI/PPI releases contain several legitimate measures (MoM, YoY,
headline/core), so the first safe contract is an official summary plus the exact
release URL. A result is attached only when the release date parsed from the BLS
page exactly matches the Vestra event date.
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
    },
    "PPI EUA": {
        "url": "https://www.bls.gov/news.release/ppi.nr0.htm",
        "paragraph_prefix": "The Producer Price Index for final demand",
    },
}

MONTHS = (
    "January|February|March|April|May|June|July|August|September|October|November|December"
)
_RELEASE_DATE_RE = re.compile(
    rf"(?:embargoed\s+until|for\s+release).*?\b({MONTHS})\s+(\d{{1,2}}),\s*(\d{{4}})",
    flags=re.I,
)

RESULT_FIELDS = ("result_summary", "result_status", "result_released_at", "source_url")


def _event_key(event: dict) -> tuple:
    return (
        str(event.get("date") or ""),
        str(event.get("date_end") or ""),
        str(event.get("short_title") or ""),
        str(event.get("source") or ""),
    )


def _normalise(value: str) -> str:
    return " ".join(str(value or "").split()).strip()


def parse_bls_release(page: str, short_title: str) -> tuple[date, str] | None:
    """Return (official release date, compact first result paragraph), or None."""
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
        released = date.fromisoformat(
            f"{int(date_match.group(3)):04d}-{date.fromisoformat('2000-01-01').replace(month=[
                'january','february','march','april','may','june','july','august','september','october','november','december'
            ].index(date_match.group(1).lower()) + 1).month:02d}-{int(date_match.group(2)):02d}"
        )
    except Exception:
        return None

    prefix = config["paragraph_prefix"].lower()
    summary = ""
    for node in tree.xpath("//p"):
        paragraph = _normalise(node.text_content())
        if paragraph.lower().startswith(prefix):
            summary = paragraph
            break
    if not summary:
        return None
    # Enough context for the headline result without turning the snapshot into a
    # copy of the release. The exact publication remains available via source_url.
    return released, summary[:900]


def _load(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def carry_forward_verified_results(payload: dict, previous: dict) -> int:
    """Keep previously verified summaries only for the exact same event identity."""
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
            if prior.get(field) not in (None, ""):
                event[field] = prior[field]
        carried += 1
    return carried


def enrich_bls_results(payload: dict, session: requests.Session, today: date | None = None) -> dict:
    today = today or date.today()
    fetched: dict[str, tuple[date, str] | None] = {}
    matched = 0
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
        matched += 1
    return {"matched": matched, "fetched": len(fetched)}


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
            "fetched_release_pages": stats["fetched"],
            "carried_forward": carried,
            "contract": "official summary only; no ambiguous Actual/Consensus/Previous inference",
        }
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(json.dumps(payload["result_enrichment"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
