"""Build evidence-quality diagnostics from canonical data_provenance.

This audit is intentionally diagnostic-only. It does not modify scores or confidence.
It measures how much independent *fundamental* evidence supports each dossier, how
fresh official filings are, and where source agreement or freshness is weak by
region/model. Analyst, insider and political-disclosure feeds remain visible as
source families but never count as independent confirmation of fundamentals.
"""
from __future__ import annotations

import collections
import datetime as dt
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "data" / "stocks.json"
OUT = ROOT / "data" / "provenance_audit.json"
FUND_TYPES = {"ETF", "CRYPTO", "MUTUALFUND", "FUND"}


def equity_rows(payload: dict) -> list[dict]:
    return [
        r for r in (payload.get("stocks") or [])
        if str(r.get("quote_type") or "").upper() not in FUND_TYPES
    ]


def _number(value):
    if isinstance(value, bool):
        return None
    try:
        if value is None or value == "":
            return None
        out = float(value)
        return out if out == out and abs(out) != float("inf") else None
    except (TypeError, ValueError):
        return None


def _parse_date(value):
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return dt.date.fromisoformat(text[:10])
    except ValueError:
        return None


def _filing_age_days(provenance: dict, today: dt.date) -> int | None:
    periods = provenance.get("filing_periods") or {}
    dates = [_parse_date(v) for v in periods.values()]
    dates = [d for d in dates if d is not None]
    if not dates:
        return None
    return max(0, (today - max(dates)).days)


def _freshness_bucket(age):
    if age is None:
        return "no_official_filing_date"
    if age <= 190:
        return "lte190d"
    if age <= 400:
        return "191_400d"
    if age <= 730:
        return "401_730d"
    return "gt730d"


def _independent_bucket(count):
    try:
        n = max(0, int(count or 0))
    except (TypeError, ValueError):
        n = 0
    return "3plus" if n >= 3 else str(n)


def _agreement_bucket(provenance: dict):
    checks = int(provenance.get("agreement_checks") or 0)
    pct = _number(provenance.get("agreement_pct"))
    if checks <= 0 or pct is None:
        return "not_measured"
    if pct >= 90:
        return "gte90"
    if pct >= 75:
        return "75_89"
    return "lt75"


def _fundamental_families(provenance: dict) -> list[str]:
    explicit = provenance.get("independent_fundamental_source_families")
    if isinstance(explicit, list):
        return [str(x) for x in explicit if x]
    # Compatibility with schema v1 rows. In v1 the generic field was intended
    # to represent independent evidence; schema v2 narrows this explicitly.
    legacy = provenance.get("independent_source_families") or []
    return [str(x) for x in legacy if x]


def _fundamental_count(provenance: dict) -> int:
    value = provenance.get("independent_fundamental_source_count")
    if value is None:
        value = provenance.get("independent_source_count")
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def summarize(rows: list[dict], today: dt.date | None = None) -> dict:
    today = today or dt.date.today()
    state = collections.Counter()
    independent_fundamental = collections.Counter()
    freshness = collections.Counter()
    agreement = collections.Counter()
    source_families = collections.Counter()
    fundamental_families = collections.Counter()
    official_family_rows = 0
    observed_rows = 0
    with_provenance = 0
    ages = []

    for row in rows:
        p = row.get("data_provenance") if isinstance(row.get("data_provenance"), dict) else {}
        if p:
            with_provenance += 1
        evidence_state = str(p.get("evidence_state") or "unknown")
        state[evidence_state] += 1
        if evidence_state == "observed":
            observed_rows += 1
        independent_fundamental[_independent_bucket(_fundamental_count(p))] += 1
        agreement[_agreement_bucket(p)] += 1

        all_families = {str(x) for x in (p.get("source_families") or []) if x}
        for family in all_families:
            source_families[family] += 1

        fundamental = set(_fundamental_families(p))
        for family in fundamental:
            fundamental_families[family] += 1
        if fundamental & {"sec_edgar", "esef"}:
            official_family_rows += 1

        age = _filing_age_days(p, today)
        freshness[_freshness_bucket(age)] += 1
        if age is not None:
            ages.append(age)

    count = len(rows)
    return {
        "count": count,
        "rows_with_provenance": with_provenance,
        "provenance_coverage_pct": round(with_provenance / count * 100, 1) if count else 0.0,
        "evidence_state": dict(state),
        "independent_fundamental_source_count": dict(independent_fundamental),
        "agreement": dict(agreement),
        "official_filing_freshness": dict(freshness),
        "official_filing_rows": official_family_rows,
        "official_filing_coverage_pct": round(official_family_rows / count * 100, 1) if count else 0.0,
        "source_family_coverage": dict(source_families.most_common()),
        "fundamental_source_family_coverage": dict(fundamental_families.most_common()),
        "avg_latest_official_filing_age_days": round(sum(ages) / len(ages), 1) if ages else None,
        "observed_pct": round(observed_rows / count * 100, 1) if count else 0.0,
    }


def weakness_key(row: dict, today: dt.date):
    p = row.get("data_provenance") if isinstance(row.get("data_provenance"), dict) else {}
    state = str(p.get("evidence_state") or "unknown")
    state_rank = {"metadata_only": 0, "carried_forward": 1, "unknown": 2, "observed": 3}.get(state, 2)
    independent = _fundamental_count(p)
    age = _filing_age_days(p, today)
    age_rank = age if age is not None else 99999
    coverage = _number(row.get("data_coverage_pct"))
    coverage_rank = coverage if coverage is not None else -1
    return (state_rank, independent, -age_rank, coverage_rank)


def build_audit(payload: dict, today: dt.date | None = None) -> dict:
    today = today or dt.date.today()
    rows = equity_rows(payload)
    by_region = collections.defaultdict(list)
    by_model = collections.defaultdict(list)
    for row in rows:
        by_region[str(row.get("region") or "Unknown")].append(row)
        by_model[str(row.get("score_model") or "general")].append(row)

    weak = sorted(rows, key=lambda row: weakness_key(row, today))[:100]
    return {
        "schema_version": 2,
        "generated_at": dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat(),
        "pipeline_generated_at": payload.get("generated_at"),
        "independent_source_scope": "fundamentals",
        "equities": summarize(rows, today),
        "by_region": {k: summarize(v, today) for k, v in sorted(by_region.items())},
        "by_score_model": {k: summarize(v, today) for k, v in sorted(by_model.items())},
        "weakest_evidence_dossiers": [
            {
                "ticker": row.get("ticker"),
                "name": row.get("name"),
                "region": row.get("region"),
                "score_model": row.get("score_model"),
                "pipeline_status": row.get("pipeline_status"),
                "coverage_pct": _number(row.get("data_coverage_pct")),
                "score_reliability": row.get("score_reliability"),
                "evidence_state": (row.get("data_provenance") or {}).get("evidence_state"),
                "independent_fundamental_source_count": _fundamental_count(row.get("data_provenance") or {}),
                "independent_fundamental_source_families": _fundamental_families(row.get("data_provenance") or {}),
                "agreement_checks": (row.get("data_provenance") or {}).get("agreement_checks", 0),
                "agreement_pct": (row.get("data_provenance") or {}).get("agreement_pct"),
                "latest_official_filing_age_days": _filing_age_days(row.get("data_provenance") or {}, today),
            }
            for row in weak
        ],
    }


def main() -> None:
    payload = json.loads(SRC.read_text(encoding="utf-8"))
    audit = build_audit(payload)
    OUT.write_text(json.dumps(audit, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"Provenance audit: {audit['equities']['count']} equities -> {OUT}")


if __name__ == "__main__":
    main()
