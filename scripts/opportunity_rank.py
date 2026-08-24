"""Best Opportunities Now overlay with strict evidence and timing gates.

The ranking is intentionally different from a list of the highest-quality
companies. A strong company that has already run hard can be a poor opportunity
*now*. Best Opportunities therefore combines structural quality with an
"early-momentum" timing layer: improving price/expectations/recovery is rewarded,
while obvious short-term overextension is capped.

This is a prioritisation aid, not an investment recommendation. Missing evidence
stays missing and sparse dossiers are never promoted by renormalising a handful
of favourable inputs.
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


def _gate(name, passed, value=None, threshold=None, detail=None):
    out = {"name": name, "passed": bool(passed)}
    if value is not None:
        out["value"] = value
    if threshold is not None:
        out["threshold"] = threshold
    if detail:
        out["detail"] = detail
    return out


def _closes(row):
    out = []
    for item in row.get("price_history_1y") or []:
        try:
            v = item.get("close") if isinstance(item, dict) else item
            v = float(v)
            if v > 0:
                out.append(v)
        except (TypeError, ValueError):
            pass
    return out


def _ret(closes, periods):
    if len(closes) <= periods or closes[-periods - 1] <= 0:
        return None
    return (closes[-1] / closes[-periods - 1] - 1.0) * 100.0


def _band_score(v, bands):
    """Piecewise score using inclusive upper bounds."""
    if v is None:
        return None
    for upper, score in bands:
        if v <= upper:
            return float(score)
    return float(bands[-1][1])


def _timing_assessment(row):
    """Prefer an emerging move, not a move that is already obviously extended.

    Sweet spot:
    - 20d return mildly positive (roughly 1-10%)
    - 60d return positive but not parabolic (roughly 3-25%)
    - some room below the 52-week high, unless fundamentals are clearly improving
    - improving estimates/recovery can confirm the inflection.
    """
    closes = _closes(row)
    if len(closes) < 22:
        return {
            "score": None,
            "label": "Dados de preço insuficientes",
            "reasons": [],
            "cautions": ["Histórico insuficiente para avaliar o timing"],
            "return_20d_pct": None,
            "return_60d_pct": None,
            "drawdown_from_high_pct": None,
            "overextended": False,
            "severely_overextended": False,
        }

    r20 = _ret(closes, 20)
    r60 = _ret(closes, 60)
    high = max(closes)
    dd = (closes[-1] / high - 1.0) * 100.0 if high > 0 else None
    room = abs(dd) if dd is not None else None

    # Reward the start/middle of a move; penalise a parabolic move or a falling knife.
    s20 = _band_score(r20, [(-12, 20), (-5, 38), (0, 58), (4, 86), (10, 92), (16, 72), (24, 48), (10**9, 28)])
    s60 = _band_score(r60, [(-25, 18), (-10, 35), (0, 55), (8, 82), (20, 90), (30, 75), (45, 50), (10**9, 30)]) if r60 is not None else None

    if room is None:
        s_room = None
    elif room < 2:
        s_room = 48.0
    elif room < 5:
        s_room = 62.0
    elif room <= 20:
        s_room = 88.0
    elif room <= 35:
        s_room = 72.0
    elif room <= 50:
        s_room = 48.0
    else:
        s_room = 28.0

    timing = _weighted([(s20, .42), (s60, .36), (s_room, .22)])
    reasons = []
    cautions = []

    est = str(row.get("estimate_signal") or "").lower()
    recovery = str(row.get("recovery_status") or "").lower()
    thesis = str(row.get("thesis_direction") or "").lower()

    if timing is not None:
        if est == "improving":
            timing += 7
            reasons.append("Revisões/expectativas a melhorar")
        elif est == "deteriorating":
            timing -= 9
            cautions.append("Expectativas a deteriorar")
        if recovery == "confirmed":
            timing += 8
            reasons.append("Recuperação confirmada")
        elif recovery == "recovering":
            timing += 5
            reasons.append("Recuperação em curso")
        elif recovery in ("failed", "bounce_only"):
            timing -= 9
            cautions.append("Preço sem confirmação fundamental")
        if thesis == "up":
            timing += 3
        elif thesis == "down":
            timing -= 4

    if r20 is not None and 1 <= r20 <= 10:
        reasons.append("Momentum de 20 dias ainda em zona inicial")
    if r60 is not None and 3 <= r60 <= 25:
        reasons.append("Momentum de 60 dias positivo sem extensão excessiva")
    if room is not None and 5 <= room <= 25:
        reasons.append("Ainda existe margem face ao máximo de 52 semanas")

    overextended = bool(
        (r20 is not None and r20 > 18)
        or (r60 is not None and r60 > 35)
        or (room is not None and room < 2 and r60 is not None and r60 > 20)
    )
    severely_overextended = bool(
        (r20 is not None and r20 > 28)
        or (r60 is not None and r60 > 50)
    )
    if severely_overextended:
        cautions.append("Movimento recente muito esticado")
        if timing is not None:
            timing -= 18
    elif overextended:
        cautions.append("Preço já bastante esticado no curto prazo")
        if timing is not None:
            timing -= 10

    if r20 is not None and r20 < -8:
        cautions.append("Momentum de curto prazo ainda negativo")
    if r60 is not None and r60 < -15:
        cautions.append("Tendência de 60 dias ainda fraca")

    timing = round(_clip(timing), 1) if timing is not None else None
    if timing is None:
        label = "Dados insuficientes"
    elif timing >= 78:
        label = "Momento emergente"
    elif timing >= 64:
        label = "Momento favorável"
    elif timing >= 50:
        label = "Timing neutro"
    elif overextended:
        label = "Preço esticado"
    else:
        label = "Timing fraco"

    return {
        "score": timing,
        "label": label,
        "reasons": reasons[:4],
        "cautions": cautions[:4],
        "return_20d_pct": round(r20, 2) if r20 is not None else None,
        "return_60d_pct": round(r60, 2) if r60 is not None else None,
        "drawdown_from_high_pct": round(dd, 2) if dd is not None else None,
        "overextended": overextended,
        "severely_overextended": severely_overextended,
    }


def _insufficient(reason, components=None, gates=None, timing=None):
    out = {
        "opportunity_score": None,
        "opportunity_score_raw": None,
        "opportunity_label": "Dados insuficientes",
        "opportunity_reasons": [],
        "opportunity_cautions": [reason],
        "opportunity_components": components or {},
        "opportunity_eligible": False,
        "opportunity_suppressed_reason": reason,
        "opportunity_gates": gates or [],
        "opportunity_caps": [],
    }
    if timing:
        out.update({
            "opportunity_timing_score": timing.get("score"),
            "opportunity_timing_label": timing.get("label"),
            "opportunity_timing_reasons": timing.get("reasons", []),
            "opportunity_timing_cautions": timing.get("cautions", []),
            "opportunity_return_20d_pct": timing.get("return_20d_pct"),
            "opportunity_return_60d_pct": timing.get("return_60d_pct"),
            "opportunity_drawdown_from_high_pct": timing.get("drawdown_from_high_pct"),
            "opportunity_overextended": timing.get("overextended", False),
        })
    return out


def assess(row: dict) -> dict:
    quote_type = str(row.get("quote_type") or "").upper()
    if quote_type in ("ETF", "CRYPTO", "MUTUALFUND"):
        return _insufficient("Instrumento fora do ranking de ações", gates=[
            _gate("equity", False, detail="Apenas ações entram no Best Opportunities")
        ])

    score = _f(row.get("score"))
    conf = _f(row.get("confidence_score"))
    coverage = _f(row.get("data_coverage_pct"))
    critical = _f(row.get("critical_metric_coverage_pct"))
    reliability = str(row.get("score_reliability") or "").lower()
    timing = _timing_assessment(row)
    timing_score = timing.get("score")

    gates = [
        _gate("score_available", score is not None, value=score, detail="Score Vestra não pode estar suprimido"),
        _gate("coverage", coverage is not None and coverage >= 55, value=coverage, threshold=55),
        _gate("critical_coverage", critical is None or critical >= 45, value=critical, threshold=45),
        _gate("confidence", conf is not None and conf >= 50, value=conf, threshold=50),
        _gate("reliability", reliability not in ("insufficient", "suppressed"), detail=reliability or "unspecified"),
        _gate("timing_available", timing_score is not None, value=timing_score, detail="Best Opportunities Now exige histórico de preço suficiente"),
    ]

    if score is None:
        return _insufficient("Score Vestra suprimido por evidência insuficiente", gates=gates, timing=timing)
    if coverage is None or coverage < 55:
        return _insufficient("Cobertura fundamental inferior a 55%", gates=gates, timing=timing)
    if critical is not None and critical < 45:
        return _insufficient("Cobertura de métricas críticas insuficiente", gates=gates, timing=timing)
    if conf is None or conf < 50:
        return _insufficient("Confiança dos dados inferior a 50%", gates=gates, timing=timing)
    if reliability in ("insufficient", "suppressed"):
        return _insufficient("Fiabilidade insuficiente para ranking", gates=gates, timing=timing)
    if timing_score is None:
        return _insufficient("Histórico de preço insuficiente para avaliar o momento", gates=gates, timing=timing)

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
        "timing": timing_score,
    }
    observed = [v for v in components.values() if v is not None]
    structural_observed = [v for v in (moat, cap, qarp, trap_inverse, sector) if v is not None]
    gates.extend([
        _gate("independent_signals", len(observed) >= 5, value=len(observed), threshold=5),
        _gate("structural_signals", len(structural_observed) >= 2, value=len(structural_observed), threshold=2),
    ])
    if len(observed) < 5:
        return _insufficient("Poucos sinais independentes para ranking", components, gates, timing)
    if len(structural_observed) < 2:
        return _insufficient("Faltam sinais estruturais suficientes", components, gates, timing)

    # Structural quality remains the foundation, but timing now has enough weight
    # to distinguish "great company" from "good opportunity now".
    raw = _weighted([
        (score, .19), (conf, .09), (moat, .11), (cap, .08), (qarp, .14),
        (trap_inverse, .10), (sector, .05), (low52, .05), (recovery, .07),
        (valuation, .02), (timing_score, .20),
    ])

    gate = str(row.get("risk_gate") or "clear").lower()
    reasons = list(timing.get("reasons") or [])
    cautions = list(timing.get("cautions") or [])
    caps = []
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

    opp = raw
    if opp is not None:
        if gate == "severe":
            if opp > 35:
                caps.append({"reason": "Risk Gate severe", "cap": 35.0})
            opp = min(opp, 35.0)
        elif gate == "high":
            if opp > 49:
                caps.append({"reason": "Risk Gate high", "cap": 49.0})
            opp = min(opp, 49.0)
        if trap is not None and trap >= 75:
            if opp > 45:
                caps.append({"reason": "Value-trap risk elevado", "cap": 45.0})
            opp = min(opp, 45.0)
        if timing.get("severely_overextended"):
            if opp > 49:
                caps.append({"reason": "Preço muito esticado", "cap": 49.0})
            opp = min(opp, 49.0)
        elif timing.get("overextended"):
            if opp > 59:
                caps.append({"reason": "Preço já esticado", "cap": 59.0})
            opp = min(opp, 59.0)
        elif timing_score < 40:
            if opp > 59:
                caps.append({"reason": "Timing fraco", "cap": 59.0})
            opp = min(opp, 59.0)
        if coverage < 65 or conf < 60:
            if opp > 59:
                caps.append({"reason": "Evidência apenas mínima", "cap": 59.0})
            opp = min(opp, 59.0)
        elif coverage < 75 or conf < 70:
            if opp > 69:
                caps.append({"reason": "Evidência moderada", "cap": 69.0})
            opp = min(opp, 69.0)
        opp = round(_clip(opp), 1)

    if opp is None:
        label = "Dados insuficientes"
    elif opp >= 78 and coverage >= 75 and conf >= 70 and timing_score >= 65:
        label = "Prioridade alta"
    elif opp >= 66 and coverage >= 65 and conf >= 60 and timing_score >= 55:
        label = "Oportunidade forte"
    elif opp >= 54:
        label = "Interessante"
    elif opp >= 42:
        label = "Acompanhar"
    else:
        label = "Baixa prioridade"

    return {
        "opportunity_score": opp,
        "opportunity_score_raw": round(_clip(raw), 1) if raw is not None else None,
        "opportunity_label": label,
        "opportunity_reasons": reasons[:5],
        "opportunity_cautions": cautions[:5],
        "opportunity_components": components,
        "opportunity_eligible": True,
        "opportunity_signal_count": len(observed),
        "opportunity_structural_signal_count": len(structural_observed),
        "opportunity_gates": gates,
        "opportunity_caps": caps,
        "opportunity_timing_score": timing_score,
        "opportunity_timing_label": timing.get("label"),
        "opportunity_timing_reasons": timing.get("reasons", []),
        "opportunity_timing_cautions": timing.get("cautions", []),
        "opportunity_return_20d_pct": timing.get("return_20d_pct"),
        "opportunity_return_60d_pct": timing.get("return_60d_pct"),
        "opportunity_drawdown_from_high_pct": timing.get("drawdown_from_high_pct"),
        "opportunity_overextended": timing.get("overextended", False),
    }
