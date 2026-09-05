"""Pure helpers for diagnostic cross-source fundamental agreement.

This module has no network or market-data dependencies. It deliberately compares
only annual observations from the exact same fiscal period and never changes the
canonical fundamental values, confidence calculation or Vestra Score.
"""
from __future__ import annotations

import math

ESEF_AGREEMENT_OBSERVATION_KEY = "_esef_same_period_observation"
AGREEMENT_METRICS = ("gross_margin", "operating_margin", "net_margin", "roe")
SOURCE_AGREEMENT_MIN_CHECKS = 2
SOURCE_AGREEMENT_TOLERANCE_PP = 5.0
SOURCE_AGREEMENT_METHOD = "same_period_annual_yahoo_esef_v1"


def finite_number(value):
    if isinstance(value, bool):
        return None
    try:
        if value is None or value == "":
            return None
        out = float(value)
        return out if math.isfinite(out) else None
    except (TypeError, ValueError):
        return None


def attach_esef_same_period_observation(metrics, period_end, esef_values) -> bool:
    """Attach ESEF values to an exact matching Yahoo annual-history observation."""
    period_text = str(period_end or "").strip()[:10]
    history = getattr(metrics, "annual_quality_history", None)
    if not period_text or not isinstance(history, list):
        return False

    clean = {key: finite_number((esef_values or {}).get(key)) for key in AGREEMENT_METRICS}
    clean = {key: value for key, value in clean.items() if value is not None}
    if not clean:
        return False

    for item in history:
        if not isinstance(item, dict):
            continue
        if str(item.get("date") or "").strip()[:10] != period_text:
            continue
        comparable = {
            key: value for key, value in clean.items()
            if finite_number(item.get(key)) is not None
        }
        if not comparable:
            return False
        item[ESEF_AGREEMENT_OBSERVATION_KEY] = {
            "period_end": period_text,
            "source_family": "esef",
            "metrics": comparable,
        }
        return True
    return False


def consume_esef_same_period_observation(row: dict) -> bool:
    """Consume transient ESEF observations and emit conservative diagnostics.

    The temporary marker is always removed when encountered. `agreement_pct` is
    emitted only when at least SOURCE_AGREEMENT_MIN_CHECKS metrics are comparable.
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
            yahoo_value = finite_number(item.get(metric))
            esef_value = finite_number(metrics.get(metric))
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
