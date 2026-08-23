"""Value-trap and quality-at-a-reasonable-price overlay.

This module deliberately stays separate from the core Vestra score. It combines
valuation context with observed quality, structural persistence and deterioration
signals. Missing evidence remains missing; no synthetic fundamentals are created.
"""
from __future__ import annotations


def _f(v):
    try:
        x=float(v)
        return x if x==x and abs(x)!=float('inf') else None
    except (TypeError, ValueError):
        return None


def _clip(v, lo=0.0, hi=100.0):
    return max(lo, min(hi, v))


def _avg(vals):
    vals=[float(v) for v in vals if v is not None]
    return sum(vals)/len(vals) if vals else None


def assess(row: dict) -> dict:
    quality=_f(row.get('quality_pct'))
    value=_f(row.get('value_pct'))
    growth=_f(row.get('growth_pct'))
    earnings_quality=_f(row.get('earnings_quality_pct'))
    execution=_f(row.get('execution_pct'))
    moat=_f(row.get('moat_score'))
    capalloc=_f(row.get('capital_allocation_intelligence_score'))
    confidence=_f(row.get('confidence_score'))
    coverage=_f(row.get('data_coverage_pct'))
    rev_growth=_f(row.get('revenue_growth'))
    rev_accel=_f(row.get('revenue_yoy_acceleration_pp'))
    margin_change=_f(row.get('net_margin_yoy_change_pp'))
    eps_accel=_f(row.get('eps_yoy_acceleration_pp'))
    dilution=_f(row.get('diluted_shares_yoy'))
    accrual=_f(row.get('accrual_ratio'))
    fcf_margin=_f(row.get('fcf_margin'))
    rel_pe=_f(row.get('trailing_pe_vs_sector_pct'))
    rel_fpe=_f(row.get('forward_pe_vs_sector_pct'))
    rel_pb=_f(row.get('pb_vs_sector_pct'))
    rel_ev=_f(row.get('ev_ebitda_vs_sector_pct'))
    risk_gate=str(row.get('risk_gate') or 'clear').lower()
    risk_flags=list(row.get('risk_flags') or [])

    valuation_discount=[]
    for x in (rel_pe, rel_fpe, rel_pb, rel_ev):
        if x is not None:
            valuation_discount.append(_clip(50 - x*0.65))
    relative_value=_avg(valuation_discount)
    if relative_value is None:
        relative_value=value

    structural_quality=_avg([quality, earnings_quality, moat, capalloc])
    operating_trend=_avg([growth, execution])

    deterioration=0.0
    red_flags=[]
    positives=[]

    if rev_growth is not None and rev_growth < -0.10:
        deterioration += 18; red_flags.append('Receita em contração')
    if rev_accel is not None and rev_accel < -10:
        deterioration += 12; red_flags.append('Crescimento da receita a desacelerar')
    if margin_change is not None and margin_change < -3:
        deterioration += 14; red_flags.append('Margens em deterioração')
    if eps_accel is not None and eps_accel < -15:
        deterioration += 10; red_flags.append('EPS a perder momentum')
    if dilution is not None and dilution > .08:
        deterioration += 14; red_flags.append('Diluição relevante')
    if accrual is not None and accrual > .08:
        deterioration += 10; red_flags.append('Accruals elevados')
    if fcf_margin is not None and fcf_margin < 0:
        deterioration += 12; red_flags.append('FCF negativo face à receita')
    if risk_gate in ('high','severe'):
        deterioration += 22 if risk_gate=='high' else 35
        red_flags.append('Risk Gate estrutural elevado')
    if any(x in risk_flags for x in ('zombie_interest_coverage','severe_dilution','revenue_contraction')):
        deterioration += 14

    if relative_value is not None and relative_value >= 65:
        positives.append('Valuation atrativo face aos pares')
    if structural_quality is not None and structural_quality >= 70:
        positives.append('Qualidade estrutural elevada')
    if moat is not None and moat >= 70:
        positives.append('Persistência económica favorável')
    if capalloc is not None and capalloc >= 70:
        positives.append('Boa disciplina de capital')
    if operating_trend is not None and operating_trend >= 65:
        positives.append('Tendência operacional favorável')

    trap_risk=None
    if relative_value is not None:
        # Cheapness only becomes a trap signal when accompanied by weak or
        # deteriorating economics. Cheap + strong quality is not penalised.
        cheapness=_clip(relative_value)
        weak_quality=100-_clip(structural_quality if structural_quality is not None else 50)
        weak_trend=100-_clip(operating_trend if operating_trend is not None else 50)
        trap_risk=_clip(cheapness*.35 + weak_quality*.28 + weak_trend*.17 + _clip(deterioration)*.20)
        if structural_quality is not None and structural_quality >= 75:
            trap_risk=max(0.0, trap_risk-18)
        if risk_gate=='severe':
            trap_risk=max(trap_risk,80)
        elif risk_gate=='high':
            trap_risk=max(trap_risk,68)
        trap_risk=round(trap_risk,1)

    qarp=None
    qarp_parts=[]
    if structural_quality is not None: qarp_parts.append((structural_quality,.42))
    if operating_trend is not None: qarp_parts.append((operating_trend,.18))
    if relative_value is not None: qarp_parts.append((relative_value,.30))
    if confidence is not None: qarp_parts.append((confidence,.10))
    elif coverage is not None: qarp_parts.append((coverage,.10))
    if qarp_parts:
        qarp=sum(v*w for v,w in qarp_parts)/sum(w for _,w in qarp_parts)
        qarp=max(0.0, qarp-min(30.0,deterioration*.35))
        if risk_gate=='severe': qarp=min(qarp,35)
        elif risk_gate=='high': qarp=min(qarp,49)
        qarp=round(_clip(qarp),1)

    if trap_risk is None:
        trap_label='Dados insuficientes'
    elif trap_risk >= 75:
        trap_label='Value trap provável'
    elif trap_risk >= 58:
        trap_label='Risco elevado'
    elif trap_risk >= 40:
        trap_label='A vigiar'
    else:
        trap_label='Baixo risco de trap'

    if qarp is None:
        qarp_label='Dados insuficientes'
    elif qarp >= 75:
        qarp_label='QARP forte'
    elif qarp >= 60:
        qarp_label='QARP interessante'
    elif qarp >= 45:
        qarp_label='Neutro'
    else:
        qarp_label='Qualidade/preço fraca'

    return {
        'value_trap_risk_score': trap_risk,
        'value_trap_label': trap_label,
        'qarp_score': qarp,
        'qarp_label': qarp_label,
        'value_trap_reasons': red_flags[:5],
        'qarp_reasons': positives[:5],
        'value_trap_components': {
            'relative_value': round(relative_value,1) if relative_value is not None else None,
            'structural_quality': round(structural_quality,1) if structural_quality is not None else None,
            'operating_trend': round(operating_trend,1) if operating_trend is not None else None,
            'deterioration': round(_clip(deterioration),1),
        },
    }
