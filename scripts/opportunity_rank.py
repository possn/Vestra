"""Best Opportunities Now overlay with strict evidence gating.

Combines independent Vestra signals into an explainable opportunity score.
This is a prioritisation/ranking aid, not an investment recommendation. Sparse
dossiers are never promoted by renormalising a handful of favourable inputs.
"""
from __future__ import annotations


def _f(v):
    try:
        if v is None or v == "":
            return None
        x = float(v)
        return x if x == x and abs(x) != float("inf") else None
    except (TypeError, ValueError):
        return None


def _clip(x):
    return max(0.0, min(100.0, x))


def _weighted(parts):
    vals = [(v, w) for v, w in parts if v is not None]
    if not vals:
        return None
    den = sum(w for _, w in vals)
    return sum(v * w for v, w in vals) / den if den else None


def _insufficient(reason, components=None):
    return {
        "opportunity_score": None,
        "opportunity_label": "Dados insuficientes",
        "opportunity_reasons": [],
        "opportunity_cautions": [reason],
        "opportunity_components": components or {},
        "opportunity_eligible": False,
        "opportunity_suppressed_reason": reason,
    }


def assess(row: dict) -> dict:
    if str(row.get("quote_type") or "").upper() in ("ETF", "CRYPTO", "MUTUALFUND"):
        return _insufficient("Instrumento fora do ranking de ações")

    score = _f(row.get("score"))
    conf = _f(row.get("confidence_score"))
    coverage = _f(row.get("data_coverage_pct"))
    critical = _f(row.get("critical_metric_coverage_pct"))
    reliability = str(row.get("score_reliability") or "").lower()

    if score is None:
        return _insufficient("Score Vestra suprimido por evidência insuficiente")
    if coverage is None or coverage < 55:
        return _insufficient("Cobertura fundamental inferior a 55%")
    if critical is not None and critical < 45:
        return _insufficient("Cobertura de métricas críticas insuficiente")
    if conf is None or conf < 50:
        return _insufficient("Confiança dos dados inferior a 50%")
    if reliability in ("insufficient", "suppressed"):
        return _insufficient("Fiabilidade insuficiente para ranking")

    moat = _f(row.get("moat_score"))
    cap = _f(row.get("capital_allocation_intelligence_score"))
    qarp = _f(row.get("qarp_score"))
    trap = _f(row.get("value_trap_risk_score"))
    sector = _f(row.get("sector_native_score"))
    low52 = _f(row.get("low52_opportunity_score"))
    if low52 is None:
        low52 = _f(row.get("low52_score"))
    recovery = _f(row.get("recovery_score"))
    valuation = _f(row.get("valuation_score"))
    trap_inverse = (100.0 - trap) if trap is not None else None

    components = {
        "vestra_score": score,
        "confidence": conf,
        "moat": moat,
        "capital_allocation": cap,
        "qarp": qarp,
        "value_trap_inverse": trap_inverse,
        "sector_native": sector,
        "low52": low52,
        "recovery": recovery,
        "valuation": valuation,
    }
    observed = [v for v in components.values() if v is not None]
    structural_observed = [v for v in (moat, cap, qarp, trap_inverse, sector) if v is not None]
    if len(observed) < 4:
        return _insufficient("Poucos sinais independentes para ranking", components)
    if len(structural_observed) < 2:
        return _insufficient("Faltam sinais estruturais suficientes", components)

    opp = _weighted([
        (score, .24), (conf, .12), (moat, .13), (cap, .10), (qarp, .16),
        (trap_inverse, .12), (sector, .06), (low52, .04), (recovery, .02), (valuation, .01),
    ])

    gate = str(row.get("risk_gate") or "clear").lower()
    reasons = []
    cautions = []
    if score >= 70:
        reasons.append("Score Vestra elevado")
    if conf >= 70:
        reasons.append("Confiança dos dados robusta")
    if moat is not None and moat >= 70:
        reasons.append("Persistência económica forte")
    if cap is not None and cap >= 70:
        reasons.append("Boa disciplina de capital")
    if qarp is not None and qarp >= 70:
        reasons.append("Qualidade a preço razoável")
    if trap is not None and trap <= 35:
        reasons.append("Baixo risco de value trap")
    if sector is not None and sector >= 70:
        reasons.append("Métricas fortes no modelo setorial")
    if low52 is not None and low52 >= 65:
        reasons.append("Queda de preço com contexto favorável")
    if recovery is not None and recovery >= 65:
        reasons.append("Recuperação com confirmação")

    if trap is not None and trap >= 65:
        cautions.append("Risco elevado de value trap")
    if moat is not None and moat < 40:
        cautions.append("Baixa persistência económica")
    if cap is not None and cap < 40:
        cautions.append("Alocação de capital fraca")
    if gate in ("high", "severe"):
        cautions.append("Risk Gate elevado")
    if coverage < 65:
        cautions.append("Cobertura ainda moderada")

    if opp is not None:
        if gate == "severe":
            opp = min(opp, 35.0)
        elif gate == "high":
            opp = min(opp, 49.0)
        if trap is not None and trap >= 75:
            opp = min(opp, 45.0)
        if coverage < 65 or conf < 60:
            opp = min(opp, 59.0)
        elif coverage < 75 or conf < 70:
            opp = min(opp, 69.0)
        opp = round(_clip(opp), 1)

    if opp is None:
        label = "Dados insuficientes"
    elif opp >= 78 and coverage >= 75 and conf >= 70:
        label = "Prioridade alta"
    elif opp >= 66 and coverage >= 65 and conf >= 60:
        label = "Oportunidade forte"
    elif opp >= 54:
        label = "Interessante"
    elif opp >= 42:
        label = "Acompanhar"
    else:
        label = "Baixa prioridade"

    return {
        "opportunity_score": opp,
        "opportunity_label": label,
        "opportunity_reasons": reasons[:4],
        "opportunity_cautions": cautions[:4],
        "opportunity_components": components,
        "opportunity_eligible": True,
        "opportunity_signal_count": len(observed),
        "opportunity_structural_signal_count": len(structural_observed),
    }
