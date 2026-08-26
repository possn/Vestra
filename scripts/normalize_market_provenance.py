"""Normalize source provenance after the main market build.

This stage intentionally runs after run.py because carried-forward rows may contain
legacy source labels from older builds. It never fabricates evidence: labels are
added only when the corresponding evidence payload is present on the row.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STOCKS = ROOT / "data" / "stocks.json"
OFFICIAL_CONGRESS_SOURCE = "Official House/Senate disclosures / STOCK Act"
LEGACY_CONGRESS_SOURCES = {
    "STOCK Act / Bargo",
    "Bargo",
    "Bargo / STOCK Act",
    "U.S. House Clerk / STOCK Act",
}


def normalize_row(row: dict) -> bool:
    sources = [str(x).strip() for x in (row.get("data_sources") or []) if str(x).strip()]
    before = list(sources)
    sources = [x for x in sources if x not in LEGACY_CONGRESS_SOURCES]
    if row.get("congress_trades"):
        if OFFICIAL_CONGRESS_SOURCE not in sources:
            sources.append(OFFICIAL_CONGRESS_SOURCE)
    # Stable order + dedupe while preserving first occurrence.
    row["data_sources"] = list(dict.fromkeys(sources))
    return row["data_sources"] != before


def main() -> None:
    payload = json.loads(STOCKS.read_text(encoding="utf-8"))
    rows = payload.get("stocks") or []
    changed = sum(1 for row in rows if isinstance(row, dict) and normalize_row(row))
    payload["provenance_normalization"] = {
        "canonical_congress_source": OFFICIAL_CONGRESS_SOURCE,
        "rows_changed": changed,
    }
    STOCKS.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"Provenance normalized: {changed} rows changed")


if __name__ == "__main__":
    main()
