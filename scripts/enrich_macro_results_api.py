#!/usr/bin/env python3
"""Fallback CPI/PPI enrichment through the official BLS Public Data API.

The release HTML endpoints can reject requests from shared CI networks. This
fallback uses the machine-oriented BLS API only when release-page enrichment
left a past CPI/PPI event without verified structured metrics.

It deliberately does not infer consensus or a generic ``actual``. Monthly
changes use seasonally-adjusted BLS series; 12-month changes use the matching
not-seasonally-adjusted series, mirroring the named measures in BLS releases.
"""
from __future__ import annotations

import json
import os
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
    return (year - 1, 12) if month == 1 else (year, month - 1)


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


def _payload_status(body: object) -> tuple[bool, str]:
    if not isinstance(body, dict):
        return False, "non_json_object"
    status = str(body.get("status") or "").upper()
    message = body.get("message")
    if isinstance(message, list):
        message = "; ".join(str(item) for item in message if item)
    message = str(message or "").strip()
    if status != "REQUEST_SUCCEEDED":
        return False, f"api_status={status or 'missing'}{': ' + message[:180] if message else ''}"
    return True, "ok"


def _post_series(session: requests.Session, series_ids: list[str], start_year: int, end_year: int) -> tuple[dict, str]:
    payload = {"seriesid": series_ids, "startyear": str(start_year), "endyear": str(end_year)}
    try:
        response = session.post(API_URL, json=payload, timeout=TIMEOUT)
        status_code = int(getattr(response, "status_code", 0) or 0)
        response.raise_for_status()
        body = response.json()
    except Exception as exc:
        return {}, f"post_http={getattr(locals().get('response', None), 'status_code', 'error')}:{type(exc).__name__}"
    ok, reason = _payload_status(body)
    if not ok:
        return {}, f"post_{reason}"
    data = _series_values(body)
    if not data:
        return {}, f"post_http={status_code}:empty_series"
    return data, f"post_http={status_code}:ok"


def _get_one_series(session: requests.Session, series_id: str, start_year: int, end_year: int) -> tuple[dict, str]:
    url = f"{API_URL}{series_id}"
    params = {"startyear": str(start_year), "endyear": str(end_year)}
    try:
        response = session.get(url, params=params, timeout=TIMEOUT)
        status_code = int(getattr(response, "status_code", 0) or 0)
        response.raise_for_status()
        body = response.json()
    except Exception as exc:
        return {}, f"get_{series_id}_http={getattr(locals().get('response', None), 'status_code', 'error')}:{type(exc).__name__}"
    ok, reason = _payload_status(body)
    if not ok:
        return {}, f"get_{series_id}_{reason}"
    data = _series_values(body)
    if series_id not in data:
        return {}, f"get_{series_id}_http={status_code}:missing_series"
    return {series_id: data[series_id]}, f"get_{series_id}_http={status_code}:ok"


def _get_series_fallback(session: requests.Session, series_ids: list[str], start_year: int, end_year: int) -> tuple[dict, list[str]]:
    combined: dict[str, dict[tuple[str, str], float]] = {}
    diagnostics: list[str] = []
    for series_id in series_ids:
        data, diagnostic = _get_one_series(session, series_id, start_year, end_year)
        diagnostics.append(diagnostic)
        combined.update(data)
    return combined, diagnostics


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


def fetch_metrics(session: requests.Session, short_title: str, event_date: date) -> tuple[dict, str, str, list[str]] | None:
    config = SERIES.get(short_title)
    if not config:
        return None
    ref_year, ref_month = _reference_month(event_date)
    prev_year, prev_month = _previous_month(ref_year, ref_month)
    series_ids = [config["headline_sa"], config["headline_nsa"], config["core_sa"], config["core_nsa"]]
    start_year, end_year = ref_year - 1, ref_year

    data, post_diag = _post_series(session, series_ids, start_year, end_year)
    diagnostics = [post_diag]
    transport = "post"

    # Some shared CI networks receive an empty/error multi-series POST while the
    # documented single-series GET endpoint remains available. Try each official
    # series independently before failing closed.
    if set(series_ids) - set(data):
        get_data, get_diags = _get_series_fallback(session, series_ids, start_year, end_year)
        diagnostics.extend(get_diags)
        if len(get_data) >= len(data):
            data = get_data
            transport = "get"

    ref_key = _period_key(ref_year, ref_month)
    prev_key = _period_key(prev_year, prev_month)
    year_ago_key = _period_key(ref_year - 1, ref_month)
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
                missing.append(f"{series_id}:{key[0]}-{key[1]}")
    if missing:
        diagnostics.append("missing=" + ",".join(missing))
        return None

    headline_mom = _pct_change(data[config["headline_sa"]][ref_key], data[config["headline_sa"]][prev_key])
    headline_yoy = _pct_change(data[config["headline_nsa"]][ref_key], data[config["headline_nsa"]][year_ago_key])
    core_mom = _pct_change(data[config["core_sa"]][ref_key], data[config["core_sa"]][prev_key])
    core_yoy = _pct_change(data[config["core_nsa"]][ref_key], data[config["core_nsa"]][year_ago_key])
    metrics = {
        "headline_mom_pct": headline_mom,
        "headline_yoy_pct": headline_yoy,
        "core_mom_pct": core_mom,
        "core_yoy_pct": core_yoy,
    }
    if any(value is None for value in metrics.values()):
        diagnostics.append("invalid_pct_change")
        return None
    return metrics, _summary(short_title, ref_year, ref_month, metrics), transport, diagnostics


def enrich_api_fallback(payload: dict, session: requests.Session, today: date | None = None) -> dict:
    today = today or date.today()
    matched = attempted = 0
    transports = {"post": 0, "get": 0}
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
            # Run a diagnostic-only fetch path so CI logs reveal whether the
            # endpoint, series, or target month is missing without dumping data.
            config_ids = [config["headline_sa"], config["headline_nsa"], config["core_sa"], config["core_nsa"]]
            ref_year, _ = _reference_month(event_date)
            data, post_diag = _post_series(session, config_ids, ref_year - 1, ref_year)
            diag = [post_diag]
            if set(config_ids) - set(data):
                _, get_diags = _get_series_fallback(session, config_ids, ref_year - 1, ref_year)
                diag.extend(get_diags)
            failures.append(f"{short_title}@{event_date.isoformat()}:" + "|".join(diag))
            continue
        metrics, summary, transport, diagnostics = fetched
        transports[transport] = transports.get(transport, 0) + 1
        event["result_status"] = "official_release_summary"
        event["result_summary"] = summary
        event["result_released_at"] = event_date.isoformat()
        event["result_metric_schema"] = config["schema"]
        event["result_metrics"] = metrics
        event["source_url"] = _release_url(short_title, event_date, today)
        event["result_transport"] = f"bls_public_api_{transport}"
        event["result_transport_diagnostic"] = diagnostics[0] if diagnostics else "ok"
        matched += 1
    return {"attempted": attempted, "matched": matched, "transports": transports, "failures": failures[:6]}


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
    if os.environ.get("VESTRA_REQUIRE_BLS_API_MATCH") == "1" and stats["attempted"] and not stats["matched"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
