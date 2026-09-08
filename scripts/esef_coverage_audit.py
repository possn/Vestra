"""Build a deterministic coverage funnel for European ESEF identity/enrichment.

Reads the currently published ``data/stocks.json`` and summarizes, per supported
European Yahoo suffix, how many equity rows carry ISIN, LEI and ESEF enrichment.
The audit is intentionally offline: it never calls Yahoo, GLEIF, Euronext, LSE or
filings.xbrl.org, so it is safe to run on every market build and useful for
comparing coverage before/after identity-source changes.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "data" / "stocks.json"
DEFAULT_OUTPUT = ROOT / "data" / "esef_coverage_audit.json"

COUNTRY = {
    ".L": "GB", ".PA": "FR", ".AS": "NL", ".BR": "BE", ".MC": "ES",
    ".MI": "IT", ".ST": "SE", ".HE": "FI", ".CO": "DK", ".OL": "NO",
    ".LS": "PT", ".VI": "AT", ".WA": "PL", ".PR": "CZ", ".AT": "GR",
    ".SW": "CH", ".DE": "DE",
}

EQUITY_TYPES = {"EQUITY", "STOCK", "COMMON_STOCK", "COMMON STOCK"}


def _rows(payload) -> list[dict]:
    if isinstance(payload, list):
        return [x for x in payload if isinstance(x, dict)]
    if isinstance(payload, dict):
        for key in ("stocks", "rows", "data", "items"):
            value = payload.get(key)
            if isinstance(value, list):
                return [x for x in value if isinstance(x, dict)]
    return []


def suffix_for(ticker: str) -> str | None:
    text = str(ticker or "").strip().upper()
    return next((suffix for suffix in COUNTRY if text.endswith(suffix)), None)


def is_equity(row: dict) -> bool:
    quote_type = str(row.get("quote_type") or row.get("quoteType") or "").strip().upper()
    if quote_type:
        return quote_type in EQUITY_TYPES
    # Existing published rows can omit quote_type; reject explicit fund markers,
    # otherwise keep a conservative equity-compatible fallback.
    text = " ".join(str(row.get(k) or "") for k in ("asset_type", "type", "category")).upper()
    return not any(token in text for token in ("ETF", "FUND", "MUTUAL", "INDEX"))


def build_audit(rows: Iterable[dict]) -> dict:
    per_suffix = defaultdict(Counter)
    source_counts = Counter()
    totals = Counter()

    for row in rows:
        ticker = str(row.get("ticker") or "").strip().upper()
        suffix = suffix_for(ticker)
        if not suffix or not is_equity(row):
            continue

        bucket = per_suffix[suffix]
        bucket["eligible"] += 1
        totals["eligible"] += 1

        isin = str(row.get("isin") or "").strip().upper()
        lei = str(row.get("lei") or "").strip().upper()
        enriched = bool(row.get("esef_enriched"))
        filing = bool(row.get("esef_period_end") or row.get("esef_retrieval_path") or enriched)

        if isin:
            bucket["with_isin"] += 1
            totals["with_isin"] += 1
        else:
            bucket["missing_isin"] += 1
            totals["missing_isin"] += 1

        if lei:
            bucket["with_lei"] += 1
            totals["with_lei"] += 1
        elif isin:
            bucket["isin_without_lei"] += 1
            totals["isin_without_lei"] += 1

        if filing:
            bucket["filing_found"] += 1
            totals["filing_found"] += 1
        elif lei:
            bucket["lei_without_filing"] += 1
            totals["lei_without_filing"] += 1

        if enriched:
            bucket["esef_enriched"] += 1
            totals["esef_enriched"] += 1

        source = str(row.get("isin_source") or "").strip()
        if source:
            source_counts[source] += 1

    def finalize(counter: Counter) -> dict:
        out = dict(counter)
        eligible = out.get("eligible", 0)
        for key, base in (
            ("isin_rate", out.get("with_isin", 0)),
            ("lei_rate", out.get("with_lei", 0)),
            ("filing_rate", out.get("filing_found", 0)),
            ("enriched_rate", out.get("esef_enriched", 0)),
        ):
            out[key] = round(base / eligible, 4) if eligible else 0.0
        return out

    return {
        "schema_version": 1,
        "scope": "published European equity rows only; offline audit",
        "totals": finalize(totals),
        "by_suffix": {
            suffix: {"country": COUNTRY[suffix], **finalize(per_suffix[suffix])}
            for suffix in COUNTRY
            if per_suffix[suffix].get("eligible", 0)
        },
        "isin_sources": dict(source_counts.most_common()),
    }


def main(input_path: Path = DEFAULT_INPUT, output_path: Path = DEFAULT_OUTPUT) -> dict:
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    audit = build_audit(_rows(payload))
    output_path.write_text(json.dumps(audit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(audit["totals"], sort_keys=True))
    return audit


if __name__ == "__main__":
    main()
