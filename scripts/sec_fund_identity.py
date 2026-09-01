"""Official SEC fund/mutual-fund ticker identity diagnostics.

The SEC publishes ``company_tickers_mf.json`` specifically for registered
funds. Vestra uses this feed only as identity evidence: it does not infer ETF vs
mutual-fund structure and it never overwrites an explicit quote type.

A validated snapshot is persisted so the audit remains usable during transient
SEC/network failures. The output is diagnostic only and does not mutate
``stocks.json`` or any score.
"""
from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
STOCKS_PATH = ROOT / "data" / "stocks.json"
SNAPSHOT_PATH = ROOT / "data" / "sec_fund_ticker_map.json"
AUDIT_PATH = ROOT / "data" / "sec_fund_identity_audit.json"
SEC_FUND_TICKERS = "https://www.sec.gov/files/company_tickers_mf.json"
SCHEMA_VERSION = 1


def _normal_ticker(value):
    ticker = str(value or "").strip().upper()
    if not ticker or len(ticker) > 20:
        return None
    allowed = set("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.-")
    return ticker if all(ch in allowed for ch in ticker) else None


def _normal_cik(value):
    try:
        cik = int(value)
    except (TypeError, ValueError):
        return None
    return cik if 0 < cik < 10_000_000_000 else None


def parse_sec_fund_payload(payload):
    """Parse the official SEC fields/data schema fail-closed."""
    if not isinstance(payload, dict):
        return {}
    fields = payload.get("fields")
    rows = payload.get("data")
    if not isinstance(fields, list) or not isinstance(rows, list):
        return {}
    positions = {str(name).strip().lower(): i for i, name in enumerate(fields)}
    symbol_i = positions.get("symbol")
    cik_i = positions.get("cik")
    series_i = positions.get("seriesid")
    class_i = positions.get("classid")
    if symbol_i is None or cik_i is None:
        return {}

    out = {}
    for row in rows:
        if not isinstance(row, (list, tuple)):
            continue
        if symbol_i >= len(row) or cik_i >= len(row):
            continue
        ticker = _normal_ticker(row[symbol_i])
        cik = _normal_cik(row[cik_i])
        if not ticker or cik is None:
            continue
        item = {"cik": cik}
        if series_i is not None and series_i < len(row) and row[series_i]:
            item["series_id"] = str(row[series_i]).strip()
        if class_i is not None and class_i < len(row) and row[class_i]:
            item["class_id"] = str(row[class_i]).strip()
        out[ticker] = item
    return out


def _valid_map(mapping, min_count=1):
    if not isinstance(mapping, dict) or len(mapping) < min_count:
        return None
    out = {}
    for ticker, item in mapping.items():
        tk = _normal_ticker(ticker)
        if not tk or not isinstance(item, dict):
            return None
        cik = _normal_cik(item.get("cik"))
        if cik is None:
            return None
        clean = {"cik": cik}
        if item.get("series_id"):
            clean["series_id"] = str(item["series_id"])
        if item.get("class_id"):
            clean["class_id"] = str(item["class_id"])
        out[tk] = clean
    return out


def read_snapshot(path=SNAPSHOT_PATH):
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        if payload.get("schema_version") != SCHEMA_VERSION:
            return None
        mapping = _valid_map(payload.get("map"), min_count=1)
        if not mapping or int(payload.get("count") or 0) != len(mapping):
            return None
        return mapping, payload
    except Exception:
        return None


def write_snapshot(mapping, source=SEC_FUND_TICKERS, path=SNAPSHOT_PATH):
    mapping = _valid_map(mapping, min_count=1)
    if not mapping:
        raise ValueError("invalid SEC fund ticker map")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source": source,
        "count": len(mapping),
        "map": dict(sorted(mapping.items())),
    }
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)
    return payload


def fetch_remote(timeout=30):
    ua = os.getenv("SEC_USER_AGENT", "Vestra/4.0 (+https://github.com/possn/Vestra)")
    request = Request(
        SEC_FUND_TICKERS,
        headers={"User-Agent": ua, "Accept": "application/json", "Accept-Encoding": "gzip, deflate"},
    )
    with urlopen(request, timeout=timeout) as response:
        payload = json.load(response)
    mapping = _valid_map(parse_sec_fund_payload(payload), min_count=1000)
    if not mapping:
        raise ValueError("SEC fund ticker payload did not pass validation")
    return mapping


def refresh_snapshot():
    try:
        mapping = fetch_remote()
        write_snapshot(mapping)
        return mapping, "remote"
    except Exception as exc:
        cached = read_snapshot()
        if cached:
            return cached[0], f"snapshot_fallback: {exc}"
        return {}, f"unavailable: {exc}"


def build_audit(mapping, source_state, stocks_path=STOCKS_PATH):
    try:
        payload = json.loads(Path(stocks_path).read_text(encoding="utf-8"))
        rows = [r for r in payload.get("stocks", []) if isinstance(r, dict)]
    except Exception as exc:
        rows = []
        source_state = f"{source_state}; stocks_unavailable: {exc}"

    unresolved_matches = []
    explicit_equity_conflicts = []
    explicit_non_equity_matches = []
    all_matches = 0
    for row in rows:
        ticker = _normal_ticker(row.get("ticker"))
        if not ticker or ticker not in mapping:
            continue
        all_matches += 1
        quote_type = str(row.get("quote_type") or "").strip().upper()
        item = {
            "ticker": ticker,
            "name": row.get("name"),
            "region": row.get("region"),
            "reported_quote_type": quote_type or None,
            "coverage_pct": row.get("data_coverage_pct"),
            "pipeline_status": row.get("pipeline_status"),
            "sec_fund_identity": mapping[ticker],
        }
        if not quote_type:
            unresolved_matches.append(item)
        elif quote_type in {"ETF", "FUND", "MUTUALFUND"}:
            explicit_non_equity_matches.append(item)
        else:
            explicit_equity_conflicts.append(item)

    audit = {
        "schema_version": 1,
        "generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "source": SEC_FUND_TICKERS,
        "source_state": source_state,
        "sec_fund_ticker_count": len(mapping),
        "market_rows_checked": len(rows),
        "market_rows_matching_sec_fund_map": all_matches,
        "unresolved_rows_confirmed_as_registered_funds": len(unresolved_matches),
        "explicit_non_equity_rows_confirmed": len(explicit_non_equity_matches),
        "explicit_equity_type_conflicts": len(explicit_equity_conflicts),
        "unresolved_examples": unresolved_matches[:200],
        "type_conflict_examples": explicit_equity_conflicts[:100],
    }
    AUDIT_PATH.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        "SEC fund identity audit: "
        f"{len(mapping)} fund tickers; {len(unresolved_matches)} unresolved matches; "
        f"{len(explicit_equity_conflicts)} explicit type conflicts"
    )
    return audit


def main():
    mapping, state = refresh_snapshot()
    build_audit(mapping, state)


if __name__ == "__main__":
    main()
