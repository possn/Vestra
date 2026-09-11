#!/usr/bin/env python3
"""Fallback CPI/PPI enrichment through the official BLS Public Data API.

The release HTML endpoints can occasionally reject requests from shared CI
networks even when the pages are publicly available. This fallback uses the
machine-oriented BLS API only when the release-page enrichment left a past CPI
or PPI event without verified structured metrics.

It deliberately does not infer consensus or a generic ``actual``. Monthly
changes use seasonally-adjusted BLS series; 12-month changes use the matching
not-seasonally-adjusted series, mirroring the named measures in BLS releases.
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "macro-events.json"
API_URL = "https://api.bls.gov/publicAPI/v2/timeseries/data/"
TIMEOUT = 25

SERIES = {
    "CPI EUA": {
        "headline_sa": "CUSR0000SA0",
        "headline_nsa": "CUUR0000SA0",
        "core_sa": "CUSR0000SA0L1E",
        "core_nsa": "CUUR0000SA0L1E",
        "schema": "bls_cpi_v1",
        "release": "cpi",
    },
    "PPI EUA": {
        "headline_sa": "WPSFD4",
        "headline_nsa": "WPUFD4",
        "core_sa": "WPSFD49116",
        "core_nsa": "WPUFD49116",
        "schema": "bls_ppi_v1",
        "release": "ppi",
    },
}


def _load(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except Exception:
        return {}


def _reference_month(release_date: date) -> tuple[int, int]:
    previous = release_date.replace(day=1) - timedelta(days=1)
    return previous.year, previous.month


def _previous_month(year: int, month: int) -> tuple[int, int]:
    if month == 1:
        return year - 1, 12
    return year, month - 1


def _period_key(year: int, month: int) -> tuple[str, str]:
    return str(year), f"M{month:02d}"


def _series_values(payload: dict) -> dict[str, dict[tuple[str, str], float]]:
    out: dict[str, dict[tuple[str, str], float]] = {}
    results = payload.get("Results") if isinstance(payload, dict) else None
    rows = results.get("series") if isinstance(results, dict) else None
    for series in rows or []:
        if not isinstance(series, dict):
            continue
        series_id = str(series.get("seriesID") or "")
        values: dict[tuple[str, str], float] = {}
        for row in series.get("data") or []:
            if not isinstance(row, dict):
                continue
            year = str(row.get("year") or "")
            period = str(row.get("period") or "")
            if not year or not period.startswith("M") or period == "M13":
                continue
            try:
                values[(year, period)] = float(row.get("value"))
            except Exception:
                continue
        if series_id:
            out[series_id] = values
    return out


def _pct_change(current: float, prior: float) -> float | None:
    if not prior:
        return None
    return round(((current / prior) - 1.0) * 100.0, 1)


def _format_pct(value: float) -> str:
    return f"{value:+.1f}%"


def _summary(short_title: str, year: int, month: int, metrics: dict) -> str:
    month_name = (
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    )[month - 1]
    return (
        f"BLS Public Data API · {month_name} {year}: "
        f"headline {_format_pct(metrics['headline_mom_pct'])} MoM / "
        f"{_format_pct(metrics['headline_yoy_pct'])} YoY; "
        f"core {_format_pct(metrics['core_mom_pct'])} MoM / "
        f"{_format_pct(metrics['core_yoy_pct'])} YoY."
    )


def _release_url(short_title: str, event_date: date, today: date) -> str:
    config = SERIES[short_title]
    if event_date >= today:
        return f"https://www.bls.gov/news.release/{config['release']}.nr0.htm"
    return f"https://www.bls.gov/news.release/archives/{config['release']}_{event_date:%m%d%Y}.htm"


def fetch_metrics(session: requests.Session, short_title: str, event_date: date) -> tuple[dict, str] | None:
    config = SERIES.get(short_title)
    if not config:
        return None
    ref_year, ref_month = _reference_month(event_date)
    prev_year, prev_month = _previous_month(ref_year, ref_month)
    series_ids = [config["headline_sa"], config["headline_nsa"], config["core_sa"], config["core_nsa"]]
    request_payload = {
        "seriesid": series_ids,
        "startyear": str(ref_year - 1),
        "endyear": str(ref_year),
    }
    try:
        response = session.post(API_URL, json=request_payload, timeout=TIMEOUT)
        response.raise_for_status()
        body = response.json()
    except Exception:
        return None
    if str(body.get("status") or "").upper() != "REQUEST_SUCCEEDED":
        return None
    data = _series_values(body)
    ref_key = _period_key(ref_year, ref_month)
    prev_key = _period_key(prev_year, prev_month)
    year_ago_key = _period_key(ref_year - 1, ref_month)
    try:
        headline_mom = _pct_change(data[config["headline_sa"]][ref_key], data[config["headline_sa"]][prev_key])
        headline_yoy = _pct_change(data[config["headline_nsa"]][ref_key], data[config["headline_nsa"]][year_ago_key])
        core_mom = _pct_change(data[config["core_sa"]][ref_key], data[config["core_sa"]][prev_key])
        core_yoy = _pct_change(data[config["core_nsa"]][ref_key], data[config["core_nsa"]][year_ago_key])
    except (KeyError, TypeError):
        return None
    metrics = {
        "headline_mom_pct": headline_mom,
        "headline_yoy_pct": headline_yoy,
        "core_mom_pct": core_mom,
        "core_yoy_pct": core_yoy,
    }
    if any(value is None for value in metrics.values()):
        return None
    return metrics, _summary(short_title, ref_year, ref_month, metrics)


def enrich_api_fallback(payload: dict, session: requests.Session, today: date | None = None) -> dict:
    today = today or date.today()
    matched = 0
    attempted = 0
    for event in payload.get("events") or []:
        if not isinstance(event, dict) or event.get("source") != "bls":
            continue
        short_title = str(event.get("short_title") or "")
        config = SERIES.get(short_title)
        if not config:
            continue
        if event.get("result_status") == "official_release_summary" and event.get("result_metrics"):
            continue
        try:
            event_date = date.fromisoformat(str(event.get("date") or ""))
        except Exception:
            continue
        if event_date > today:
            continue
        attempted += 1
        fetched = fetch_metrics(session, short_title, event_date)
        if not fetched:
            continue
        metrics, summary = fetched
        event["result_status"] = "official_release_summary"
        event["result_summary"] = summary
        event["result_released_at"] = event_date.isoformat()
        event["result_metric_schema"] = config["schema"]
        event["result_metrics"] = metrics
        event["source_url"] = _release_url(short_title, event_date, today)
        event["result_transport"] = "bls_public_api"
        matched += 1
    return {"attempted": attempted, "matched": matched}


def main() -> int:
    payload = _load(OUTPUT)
    if not isinstance(payload.get("events"), list):
        raise RuntimeError("macro API fallback: invalid or missing events snapshot")
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Vestra/1.0 macro-results (+https://github.com/possn/Vestra)",
        "Accept": "application/json",
    })
    stats = enrich_api_fallback(payload, session)
    enrichment = payload.setdefault("result_enrichment", {})
    enrichment["bls_api_fallback"] = {
        "state": "checked",
        **stats,
        "contract": "official BLS API named metrics; no consensus inference and no generic Actual coercion",
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(json.dumps(enrichment["bls_api_fallback"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
