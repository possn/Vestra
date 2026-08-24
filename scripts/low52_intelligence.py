"""Vestra 52-week-low intelligence overlay with strict evidence gating.

Price proximity alone is never enough to call an equity an opportunity. Sparse
dossiers are explicitly classified as insufficient and receive no opportunity
score until coverage and confidence cross minimum thresholds.
"""
from __future__ import annotations


def _n(v):
    try:
        if v is None or v == "":
            return None
        x = float(v)
        return x if x == x else None
    except Exception:
        return None


def _clamp(v, lo=0.0, hi=100.0):
    return max(lo, min(hi, float(v)))


def _price_position(row: dict):
    hist = row.get("price_history_1y") or []
    closes = []
    for item in hist:
        try:
            v = item.get("close") if isinstance(item, dict) else item
            v = float(v)
            if v > 0:
                closes.append(v)
        except Exception:
            pass
    current = _n(row.get("current_price"))
    if current is None and closes:
        current = closes[-1]
    if not closes or current is None or current <= 0:
        return None
    low, high = min(closes), max(closes)
    if low <= 0 or high <= 0:
        return None
    return {
        "low": low,
        "high": high,
        "current": current,
        "above_low_pct": (current / low - 1.0) * 100.0,
        "drawdown_from_high_pct": (current / high - 1.0) * 100.0,
        "range_position_pct": ((current - low) / (high - low) * 100.0) if high > low else 0.0,
    }


def _insufficient(pos, reason):
    out = {
        "low52_status": "insufficient",
        "low52_label": "Dados insuficientes",
        "low52_score": None,
        "low52_resilience_score": None,
        "low52_deterioration_penalty": None,
        "low52_reasons": [reason],
    }
    if pos:
        out.update({
            "low52_above_low_pct": round(pos["above_low_pct"], 2),
            "low52_drawdown_from_high_pct": round(pos["drawdown_from_high_pct"], 2),
            "low52_range_position_pct": round(pos["range_position_pct"], 1),
            "low52_price_low": round(pos["low"], 6),
            "low52_price_high": round(pos["high"], 6),
        })
    return out


