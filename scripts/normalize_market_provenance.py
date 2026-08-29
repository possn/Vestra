"""Normalize source provenance after the main market build.

This stage intentionally runs after run.py because carried-forward rows may contain
legacy source labels from older builds. It never fabricates evidence: labels and
provenance metadata are added only when the corresponding evidence is already
present on the row.
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

SOURCE_FAMILIES = {
    "Yahoo Finance": ("yahoo", "market_and_fundamentals", True),
    "Yahoo Statements (targeted)": ("yahoo", "financial_statements", False),
    "SEC EDGAR": ("sec_edgar", "regulatory_filing", True),
    "ESEF / filings.xbrl.org": ("esef", "regulatory_filing", True),
    OFFICIAL_CONGRESS_SOURCE: ("stock_act", "official_disclosure", True),
}

CARRIED_STATUSES = {
    "equity_carried_forward",
    "catalog_carried_forward",
}
METADATA_STATUSES = {
    "equity_catalog_only",
    "catalog_only",
}


def _source_descriptor(name: str) -> dict:
    family, role, independent = SOURCE_FAMILIES.get(name, ("other", "supplemental", True))
    return {
        "name": name,
        "family": family,
        "role": role,
        "independent": independent,
    }


def _evidence_state(row: dict) -> str:
    status = str(row.get("pipeline_status") or "").strip().lower()
    if status in METADATA_STATUSES:
        return "metadata_only"
    if status in CARRIED_STATUSES:
        return "carried_forward"
    return "observed"


def _filing_periods(row: dict) -> dict:
    periods = {}
    if row.get("sec_period_end"):
        periods["sec_edgar"] = row.get("sec_period_end")
    if row.get("esef_period_end"):
        periods["esef"] = row.get("esef_period_end")
    return periods


def build_provenance(row: dict, generated_at: str | None = None) -> dict:
    sources = [str(x).strip() for x in (row.get("data_sources") or []) if str(x).strip()]
    descriptors = [_source_descriptor(name) for name in sources]
    families = list(dict.fromkeys(d["family"] for d in descriptors))
    independent_families = list(dict.fromkeys(
        d["family"] for d in descriptors if d["independent"]
    ))

    agreement_checks = row.get("source_agreement_checks")
    try:
        agreement_checks = max(0, int(agreement_checks or 0))
    except (TypeError, ValueError):
        agreement_checks = 0

    agreement_pct = row.get("source_agreement_pct")
    if not isinstance(agreement_pct, (int, float)):
        agreement_pct = None

    out = {
        "schema_version": 1,
        "evidence_state": _evidence_state(row),
        "sources": descriptors,
        "source_count": len(descriptors),
        "source_families": families,
        "independent_source_count": len(independent_families),
        "independent_source_families": independent_families,
        "agreement_checks": agreement_checks,
        "agreement_pct": agreement_pct,
        "filing_periods": _filing_periods(row),
    }
    if generated_at:
        out["pipeline_generated_at"] = generated_at
    if row.get("identity_source"):
        out["identity_source"] = row.get("identity_source")
    if row.get("isin"):
        out["isin"] = row.get("isin")
    if row.get("lei"):
        out["lei"] = row.get("lei")
    if row.get("derived_metrics"):
        out["derived_metrics"] = list(row.get("derived_metrics") or [])
        out["derived_metrics_are_independent"] = False
    return out


def normalize_row(row: dict, generated_at: str | None = None) -> bool:
    sources = [str(x).strip() for x in (row.get("data_sources") or []) if str(x).strip()]
    before_sources = list(sources)
    before_provenance = row.get("data_provenance")
    sources = [x for x in sources if x not in LEGACY_CONGRESS_SOURCES]
    if row.get("congress_trades"):
        if OFFICIAL_CONGRESS_SOURCE not in sources:
            sources.append(OFFICIAL_CONGRESS_SOURCE)
    # Stable order + dedupe while preserving first occurrence.
    row["data_sources"] = list(dict.fromkeys(sources))
    row["data_provenance"] = build_provenance(row, generated_at)
    return row["data_sources"] != before_sources or row["data_provenance"] != before_provenance


def main() -> None:
    payload = json.loads(STOCKS.read_text(encoding="utf-8"))
    rows = payload.get("stocks") or []
    generated_at = payload.get("generated_at")
    changed = sum(
        1 for row in rows
        if isinstance(row, dict) and normalize_row(row, generated_at)
    )
    payload["provenance_normalization"] = {
        "schema_version": 1,
        "canonical_congress_source": OFFICIAL_CONGRESS_SOURCE,
        "row_contract": "data_provenance",
        "rows_changed": changed,
    }
    STOCKS.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"Provenance normalized: {changed} rows changed")


if __name__ == "__main__":
    main()
