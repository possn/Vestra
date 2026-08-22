"""Vestra v4.3 evidence-confidence engine.

Confidence is deliberately separate from attractiveness. A company can have a
low investment score with high confidence (strong evidence that risk is real),
or a high factor score with low confidence (sparse/stale/unconfirmed data).

The engine combines:
- metric coverage;
- source authority/diversity;
- statement freshness;
- independent-source agreement when available;
- provenance completeness.

It does not change the investment score directly. It changes how strongly
Vestra is allowed to communicate a thesis.
"""
from __future__ import annotations

import datetime as _dt


def _n(v):
    try:
        x = float(v)
        return x if x == x else None
    except (TypeError, ValueError):
        return None


def _date(v):
    if not v:
        return None
    s = str(v)[:10]
    try:
        return _dt.date.fromisoformat(s)
    except Exception:
        return None


def _latest_statement_date(row: dict):
    dates = []
    for key in ("sec_period_end", "esef_period_end"):
        d = _date(row.get(key))
        if d:
            dates.append(d)
    for key in ("quarterly_revenue", "quarterly_net_income", "quarterly_eps"):
        vals = row.get(key)
        if isinstance(vals, list):
            for item in vals[:2]:
                if isinstance(item, dict):
                    d = _date(item.get("date"))
                    if d:
                        dates.append(d)
    return max(dates) if dates else None


def _freshness_score(row: dict, today=None):
    today = today or _dt.date.today()
    d = _latest_statement_date(row)
    if not d:
        return 50.0, None
    age = max(0, (today - d).days)
    if age <= 120:
        score = 100.0
    elif age <= 180:
        score = 90.0
    elif age <= 270:
        score = 78.0
    elif age <= 365:
        score = 65.0
    elif age <= 540:
        score = 45.0
    else:
        score = 25.0
    return score, age


def _source_score(row: dict):
    sources = {str(x) for x in (row.get("data_sources") or [])}
    official = bool(sources & {"SEC EDGAR", "ESEF / filings.xbrl.org"})
    yahoo = "Yahoo Finance" in sources
    analyst = "Analyst feed" in sources
    capital = "SEC Capital Structure" in sources

    if official and yahoo:
        score = 94.0
    elif official:
        score = 90.0
    elif yahoo:
        score = 68.0
    else:
        score = 45.0

    # Independent contextual sources improve provenance breadth, but never make
    # up for missing fundamental statements.
    if analyst:
        score += 3.0
    if capital:
        score += 2.0
    return min(100.0, score), official, len(sources)


def assess(row: dict) -> dict:
    if row.get("quote_type") in ("ETF", "CRYPTO"):
        return {
            "metric_confidence": row.get("data_confidence") or "low",
            "confidence_score": None,
            "confidence_label": row.get("data_confidence") or "low",
            "confidence_components": {},
            "confidence_reasons": [],
        }

    coverage = _n(row.get("data_coverage_pct"))
    coverage_score = max(0.0, min(100.0, coverage if coverage is not None else 0.0))
    source_score, has_official, source_count = _source_score(row)
    freshness_score, age_days = _freshness_score(row)

    checks = _n(row.get("source_agreement_checks")) or 0.0
    agreement = _n(row.get("source_agreement_pct"))
    if agreement is not None and checks >= 2:
        agreement_score = max(0.0, min(100.0, agreement))
    elif has_official and source_count >= 2:
        # Official source exists but there were not enough like-for-like values
        # to claim agreement. Neutral, not a reward.
        agreement_score = 60.0
    else:
        agreement_score = 52.0

    identity_score = 100.0
    if "ESEF / filings.xbrl.org" in (row.get("data_sources") or []):
        identity_score = 100.0 if row.get("isin") and row.get("lei") else 55.0
    elif "SEC EDGAR" in (row.get("data_sources") or []):
        identity_score = 95.0
    elif row.get("ticker"):
        identity_score = 75.0

    score = (
        coverage_score * 0.34
        + source_score * 0.24
        + freshness_score * 0.20
        + agreement_score * 0.14
        + identity_score * 0.08
    )

    # A failed cross-check is evidence uncertainty, not investment risk.
    if agreement is not None and checks >= 2 and agreement < 50:
        score = min(score, 54.0)
    elif agreement is not None and checks >= 2 and agreement < 70:
        score = min(score, 69.0)

    # Very stale statements cannot support a high-confidence current thesis.
    if age_days is not None and age_days > 540:
        score = min(score, 49.0)
    elif age_days is not None and age_days > 365:
        score = min(score, 64.0)

    score = round(max(0.0, min(100.0, score)), 1)
    label = "high" if score >= 80 else "medium" if score >= 60 else "low"

    reasons = []
    if coverage_score >= 75:
        reasons.append("Cobertura fundamental elevada")
    elif coverage_score < 45:
        reasons.append("Cobertura fundamental limitada")
    if has_official:
        reasons.append("Filings oficiais presentes")
    elif source_count <= 1:
        reasons.append("Dependência de uma única fonte principal")
    if age_days is not None:
        if age_days <= 180:
            reasons.append("Contas recentes")
        elif age_days > 365:
            reasons.append("Contas desatualizadas")
    if agreement is not None and checks >= 2:
        if agreement >= 85:
            reasons.append("Fontes independentes concordam")
        elif agreement < 70:
            reasons.append("Divergência entre fontes")
    elif has_official:
        reasons.append("Cross-check ainda insuficiente")

    return {
        "metric_confidence": row.get("data_confidence") or "low",
        "data_confidence": label,
        "confidence_score": score,
        "confidence_label": label,
        "confidence_components": {
            "coverage": round(coverage_score, 1),
            "source_quality": round(source_score, 1),
            "freshness": round(freshness_score, 1),
            "source_agreement": round(agreement_score, 1),
            "identity": round(identity_score, 1),
        },
        "confidence_reasons": reasons[:4],
        "fundamental_age_days": age_days,
    }
