"""Sector-native intelligence overlay for Vestra.

This layer does not replace the core score. It summarizes the sector-specific
metrics that are already observed in the row and returns a separate score,
label, components and evidence. Missing metrics stay missing.
"""
from __future__ import annotations


def _f(v):
    try:
        x = float(v)
        return x if x == x and abs(x) != float("inf") else None
    except (TypeError, ValueError):
        return None


def _clip(x):
    return max(0.0, min(100.0, x))


def _avg(values):
    vals = [float(v) for v in values if v is not None]
    return sum(vals) / len(vals) if vals else None


def _score_high(v, good, excellent):
    if v is None:
        return None
    if excellent == good:
        return 50.0
    return _clip((v - good) / (excellent - good) * 50.0 + 50.0)


def _score_low(v, good, poor):
    if v is None:
        return None
    if poor == good:
        return 50.0
    return _clip(100.0 - (v - good) / (poor - good) * 50.0)


def assess(row: dict) -> dict:
    model = str(row.get("score_model") or "general")
    if model == "general":
        return {"sector_native_score": None, "sector_native_label": "Modelo geral", "sector_native_components": {}, "sector_native_reasons": [], "sector_native_risks": []}

    components = {}
    reasons = []
    risks = []

    if model == "bank":
        roe = _f(row.get("roe")); eff = _f(row.get("efficiency_ratio_proxy")); prov = _f(row.get("provision_to_revenue")); cap = _f(row.get("equity_to_assets")); nii = _f(row.get("net_interest_income_yoy"))
        components = {
            "Profitability": _score_high(roe, .08, .18),
            "Efficiency": _score_low(eff, .50, .80),
            "Credit Loss Load": _score_low(prov, .02, .12),
            "Capital Proxy": _score_high(cap, .06, .14),
            "NII Growth": _score_high(nii, 0.0, .15),
        }
        if roe is not None and roe >= .14: reasons.append("ROE robusto")
        if eff is not None and eff <= .55: reasons.append("Boa eficiência operacional")
        if prov is not None and prov >= .08: risks.append("Provisões elevadas face à receita")
    elif model == "reit":
        pffo = _f(row.get("reit_p_ffo_proxy")); lev = _f(row.get("reit_net_debt_to_ebitda")); payout = _f(row.get("reit_ffo_payout_proxy")); ffo = _f(row.get("reit_ffo_per_share_proxy"))
        components = {
            "FFO Quality": _score_high(ffo, 0.0, 5.0),
            "P/FFO": _score_low(pffo, 12.0, 28.0),
            "Leverage": _score_low(lev, 4.0, 8.0),
            "Distribution": _score_low(payout, .65, 1.05),
        }
        if lev is not None and lev <= 5: reasons.append("Leverage controlado para REIT")
        if payout is not None and payout > 1: risks.append("Distribuição acima do FFO proxy")
    elif model == "insurance":
        claims = _f(row.get("insurance_claims_to_revenue")); op = _f(row.get("insurance_operating_ratio_proxy")); cap = _f(row.get("insurance_equity_to_assets")); roe = _f(row.get("roe")); pb = _f(row.get("price_to_book"))
        components = {
            "Underwriting Proxy": _avg([_score_low(claims, .55, .90), _score_low(op, .75, 1.10)]),
            "Capital Proxy": _score_high(cap, .10, .25),
            "ROE": _score_high(roe, .08, .18),
            "P/B": _score_low(pb, 1.2, 3.0),
        }
        if op is not None and op < .9: reasons.append("Operating ratio proxy favorável")
        if claims is not None and claims > .85: risks.append("Carga de sinistros elevada")
    elif model == "utility":
        de = _f(row.get("debt_to_equity")); cov = _f(row.get("interest_coverage")); div = _f(row.get("dividend_yield")); roe = _f(row.get("roe")); beta = _f(row.get("beta"))
        components = {
            "Balance": _avg([_score_low(de, 120, 300), _score_high(cov, 2.0, 6.0)]),
            "Income": _score_high(div, .02, .06),
            "Profitability": _score_high(roe, .07, .16),
            "Stability": _score_low(beta, .7, 1.4),
        }
        if cov is not None and cov < 2: risks.append("Cobertura de juros fraca")
        if div is not None and div >= .04: reasons.append("Rendimento relevante")
    elif model == "energy":
        fcf = _f(row.get("fcf_yield")); roce = _f(row.get("roce_proxy")); de = _f(row.get("debt_to_equity")); ev = _f(row.get("enterprise_to_ebitda"))
        components = {
            "Cash Generation": _score_high(fcf, .03, .12),
            "Capital Efficiency": _score_high(roce, .08, .22),
            "Balance": _score_low(de, 60, 180),
            "EV/EBITDA": _score_low(ev, 6.0, 14.0),
        }
        if fcf is not None and fcf >= .08: reasons.append("FCF yield forte")
        if de is not None and de > 180: risks.append("Leverage elevado")
    elif model == "biotech":
        cash = _f(row.get("net_cash")); cap = _f(row.get("market_cap")); dilution = _f(row.get("diluted_shares_yoy")); growth = _f(row.get("revenue_growth")); fcf = _f(row.get("free_cash_flow")); total_cash = _f(row.get("total_cash"))
        runway = None
        if total_cash is not None and fcf is not None and fcf < 0:
            runway = total_cash / abs(fcf)
        components = {
            "Cash Runway": _score_high(runway, 1.0, 4.0),
            "Net Cash": _score_high((cash / cap) if cash is not None and cap not in (None, 0) else None, 0.0, .6),
            "Dilution Discipline": _score_low(dilution, .02, .20),
            "Operating Progress": _score_high(growth, 0.0, .50),
        }
        if runway is not None and runway < 1.5: risks.append("Runway de caixa curto")
        if dilution is not None and dilution > .10: risks.append("Diluição material")
    elif model == "growth_tech":
        growth = _f(row.get("revenue_growth")); exec_ = _f(row.get("execution_pct")); eq = _f(row.get("earnings_quality_pct")); dilution = _f(row.get("diluted_shares_yoy")); sbc = _f(row.get("sbc_to_revenue")); fpe = _f(row.get("forward_pe"))
        components = {
            "Growth": _score_high(growth, .08, .30),
            "Execution": exec_,
            "Earnings Quality": eq,
            "Dilution": _score_low(dilution, .01, .12),
            "SBC": _score_low(sbc, .03, .15),
            "Forward Valuation": _score_low(fpe, 22.0, 55.0),
        }
        if growth is not None and growth >= .20: reasons.append("Crescimento de receita forte")
        if dilution is not None and dilution > .08: risks.append("Diluição elevada")
        if sbc is not None and sbc > .12: risks.append("SBC elevada")
    else:
        return {"sector_native_score": None, "sector_native_label": model, "sector_native_components": {}, "sector_native_reasons": [], "sector_native_risks": []}

    vals = [v for v in components.values() if v is not None]
    score = round(sum(vals) / len(vals), 1) if vals else None
    if score is None:
        label = "Dados insuficientes"
    elif score >= 75:
        label = "Forte no setor"
    elif score >= 58:
        label = "Acima da média"
    elif score >= 42:
        label = "Misto"
    else:
        label = "Fraco no setor"
    return {
        "sector_native_score": score,
        "sector_native_label": label,
        "sector_native_model": model,
        "sector_native_components": {k: (round(v, 1) if v is not None else None) for k, v in components.items()},
        "sector_native_reasons": reasons[:4],
        "sector_native_risks": risks[:4],
    }
