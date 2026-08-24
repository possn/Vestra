"""Vestra intelligent scanner overlays with strict evidence gating.

Scanner strategies are research overlays. They must never promote a company as
an opportunity when the fundamental dossier is too sparse to support the claim.
The scanner is also the final composition layer for structural intelligence,
which guarantees those overlays are emitted without a second run.py integration.
"""
from __future__ import annotations

from capital_allocation_intelligence import assess as assess_capital_allocation
from moat import assess as assess_moat
from sector_native import assess as assess_sector_native
from value_trap import assess as assess_value_trap
from opportunity_rank import assess as assess_opportunity_rank


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


def _empty(reason=None):
    out = {
        "scanner_tags": [], "scanner_results": {}, "scanner_best": None,
        "scanner_best_score": None, "opportunity_score": None,
        "opportunity_label": "Dados insuficientes", "opportunity_eligible": False,
    }
    if reason:
        out["scanner_suppressed_reason"] = reason
        out["opportunity_suppressed_reason"] = reason
    return out


def _evidence_ok(row):
    score = _n(row.get("score"))
    coverage = _n(row.get("data_coverage_pct"))
    critical = _n(row.get("critical_metric_coverage_pct"))
    confidence = _n(row.get("confidence_score"))
    reliability = str(row.get("score_reliability") or "").lower()
    if score is None:
        return False, "Score Vestra suprimido por dados insuficientes"
    if coverage is None or coverage < 55:
        return False, "Cobertura fundamental inferior a 55%"
    if critical is not None and critical < 45:
        return False, "Cobertura de métricas críticas insuficiente"
    if confidence is None or confidence < 50:
        return False, "Confiança dos dados insuficiente"
    if reliability in ("insufficient", "suppressed"):
        return False, "Fiabilidade insuficiente para ranking"
    return True, None


def _low52(row):
    hist = row.get("price_history_1y") or []
    closes = []
    for x in hist:
        try:
            v = x.get("close") if isinstance(x, dict) else x
            v = float(v)
            if v > 0:
                closes.append(v)
        except Exception:
            pass
    cur = _n(row.get("current_price"))
    if cur is None and closes:
        cur = closes[-1]
    if not closes or cur is None or cur <= 0:
        return None
    low = min(closes)
    return {"low": low, "above_pct": (cur / low - 1) * 100.0}


def _dividend_growth(row):
    hist = row.get("annual_dividend_history") or []
    vals = []
    for item in hist[:6]:
        try:
            v = item.get("value", item.get("dividend", item.get("amount"))) if isinstance(item, dict) else item
            v = float(v)
            if v >= 0:
                vals.append(v)
        except Exception:
            pass
    if len(vals) < 2:
        return None
    comps = [newer / older - 1 for newer, older in zip(vals, vals[1:]) if older > 0]
    return sum(comps) / len(comps) if comps else None


def _structural_overlays(row, base):
    """Compose structural engines in dependency order and return only new fields."""
    working = dict(row)
    working.update(base)
    for fn in (assess_capital_allocation, assess_moat, assess_sector_native, assess_value_trap):
        try:
            extra = fn(working) or {}
            working.update(extra)
        except Exception as exc:
            working.setdefault("structural_intelligence_errors", []).append(type(exc).__name__)
    if working.get("low52_opportunity_score") is None and working.get("low52_score") is not None:
        working["low52_opportunity_score"] = working.get("low52_score")
    try:
        working.update(assess_opportunity_rank(working) or {})
    except Exception as exc:
        working.setdefault("structural_intelligence_errors", []).append(type(exc).__name__)
        working.update({
            "opportunity_score": None,
            "opportunity_label": "Dados insuficientes",
            "opportunity_eligible": False,
            "opportunity_suppressed_reason": "Erro no ranking estrutural",
        })
    return {k: v for k, v in working.items() if k not in row or row.get(k) != v}


