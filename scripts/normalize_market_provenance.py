"""Normalize source provenance after the main market build.

This stage intentionally runs after run.py because carried-forward rows may contain
legacy source labels from older builds. It never fabricates evidence: labels and
provenance metadata are added only when the corresponding evidence is already
present on the row.
"""
from __future__ import annotations

import math
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

# Same-period source agreement is diagnostic-only. A percentage is published only
# when at least two annual metrics can be compared for the exact same fiscal period.
# Five percentage points is deliberately tolerant of presentation/classification
# differences between Yahoo statements and ESEF while still surfacing material
# disagreements. This does not change confidence or Score.
ESEF_AGREEMENT_OBSERVATION_KEY = "_esef_same_period_observation"
AGREEMENT_METRICS = ("gross_margin", "operating_margin", "net_margin", "roe")
SOURCE_AGREEMENT_MIN_CHECKS = 2
SOURCE_AGREEMENT_TOLERANCE_PP = 5.0
SOURCE_AGREEMENT_METHOD = "same_period_annual_yahoo_esef_v1"

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


def _number(value):
    if isinstance(value, bool):
        return None
    try:
        if value is None or value == "":
            return None
        out = float(value)
        return out if math.isfinite(out) else None
    except (TypeError, ValueError):
        return None


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


def _consume_esef_same_period_observation(row: dict) -> bool:
    """Convert transient ESEF observations into a conservative agreement audit.

    ESEF enriches only missing canonical values, so comparing the final row would
    risk comparing a source with itself. Instead the adapter temporarily attaches
    its independent annual observation to the exact Yahoo annual-history period.
    This function consumes and removes that marker before publication.
    """
    history = row.get("annual_quality_history")
    if not isinstance(history, list):
        return False

    details = []
    periods = []
    consumed = False
    for item in history:
        if not isinstance(item, dict):
            continue
        observation = item.pop(ESEF_AGREEMENT_OBSERVATION_KEY, None)
        if not isinstance(observation, dict):
            continue
        consumed = True
        period_end = str(observation.get("period_end") or "").strip()[:10]
        yahoo_period = str(item.get("date") or "").strip()[:10]
        if not period_end or yahoo_period != period_end:
            continue
        metrics = observation.get("metrics") if isinstance(observation.get("metrics"), dict) else {}
        for metric in AGREEMENT_METRICS:
            yahoo_value = _number(item.get(metric))
            esef_value = _number(metrics.get(metric))
            if yahoo_value is None or esef_value is None:
                continue
            signed_delta_pp = (esef_value - yahoo_value) * 100.0
            abs_delta_pp = abs(signed_delta_pp)
            details.append({
                "metric": metric,
                "period_end": period_end,
                "yahoo_value": round(yahoo_value, 8),
                "esef_value": round(esef_value, 8),
                "delta_pp": round(signed_delta_pp, 2),
                "abs_delta_pp": round(abs_delta_pp, 2),
                "tolerance_pp": SOURCE_AGREEMENT_TOLERANCE_PP,
                "agrees": abs_delta_pp <= SOURCE_AGREEMENT_TOLERANCE_PP,
            })
            periods.append(period_end)

    if details:
        checks = len(details)
        row["source_agreement_checks"] = checks
        row["source_agreement_pct"] = (
            round(sum(1 for detail in details if detail["agrees"]) / checks * 100.0, 1)
            if checks >= SOURCE_AGREEMENT_MIN_CHECKS else None
        )
        row["source_agreement_details"] = details
        row["source_agreement_period_end"] = max(periods) if periods else None
        row["source_agreement_method"] = SOURCE_AGREEMENT_METHOD
    return consumed


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

    agreement_pct = _number(row.get("source_agreement_pct"))
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
    consumed_observation = _consume_esef_same_period_observation(row)
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