def assess(row: dict) -> dict:
    if str(row.get("quote_type") or "").upper() in ("ETF", "CRYPTO", "MUTUALFUND"):
        return {}

    pos = _price_position(row)
    if not pos:
        return _insufficient(None, "Histórico de preço insuficiente")

    score = _n(row.get("score"))
    coverage = _n(row.get("data_coverage_pct"))
    critical = _n(row.get("critical_metric_coverage_pct"))
    confidence = _n(row.get("confidence_score"))
    reliability = str(row.get("score_reliability") or "").lower()

    # Hard evidence gate: a 52-week low is only a price fact. It cannot become
    # an investment opportunity label without enough fundamental evidence.
    if score is None:
        return _insufficient(pos, "Score fundamental suprimido por evidência insuficiente")
    if coverage is None or coverage < 55:
        return _insufficient(pos, "Cobertura fundamental inferior a 55%")
    if critical is not None and critical < 45:
        return _insufficient(pos, "Cobertura de métricas críticas insuficiente")
    if confidence is None or confidence < 50:
        return _insufficient(pos, "Confiança dos dados insuficiente")
    if reliability in ("insufficient", "suppressed"):
        return _insufficient(pos, "Fiabilidade insuficiente para classificar oportunidade")

    quality = _n(row.get("quality_pct"))
    balance = _n(row.get("balance_pct"))
    cashflow = _n(row.get("cashflow_pct"))
    execution = _n(row.get("execution_pct"))
    value = _n(row.get("value_pct"))
    mos = _n(row.get("margin_of_safety_pct"))
    revenue_growth = _n(row.get("revenue_growth"))
    revenue_accel = _n(row.get("revenue_yoy_acceleration_pp"))
    margin_change = _n(row.get("net_margin_yoy_change_pp"))
    dilution = _n(row.get("diluted_shares_yoy"))
    est = _n(row.get("estimate_momentum_score"))
    est_signal = str(row.get("estimate_signal") or "").lower()
    thesis = str(row.get("thesis_direction") or "").lower()
    gate = str(row.get("risk_gate") or "clear").lower()
    valuation = str(row.get("valuation_signal") or "").lower()
    capital_risk = str(row.get("capital_structure_risk") or "clear").lower()
    flags = set(row.get("risk_flags") or []) | set(row.get("capital_structure_flags") or [])

    resilience_parts = [x for x in (quality, balance, cashflow, execution, confidence) if x is not None]
    if len(resilience_parts) < 3:
        return _insufficient(pos, "Poucas dimensões fundamentais observadas")
    resilience = sum(resilience_parts) / len(resilience_parts)

    deterioration = 0.0
    reasons = []
    positives = []
    if gate == "severe": deterioration += 35; reasons.append("Risk Gate severe")
    elif gate == "high": deterioration += 25; reasons.append("Risk Gate high")
    elif gate == "watch": deterioration += 8; reasons.append("Risk Gate watch")
    if capital_risk in ("high", "severe"): deterioration += 18; reasons.append("estrutura de capital frágil")
    if {"severe_dilution", "material_dilution"} & flags: deterioration += 14; reasons.append("diluição material")
    if dilution is not None and dilution > 0.20: deterioration += 12; reasons.append(f"ações diluídas +{dilution*100:.0f}%")
    if revenue_growth is not None and revenue_growth < -0.15: deterioration += 12; reasons.append(f"receita {revenue_growth*100:.0f}% YoY")
    elif revenue_growth is not None and revenue_growth < -0.05: deterioration += 6; reasons.append("receita em contração")
    if revenue_accel is not None and revenue_accel < -8: deterioration += 7; reasons.append("crescimento a desacelerar")
    if margin_change is not None and margin_change < -3: deterioration += 7; reasons.append("margens a deteriorar")
    if thesis == "down": deterioration += 9; reasons.append("tese quantitativa a piorar")
    if est_signal == "deteriorating": deterioration += 10; reasons.append("expectativas a piorar")

    if quality is not None and quality >= 65: positives.append(f"qualidade {quality:.0f}/100")
    if balance is not None and balance >= 60: positives.append(f"balanço {balance:.0f}/100")
    if confidence >= 70: positives.append(f"confiança {confidence:.0f}/100")
    if valuation == "undervalued" or (mos is not None and mos >= 10): positives.append("valuation com margem de segurança")
    if est_signal == "improving" and est is not None: positives.append(f"expectativas a melhorar {est:.0f}/100")
    if revenue_accel is not None and revenue_accel >= 5: positives.append("receita a reacelerar")
    if margin_change is not None and margin_change >= 1: positives.append("margens a melhorar")

    proximity = _clamp(100 - max(0.0, pos["above_low_pct"]) * 6.0)
    valuation_component = 50.0
    if valuation == "undervalued": valuation_component = 82.0
    elif valuation == "fair": valuation_component = 62.0
    elif valuation == "overvalued": valuation_component = 25.0
    elif value is not None: valuation_component = value
    if mos is not None:
        valuation_component = _clamp((valuation_component + _clamp(50 + mos)) / 2)

    opportunity = _clamp(
        proximity * 0.20 + resilience * 0.35 + valuation_component * 0.20
        + (est if est is not None else 50.0) * 0.10 + score * 0.15 - deterioration
    )

    near_low = pos["above_low_pct"] <= 10
    if not near_low: status = "not_near_low"
    elif gate in ("high", "severe") or deterioration >= 35: status = "structural_risk"
    elif deterioration >= 20 or resilience < 48: status = "value_trap_risk"
    elif opportunity >= 70 and resilience >= 62 and confidence >= 60 and coverage >= 65: status = "opportunity"
    elif opportunity >= 58 and deterioration < 18 and confidence >= 55 and coverage >= 60: status = "watch"
    else: status = "uncertain"

    label = {
        "opportunity": "Oportunidade potencial",
        "watch": "Queda saudável / acompanhar",
        "uncertain": "Indeterminado",
        "value_trap_risk": "Risco de value trap",
        "structural_risk": "Deterioração estrutural",
        "not_near_low": "Fora da zona de mínimo",
    }.get(status, "Dados insuficientes")

    why = [f"{max(0.0, pos['above_low_pct']):.1f}% acima do mínimo 52s"] + positives[:3] + reasons[:3]
    return {
        "low52_status": status,
        "low52_label": label,
        "low52_score": round(opportunity, 1),
        "low52_resilience_score": round(_clamp(resilience), 1),
        "low52_deterioration_penalty": round(deterioration, 1),
        "low52_above_low_pct": round(pos["above_low_pct"], 2),
        "low52_drawdown_from_high_pct": round(pos["drawdown_from_high_pct"], 2),
        "low52_range_position_pct": round(pos["range_position_pct"], 1),
        "low52_price_low": round(pos["low"], 6),
        "low52_price_high": round(pos["high"], 6),
        "low52_reasons": why[:6],
    }
