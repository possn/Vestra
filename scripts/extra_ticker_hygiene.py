"""Audit historical extra tickers without mutating portfolio identity.

The explicit portfolio extension may contain current symbols, historical symbols
with source-backed successors, broker identities, or stale/import artefacts. This
diagnostic classifies only exact evidence. Similar-looking symbols are reported
as review families, never auto-merged, deleted or rewritten.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

try:
    from known_asset_identity import exact_identity_override
    from ticker_successors import successor_for
except (ImportError, ModuleNotFoundError):
    from scripts.known_asset_identity import exact_identity_override
    from scripts.ticker_successors import successor_for

ROOT = Path(__file__).resolve().parents[1]
EXTRA_PATH = ROOT / "data" / "extra_tickers.json"
STOCKS_PATH = ROOT / "data" / "stocks.json"
SEC_TICKER_MAP_PATH = ROOT / "data" / "sec_ticker_map.json"
OUT_PATH = ROOT / "data" / "extra_ticker_hygiene.json"


def _load_json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return {}


def extra_tickers(payload):
    values = payload.get("tickers", payload) if isinstance(payload, dict) else payload
    if not isinstance(values, list):
        return []
    return sorted({str(x or "").strip().upper() for x in values if str(x or "").strip()})


def stock_index(payload):
    rows = payload.get("stocks") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        return {}
    out = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        ticker = str(row.get("ticker") or "").strip().upper()
        if ticker:
            out[ticker] = row
    return out


def sec_identity_index(payload):
    """Return exact SEC ticker->CIK identity evidence without inferring asset type.

    The validated SEC snapshot proves that a ticker is a registered current
    identity in that source. It does *not* prove EQUITY versus fund/security type,
    so hygiene keeps quote_type null unless a stronger source provides it.
    """
    values = payload.get("map") if isinstance(payload, dict) else None
    if not isinstance(values, dict):
        return {}
    out = {}
    for ticker, cik in values.items():
        key = str(ticker or "").strip().upper()
        try:
            cik_value = int(cik)
        except (TypeError, ValueError):
            continue
        if key and cik_value > 0:
            out[key] = cik_value
    return out


def classify(ticker, published_row=None, sec_cik=None):
    ticker = str(ticker or "").strip().upper()
    published_row = published_row if isinstance(published_row, dict) else {}
    reported_type = str(published_row.get("quote_type") or "").strip().upper()
    successor = successor_for(ticker)
    override = exact_identity_override(ticker)

    if reported_type:
        return {
            "state": "published_confirmed",
            "quote_type": reported_type,
            "evidence": "stocks_snapshot",
        }
    if isinstance(successor, dict):
        return {
            "state": "corporate_successor",
            "quote_type": str(successor.get("quote_type") or "").strip().upper() or None,
            "evidence": "ticker_successor",
            "retrieval_ticker": successor.get("successor"),
            "effective_date": successor.get("effective_date"),
        }
    if isinstance(override, dict):
        return {
            "state": "known_identity",
            "quote_type": str(override.get("quote_type") or "").strip().upper() or None,
            "evidence": "known_asset_identity",
            "isin": override.get("isin"),
        }
    try:
        cik_value = int(sec_cik) if sec_cik is not None else None
    except (TypeError, ValueError):
        cik_value = None
    if cik_value is not None and cik_value > 0:
        return {
            "state": "sec_registered_identity",
            "quote_type": None,
            "evidence": "sec_ticker_map",
            "cik": cik_value,
        }
    return {
        "state": "unresolved",
        "quote_type": None,
        "evidence": None,
    }


def review_family_key(ticker):
    """Return a conservative review-only family key for obvious prefix variants.

    This is not identity evidence. It exists only to group unresolved historical
    symbols for human review, e.g. BRADE/BRADES or VICO/VICOR. Families are never
    used to mutate or infer ticker identity.
    """
    ticker = str(ticker or "").strip().upper()
    if len(ticker) < 4 or "." in ticker or "-" in ticker:
        return None
    return ticker[:4]


def build_audit(extra_payload, stocks_payload, sec_payload=None):
    tickers = extra_tickers(extra_payload)
    stocks = stock_index(stocks_payload)
    sec_identities = sec_identity_index(sec_payload or {})
    rows = []
    unresolved_by_family = defaultdict(list)

    for ticker in tickers:
        result = {
            "ticker": ticker,
            **classify(ticker, stocks.get(ticker), sec_identities.get(ticker)),
        }
        if result["state"] == "unresolved":
            key = review_family_key(ticker)
            if key:
                unresolved_by_family[key].append(ticker)
        rows.append(result)

    review_families = [
        {"family_key": key, "tickers": sorted(values), "action": "review_only"}
        for key, values in sorted(unresolved_by_family.items())
        if len(set(values)) >= 2
    ]
    counts = Counter(row["state"] for row in rows)
    unresolved = [row["ticker"] for row in rows if row["state"] == "unresolved"]
    return {
        "schema_version": 2,
        "extra_ticker_count": len(tickers),
        "states": dict(counts.most_common()),
        "unresolved_count": len(unresolved),
        "unresolved_tickers": unresolved,
        "review_families": review_families,
        "rows": rows,
        "mutation_policy": "diagnostic_only_exact_evidence_no_auto_merge_no_delete",
        "identity_note": (
            "sec_registered_identity proves exact ticker registration in the validated SEC "
            "ticker map only; quote_type remains unresolved unless stronger evidence supplies it"
        ),
    }


def main():
    audit = build_audit(
        _load_json(EXTRA_PATH),
        _load_json(STOCKS_PATH),
        _load_json(SEC_TICKER_MAP_PATH),
    )
    OUT_PATH.write_text(json.dumps(audit, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Extra ticker hygiene: {audit['extra_ticker_count']} tickers, {audit['unresolved_count']} unresolved -> {OUT_PATH}")


if __name__ == "__main__":
    main()
