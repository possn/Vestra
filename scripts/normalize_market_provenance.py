"""Normalize source provenance after the main market build.

This stage intentionally runs after run.py because carried-forward rows may contain
legacy source labels from older builds. It never fabricates evidence: labels and
provenance metadata are added only when the corresponding evidence is already
present on the row.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from source_agreement import (
    SOURCE_AGREEMENT_METHOD,
    SOURCE_AGREEMENT_MIN_CHECKS,
    consume_esef_same_period_observation,
    finite_number,
)

ROOT = Path(__file__).resolve().parents[1]
STOCKS = ROOT / "data" / "stocks.json"
OFFICIAL_CONGRESS_SOURCE = "Official House/Senate disclosures / STOCK Act"
LEGACY_CONGRESS_SOURCES = {
    "STOCK Act / Bargo",
    "Bargo",
    "Bargo / STOCK Act",
    "U.S. House Clerk / STOCK Act",
}

# Provenance is domain-aware. A source may be independent evidence for one domain
# (e.g. Form 4 for insider activity) without being independent confirmation of
# accounting fundamentals. Unknown sources are conservative by default and never
# increase fundamental-source counts silently.
SOURCE_DEFINITIONS = {
    "Yahoo Finance": {
        "family": "yahoo",
        "role": "market_and_fundamentals",
        "independent_for": ["fundamentals", "market"],
    },
    "Yahoo Statements (targeted)": {
        "family": "yahoo",
        "role": "financial_statements",
        "independent_for": [],
    },
    "Yahoo Quarterly Statements (TTM)": {
        "family": "yahoo",
        "role": "financial_statements_ttm",
        "independent_for": [],
    },
    "SEC EDGAR": {
        "family": "sec_edgar",
        "role": "regulatory_filing",
        "independent_for": ["fundamentals"],
    },
    "SEC Capital Structure": {
        "family": "sec_edgar",
        "role": "capital_structure",
        "independent_for": ["capital_structure"],
    },
    "ESEF / filings.xbrl.org": {
        "family": "esef",
        "role": "regulatory_filing",
        "independent_for": ["fundamentals"],
    },
    "Analyst feed": {
        "family": "analyst",
        "role": "estimates_and_consensus",
        "independent_for": ["estimates"],
    },
    "SEC Form 4": {
        "family": "sec_form4",
        "role": "official_insider_disclosure",
        "independent_for": ["insider"],
    },
    OFFICIAL_CONGRESS_SOURCE: {
        "family": "stock_act",
        "role": "official_disclosure",
        "independent_for": ["political_disclosure"],
    },
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
    definition = SOURCE_DEFINITIONS.get(name) or {
        "family": "other",
        "role": "supplemental",
        "independent_for": [],
    }
    independent_for = list(definition.get("independent_for") or [])
    return {
        "name": name,
        "family": definition.get("family") or "other",
        "role": definition.get("role") or "supplemental",
        "independent": bool(independent_for),
        "independent_for": independent_for,
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


def _families_for_domain(descriptors: list[dict], domain: str) -> list[str]:
    return list(dict.fromkeys(
        d["family"] for d in descriptors
        if domain in (d.get("independent_for") or [])
    ))


def build_provenance(row: dict, generated_at: str | None = None) -> dict:
    sources = [str(x).strip() for x in (row.get("data_sources") or []) if str(x).strip()]
    descriptors = [_source_descriptor(name) for name in sources]
    families = list(dict.fromkeys(d["family"] for d in descriptors))
    fundamental_families = _families_for_domain(descriptors, "fundamentals")
    domain_families = {
        domain: _families_for_domain(descriptors, domain)
        for domain in ("fundamentals", "market", "estimates", "insider", "political_disclosure", "capital_structure")
    }
    domain_families = {k: v for k, v in domain_families.items() if v}

    agreement_checks = row.get("source_agreement_checks")
    try:
        agreement_checks = max(0, int(agreement_checks or 0))
    except (TypeError, ValueError):
        agreement_checks = 0

    agreement_pct = finite_number(row.get("source_agreement_pct"))
    if agreement_checks < SOURCE_AGREEMENT_MIN_CHECKS:
        agreement_pct = None

    out = {
        "schema_version": 2,
        "evidence_state": _evidence_state(row),
        "sources": descriptors,
        "source_count": len(descriptors),
        "source_families": families,
        "independent_fundamental_source_count": len(fundamental_families),
        "independent_fundamental_source_families": fundamental_families,
        # Backward-compatible aliases now explicitly scoped to fundamentals.
        "independent_source_count": len(fundamental_families),
        "independent_source_families": fundamental_families,
        "independent_source_scope": "fundamentals",
        "independent_source_families_by_domain": domain_families,
        "agreement_checks": agreement_checks,
        "agreement_pct": agreement_pct,
        "filing_periods": _filing_periods(row),
    }
    agreement_details = row.get("source_agreement_details")
    if isinstance(agreement_details, list) and agreement_details:
        out["agreement_details"] = agreement_details
    if row.get("source_agreement_period_end"):
        out["agreement_period_end"] = row.get("source_agreement_period_end")
    if row.get("source_agreement_method"):
        out["agreement_method"] = row.get("source_agreement_method")
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
    consumed_observation = consume_esef_same_period_observation(row)
    sources = [x for x in sources if x not in LEGACY_CONGRESS_SOURCES]
    if row.get("congress_trades"):
        if OFFICIAL_CONGRESS_SOURCE not in sources:
            sources.append(OFFICIAL_CONGRESS_SOURCE)
    # Stable order + dedupe while preserving first occurrence.
    row["data_sources"] = list(dict.fromkeys(sources))
    row["data_provenance"] = build_provenance(row, generated_at)
    return consumed_observation or row["data_sources"] != before_sources or row["data_provenance"] != before_provenance


def main() -> None:
    payload = json.loads(STOCKS.read_text(encoding="utf-8"))
    rows = payload.get("stocks") or []
    generated_at = payload.get("generated_at")
    changed = sum(
        1 for row in rows
        if isinstance(row, dict) and normalize_row(row, generated_at)
    )
    payload["provenance_normalization"] = {
        "schema_version": 2,
        "canonical_congress_source": OFFICIAL_CONGRESS_SOURCE,
        "row_contract": "data_provenance",
        "independent_source_scope": "fundamentals",
        "source_agreement_min_checks": SOURCE_AGREEMENT_MIN_CHECKS,
        "source_agreement_method": SOURCE_AGREEMENT_METHOD,
        "rows_changed": changed,
    }
    STOCKS.write_text(json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"Provenance normalized: {changed} rows changed")


if __name__ == "__main__":
    main()
