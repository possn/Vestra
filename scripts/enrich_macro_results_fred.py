#!/usr/bin/env python3
"""Attach CPI/PPI metrics from FRED's mirror of official BLS series.

BLS release pages and api.bls.gov can reject GitHub-hosted runners. Vestra
already uses the Federal Reserve Bank of St. Louis (FRED) as the resilient
transport for the BLS release calendar. This module applies the same pattern to
CPI/PPI result data: the underlying series remain U.S. Bureau of Labor
Statistics series, mirrored by FRED.

No market consensus is inferred and no generic ``actual`` is created. Monthly
changes use seasonally-adjusted series; 12-month changes use the corresponding
not-seasonally-adjusted series. A result is published only when all four named
headline/core metrics can be calculated for the exact reference month.
"""
from __future__ import annotations

import csv
import io
import json
import os
from datetime import date, timedelta
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "macro-events.json"
FRED_CSV_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv"
TIMEOUT = 15

SERIES = {
    "CPI EUA": {
        "headline_sa": "CPIAUCSL",
        "headline_nsa": "CPIAUCNS",
        "core_sa": "CPILFESL",
        "core_nsa": "CPILFENS",
        "schema": "bls_cpi_v1",
        "release": "cpi",
    },
    "PPI EUA": {
        "headline_sa": "PPIFIS",
        "headline_nsa": "PPIFID",
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
    return (year - 1, 12) if month == 1 else (year, month - 1)


def _month_date(year: int, month: int) -> str:
    return f"{year:04d}-{month:02d}-01"


def _pct_change(current: float, prior: float) -> float | None:
    if not prior:
        return None
    return round(((current / prior) - 1.0) * 100.0, 1)


def _format_pct(value: float) -> str:
    return f"{value:+.1f}%"


def _summary(year: int, month: int, metrics: dict) -> str:
    month_name = (
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December",
    )[month - 1]
    return (
        f"U.S. BLS data via FRED · {month_name} {year}: "
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


def _fetch_series(session: requests.Session, series_id: str, start_date: str, end_date: str) -> tuple[dict[str, float], str]:
    params = {"id": series_id, "cosd": start_date, "coed": end_date}
    try:
        response = session.get(FRED_CSV_URL, params=params, timeout=TIMEOUT)
        status = int(getattr(response, "status_code", 0) or 0)
        response.raise_for_status()
        text = response.text
    except Exception as exc:
        return {}, f"{series_id}:http={getattr(locals().get('response', None), 'status_code', 'error')}:{type(exc).__name__}"

    values: dict[str, float] = {}
    try:
        reader = csv.DictReader(io.StringIO(text))
        value_column = next((name for name in (reader.fieldnames or []) if name and name != "observation_date"), "")
        for row in reader:
            obs_date = str(row.get("observation_date") or "").strip()
            raw = str(row.get(value_column) or "").strip()
            if not obs_date or not raw or raw == ".":
                continue
            values[obs_date] = float(raw)
    except Exception as exc:
        return {}, f"{series_id}:http={status}:parse={type(exc).__name__}"
    if not values:
        return {}, f"{series_id}:http={status}:empty"
    return values, f"{series_id}:http={status}:ok"


def fetch_metrics(session: requests.Session, short_title: str, event_date: date) -> tuple[dict, str, list[str]] | None:
    config = SERIES.get(short_title)
    if not config:
        return None
    ref_year, ref_month = _reference_month(event_date)
    prev_year, prev_month = _previous_month(ref_year, ref_month)
    start_date = _month_date(ref_year - 1, ref_month)
    end_date = _month_date(ref_year, ref_month)
    series_ids = [config["headline_sa"], config["headline_nsa"], config["core_sa"], config["core_nsa"]]
    data: dict[str, dict[str, float]] = {}
    diagnostics: list[str] = []
    for series_id in series_ids:
        values, diagnostic = _fetch_series(session, series_id, start_date, end_date)
        diagnostics.append(diagnostic)
        if values:
            data[series_id] = values

    ref_key = _month_date(ref_year, ref_month)
    prev_key = _month_date(prev_year, prev_month)
    year_ago_key = _month_date(ref_year - 1, ref_month)
    required = {
        config["headline_sa"]: (ref_key, prev_key),
        config["headline_nsa"]: (ref_key, year_ago_key),
        config["core_sa"]: (ref_key, prev_key),
        config["core_nsa"]: (ref_key, year_ago_key),
    }
    missing = []
    for series_id, keys in required.items():
        values = data.get(series_id, {})
        for key in keys:
            if key not in values:
                missing.append(f"{series_id}:{key}")
    if missing:
        diagnostics.append("missing=" + ",".join(missing))
        return None

    metrics = {
        "headline_mom_pct": _pct_change(data[config["headline_sa"]][ref_key], data[config["headline_sa"]][prev_key]),
        "headline_yoy_pct": _pct_change(data[config["headline_nsa"]][ref_key], data[config["headline_nsa"]][year_ago_key]),
        "core_mom_pct": _pct_change(data[config["core_sa"]][ref_key], data[config["core_sa"]][prev_key]),
        "core_yoy_pct": _pct_change(data[config["core_nsa"]][ref_key], data[config["core_nsa"]][year_ago_key]),
    }
    if any(value is None for value in metrics.values()):
        return None
    return metrics, _summary(ref_year, ref_month, metrics), diagnostics


def enrich_fred_fallback(payload: dict, session: requests.Session, today: date | None = None) -> dict:
    today = today or date.today()
    attempted = matched = 0
    failures: list[str] = []
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
            failures.append(f"{short_title}@{event_date.isoformat()}:missing_or_unreachable")
            continue
        metrics, summary, diagnostics = fetched
        event["result_status"] = "official_release_summary"
        event["result_summary"] = summary
        event["result_released_at"] = event_date.isoformat()
        event["result_metric_schema"] = config["schema"]
        event["result_metrics"] = metrics
        event["source_url"] = _release_url(short_title, event_date, today)
        event["result_transport"] = "fred_bls_mirror"
        event["result_transport_diagnostic"] = ";".join(diagnostics)
        matched += 1
    return {"attempted": attempted, "matched": matched, "failures": failures[:6]}


def main() -> int:
    payload = _load(OUTPUT)
    if not isinstance(payload.get("events"), list):
        raise RuntimeError("macro FRED fallback: invalid or missing events snapshot")
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Vestra/1.0 macro-results (+https://github.com/possn/Vestra)",
        "Accept": "text/csv,text/plain;q=0.9,*/*;q=0.8",
    })
    stats = enrich_fred_fallback(payload, session)
    enrichment = payload.setdefault("result_enrichment", {})
    enrichment["fred_bls_results"] = {
        "state": "checked",
        **stats,
        "contract": "BLS source series mirrored by Federal Reserve Bank of St. Louis; named metrics only; no consensus inference and no generic Actual coercion",
    }
    OUTPUT.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n", encoding="utf-8")
    print(json.dumps(enrichment["fred_bls_results"], ensure_ascii=False))
    if os.environ.get("VESTRA_REQUIRE_FRED_BLS_MATCH") == "1" and stats["attempted"] and not stats["matched"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