def assess(row: dict) -> dict:
    if str(row.get("quote_type") or "").upper() in ("ETF", "CRYPTO", "MUTUALFUND"):
        return _empty()

    ok, reason = _evidence_ok(row)
    if not ok:
        return _empty(reason)

    score = _n(row.get("score")); quality = _n(row.get("quality_pct")); value = _n(row.get("value_pct")); conf = _n(row.get("confidence_score"))
    gate = str(row.get("risk_gate") or "clear").lower(); dilution = _n(row.get("diluted_shares_yoy"))
    margin_delta = _n(row.get("net_margin_yoy_change_pp")); rev_accel = _n(row.get("revenue_yoy_acceleration_pp")); thesis = str(row.get("thesis_direction") or "")
    delta30 = _n(row.get("thesis_score_delta_30d")); valuation = str(row.get("valuation_signal") or ""); mos = _n(row.get("margin_of_safety_pct"))
    est = _n(row.get("estimate_momentum_score")); est_signal = str(row.get("estimate_signal") or ""); buy_count = _n(row.get("insider_buy_count_30d")) or 0
    buy_val = _n(row.get("insider_buy_value_30d")) or 0; sell_val = _n(row.get("insider_sell_value_30d")) or 0
    div_yield = _n(row.get("dividend_yield")); div_cover = _n(row.get("dividend_fcf_coverage")); low52 = _low52(row); div_growth = _dividend_growth(row)
    low52_status = str(row.get("low52_status") or ""); low52_score = _n(row.get("low52_score")); low52_reasons = list(row.get("low52_reasons") or [])
    safe_gate = gate in ("clear", "watch"); results = {}

    def add(key, label, parts, reasons):
        vals = [float(p) for p in parts if p is not None]
        if vals:
            results[key] = {"label": label, "score": round(_clamp(sum(vals) / len(vals)), 1), "reasons": reasons[:4]}

    if safe_gate and (quality or 0) >= 65 and conf >= 60 and score >= 62 and (valuation in ("undervalued", "fair") or (mos is not None and mos >= 8) or (value or 0) >= 60):
        add("qarp", "Quality at a Reasonable Price", [quality, score, conf, value if value is not None else 50, _clamp(50 + (mos or 0))], [f"Qualidade {quality:.0f}/100", f"Score {score:.0f}/100", f"Confiança {conf:.0f}/100", f"Margem de segurança {mos:.0f}%" if mos is not None else "Valuation favorável vs pares"])
    if low52 and low52["above_pct"] <= 15 and low52_status in ("opportunity", "watch") and low52_score is not None and conf >= 60:
        add("fallen_angels", "Fallen Angels", [low52_score, quality, conf, score], low52_reasons or [f"{max(0, low52['above_pct']):.1f}% acima do mínimo 52s", "Fundamentos com evidência suficiente"])
    if low52 and low52["above_pct"] <= 5 and low52_status == "opportunity" and low52_score is not None and conf >= 65:
        add("lows_intact", "Mínimos 52s · fundamentos intactos", [low52_score, quality, conf, score], low52_reasons or [f"{max(0, low52['above_pct']):.1f}% acima do mínimo 52s", "Risk Gate sem alerta alto/severo"])
    if est_signal == "improving" and (est or 0) >= 65 and conf >= 55 and gate not in ("high", "severe"):
        breadth = _n(row.get("estimate_revision_breadth_pct"))
        add("positive_revisions", "Revisões positivas", [est, breadth, conf], [f"Momentum de expectativas {est:.0f}/100", f"Breadth {breadth:.0f}%" if breadth is not None else "Revisões de EPS a subir", f"Confiança {conf:.0f}/100"])
    if conf >= 55 and gate not in ("high", "severe") and buy_count >= 1 and buy_val > sell_val and (buy_count >= 2 or buy_val >= 100000):
        add("insider_accumulation", "Insider Accumulation", [_clamp(45 + buy_count * 8 + min(30, buy_val / 100000)), conf, score], [f"{int(buy_count)} compras open-market", f"Compras líquidas ~{buy_val-sell_val:,.0f} USD", f"Score {score:.0f}/100"])
    turnaround_signal = (delta30 is not None and delta30 >= 3) or ((rev_accel or 0) >= 5 and (margin_delta or 0) >= 1)
    if turnaround_signal and gate != "severe" and conf >= 55 and score >= 45 and thesis != "down":
        add("turnarounds", "Turnarounds", [_clamp(55 + (delta30 or 0) * 3 + (rev_accel or 0) * 0.5 + (margin_delta or 0) * 3), conf, score], [f"Δ score 30d +{delta30:.1f}" if delta30 is not None else "Execução a acelerar", f"Aceleração receita {rev_accel:+.1f} pp" if rev_accel is not None else "Receita a melhorar", f"Margem {margin_delta:+.1f} pp" if margin_delta is not None else "Margens estabilizadas"])
    if div_yield is not None and div_yield > 0 and safe_gate and (quality or 0) >= 55 and conf >= 55 and (dilution is None or dilution <= 0.05) and (div_cover is None or div_cover >= 1.0) and (div_growth is None or div_growth >= 0):
        add("dividend_growers", "Dividend Growers", [quality, conf, _clamp(50 + (div_growth or 0) * 200), _clamp(45 + div_yield * 700), score], [f"Dividend yield {div_yield*100:.1f}%", f"Qualidade {quality:.0f}/100", f"Cobertura FCF {div_cover:.2f}×" if div_cover is not None else "Sem sinal de payout descoberto", "Sem diluição material"])

    ordered = sorted(results.items(), key=lambda kv: kv[1]["score"], reverse=True)
    base = {
        "scanner_tags": [k for k, _ in ordered],
        "scanner_results": dict(ordered),
        "scanner_best": ordered[0][0] if ordered else None,
        "scanner_best_score": ordered[0][1]["score"] if ordered else None,
    }
    base.update(_structural_overlays(row, base))

    # Expose the structural ranking through the same scanner contract consumed by
    # market.js. This avoids a second frontend-specific data path and keeps all
    # opportunity surfaces under the same evidence gate.
    opp = _n(base.get("opportunity_score"))
    if opp is not None and bool(base.get("opportunity_eligible")):
        reasons = list(base.get("opportunity_reasons") or [])
        cautions = list(base.get("opportunity_cautions") or [])
        scanner_results = dict(base.get("scanner_results") or {})
        scanner_results["best_opportunities"] = {
            "label": base.get("opportunity_label") or "Best Opportunities",
            "score": round(opp, 1),
            "reasons": (reasons + [f"Atenção: {x}" for x in cautions])[:4],
        }
        tags = ["best_opportunities"] + [x for x in (base.get("scanner_tags") or []) if x != "best_opportunities"]
        base["scanner_results"] = scanner_results
        base["scanner_tags"] = tags
        base["scanner_best"] = "best_opportunities"
        base["scanner_best_score"] = round(opp, 1)
    return base
