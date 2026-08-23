"""Vestra v4.7 — structural quality / moat persistence overlay.

This module deliberately does not pretend to identify an economic moat from a
single accounting ratio. It scores *observable persistence* that is consistent
with durable economics: margin stability, ROE/ROCE persistence, growth without
share dilution, and resilience of recent operating trends.

The output is an overlay. It should inform the dossier and thesis, not silently
replace the core Vestra score.
"""
from __future__ import annotations

import math


def _n(v):
    try:
        x = float(v)
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def _clamp(v, lo=0.0, hi=100.0):
    return max(lo, min(hi, float(v)))


def _avg(values):
    vals = [float(v) for v in values if v is not None]
    return sum(vals) / len(vals) if vals else None


def _std(values):
    vals = [float(v) for v in values if v is not None]
    if len(vals) < 2:
        return None
    mean = sum(vals) / len(vals)
    return (sum((v - mean) ** 2 for v in vals) / len(vals)) ** 0.5


def _persistence_score(values, *, floor=None, volatility_scale=0.10):
    """Reward a consistently healthy series, not merely one good observation."""
    vals = [_n(v) for v in values]
    vals = [v for v in vals if v is not None]
    if len(vals) < 2:
        return None
    mean = sum(vals) / len(vals)
    stdev = _std(vals) or 0.0
    stability = _clamp(100.0 - (stdev / max(volatility_scale, 1e-9)) * 45.0)
    if floor is None:
        return stability
    level = _clamp(50.0 + ((mean - floor) / max(abs(floor), 0.05)) * 25.0)
    return _avg([stability, level])


def _trend_score(values):
    vals = [_n(v) for v in values]
    vals = [v for v in vals if v is not None]
    if len(vals) < 2:
        return None
    # annual_quality_history is newest first; compare newest with oldest.
    delta = vals[0] - vals[-1]
    return _clamp(50.0 + delta * 180.0)


def assess(row: dict) -> dict:
    if str(row.get("quote_type") or "").upper() in {"ETF", "CRYPTO"}:
        return {
            "moat_score": None,
            "moat_label": "not_applicable",
            "moat_components": {},
            "moat_reasons": [],
        }

    hist = row.get("annual_quality_history") or []
    if not isinstance(hist, list):
        hist = []
    hist = [x for x in hist if isinstance(x, dict)][:4]

    gross = [x.get("gross_margin") for x in hist]
    operating = [x.get("operating_margin") for x in hist]
    net = [x.get("net_margin") for x in hist]
    roe = [x.get("roe") for x in hist]
    roce = [x.get("roce_proxy") for x in hist]

    margin_persistence = _avg([
        _persistence_score(gross, floor=0.20, volatility_scale=0.08),
        _persistence_score(operating, floor=0.10, volatility_scale=0.07),
        _persistence_score(net, floor=0.06, volatility_scale=0.06),
    ])
    capital_efficiency = _avg([
        _persistence_score(roe, floor=0.12, volatility_scale=0.10),
        _persistence_score(roce, floor=0.10, volatility_scale=0.09),
    ])
    trend = _avg([
        _trend_score(operating),
        _trend_score(net),
        _trend_score(roce),
    ])

    revenue_growth = _n(row.get("revenue_growth"))
    revenue_latest = _n(row.get("revenue_yoy_latest"))
    dilution = _n(row.get("diluted_shares_yoy"))
    growth_level = _avg([revenue_growth, revenue_latest])
    if growth_level is None:
        growth_quality = None
    else:
        growth_quality = _clamp(50.0 + growth_level * 160.0)
        if dilution is not None:
            # Growth funded by material share issuance is lower-quality growth.
            growth_quality -= _clamp(max(0.0, dilution) * 180.0, 0.0, 35.0)
        growth_quality = _clamp(growth_quality)

    pricing_power = _avg([
        _persistence_score(gross, floor=0.25, volatility_scale=0.06),
        _trend_score(gross),
    ])

    cash_conversion = _n(row.get("cash_conversion_ratio"))
    accrual = _n(row.get("accrual_ratio"))
    fcf_margin = _n(row.get("fcf_margin"))
    cash_quality_parts = []
    if cash_conversion is not None:
        cash_quality_parts.append(_clamp(45.0 + cash_conversion * 35.0))
    if accrual is not None:
        cash_quality_parts.append(_clamp(70.0 - accrual * 500.0))
    if fcf_margin is not None:
        cash_quality_parts.append(_clamp(50.0 + fcf_margin * 160.0))
    cash_quality = _avg(cash_quality_parts)

    components = {
        "margin_persistence": margin_persistence,
        "capital_efficiency": capital_efficiency,
        "growth_quality": growth_quality,
        "pricing_power_proxy": pricing_power,
        "cash_quality": cash_quality,
        "structural_trend": trend,
    }
    weighted = [
        (margin_persistence, 0.24),
        (capital_efficiency, 0.24),
        (growth_quality, 0.14),
        (pricing_power, 0.14),
        (cash_quality, 0.14),
        (trend, 0.10),
    ]
    present = [(v, w) for v, w in weighted if v is not None]
    if not present:
        score = None
    else:
        score = sum(v * w for v, w in present) / sum(w for _, w in present)

    reasons = []
    if margin_persistence is not None:
        if margin_persistence >= 75:
            reasons.append("Margens persistentemente fortes")
        elif margin_persistence < 45:
            reasons.append("Margens pouco persistentes")
    if capital_efficiency is not None:
        if capital_efficiency >= 75:
            reasons.append("ROE/ROCE sustentados")
        elif capital_efficiency < 45:
            reasons.append("Eficiência de capital inconsistente")
    if growth_quality is not None:
        if growth_quality >= 70 and (dilution is None or dilution <= 0.03):
            reasons.append("Crescimento com baixa diluição")
        elif dilution is not None and dilution > 0.10:
            reasons.append("Diluição reduz a qualidade do crescimento")
    if pricing_power is not None and pricing_power >= 72:
        reasons.append("Persistência de margem sugere pricing power")
    if cash_quality is not None and cash_quality >= 72:
        reasons.append("Lucros bem suportados por caixa")
    if trend is not None and trend < 40:
        reasons.append("Persistência económica a deteriorar")

    if score is None:
        label = "insufficient"
    elif score >= 80:
        label = "durable"
    elif score >= 65:
        label = "promising"
    elif score >= 50:
        label = "mixed"
    else:
        label = "weak"

    return {
        "moat_score": round(score, 1) if score is not None else None,
        "moat_label": label,
        "moat_components": {k: (round(v, 1) if v is not None else None) for k, v in components.items()},
        "moat_reasons": reasons[:5],
    }
