"""Vestra v4.6 — capital allocation intelligence overlay.

Uses observed/accounting-derived fields only. Missing metrics remain missing.
"""
from __future__ import annotations


def _f(v):
    try:
        x=float(v)
        return x if x==x and abs(x)!=float('inf') else None
    except (TypeError, ValueError):
        return None


def _clip(x, lo=0.0, hi=100.0):
    return max(lo, min(hi, x))


def assess(row: dict) -> dict:
    dilution=_f(row.get('diluted_shares_yoy'))
    buybacks=_f(row.get('repurchases_last_quarter'))
    roce=_f(row.get('roce_proxy'))
    sector_roce=_f(row.get('sector_roce_proxy_median'))
    div_cover=_f(row.get('dividend_fcf_coverage'))
    sbc_ratio=_f(row.get('sbc_to_revenue'))
    hist=row.get('annual_quality_history') if isinstance(row.get('annual_quality_history'), list) else []
    parts=[]; reasons=[]; risks=[]

    dilution_score=None
    if dilution is not None:
        dilution_score=_clip(80-dilution*500)
        parts.append((dilution_score,.30))
        if dilution<=-.01: reasons.append('Redução líquida do número de ações')
        elif dilution>=.10: risks.append('Diluição material do acionista')
        elif dilution>=.03: risks.append('Número de ações em crescimento')

    roce_score=None
    if roce is not None:
        if sector_roce not in (None,0):
            rel=roce/abs(sector_roce); roce_score=_clip(50+(rel-1)*35)
            if rel>=1.25: reasons.append('ROCE acima da mediana do setor')
            elif rel<.75: risks.append('ROCE abaixo da mediana do setor')
        else: roce_score=_clip(50+roce*180)
        parts.append((roce_score,.25))

    cover_score=None
    if div_cover is not None:
        cover_score=_clip((div_cover-.5)/1.5*100); parts.append((cover_score,.18))
        if div_cover>=1.5: reasons.append('Dividendos bem cobertos pelo FCF')
        elif div_cover<1: risks.append('Dividendos sem cobertura confortável de FCF')

    buyback_score=None
    if buybacks is not None:
        buyback_score=75.0 if buybacks>0 else 45.0; parts.append((buyback_score,.07))
        if buybacks>0 and (dilution is None or dilution<=0): reasons.append('Buybacks traduzem-se em redução/estabilidade de ações')

    sbc_score=None
    if sbc_ratio is not None:
        sbc_score=_clip(100-sbc_ratio*500); parts.append((sbc_score,.12))
        if sbc_ratio>=.10: risks.append('SBC elevada face à receita')
        elif sbc_ratio<=.02: reasons.append('SBC contida face à receita')

    roces=[_f(x.get('roce_proxy')) for x in hist[:4] if isinstance(x,dict)]
    roces=[x for x in roces if x is not None]
    persistence=None
    if len(roces)>=3:
        positive=sum(1 for x in roces if x>0)/len(roces)
        spread=max(roces)-min(roces); base=max(abs(sum(roces)/len(roces)),.05)
        stability=_clip(100-(spread/base)*28)
        persistence=_clip(positive*55+stability*.45); parts.append((persistence,.08))
        if persistence>=75: reasons.append('ROCE consistente em vários anos')
        elif persistence<45: risks.append('ROCE pouco consistente historicamente')

    if parts:
        score=round(_clip(sum(v*w for v,w in parts)/sum(w for _,w in parts)),1)
        label='Disciplinada' if score>=75 else 'Razoável' if score>=55 else 'Fraca' if score<40 else 'A vigiar'
    else:
        score=None; label='Dados insuficientes'
    if buybacks and dilution is not None and dilution>.03:
        risks.append('Buybacks não compensam a diluição líquida')
        if score is not None: score=round(min(score,54.0),1)
        label='A vigiar'

    return {
        'capital_allocation_intelligence_score':score,
        'capital_allocation_intelligence_label':label,
        'capital_allocation_reasons':reasons[:4],
        'capital_allocation_risks':risks[:4],
        'capital_allocation_components':{
            'dilution_discipline':round(dilution_score,1) if dilution_score is not None else None,
            'roce_efficiency':round(roce_score,1) if roce_score is not None else None,
            'dividend_fcf_coverage':round(cover_score,1) if cover_score is not None else None,
            'buyback_quality':round(buyback_score,1) if buyback_score is not None else None,
            'sbc_discipline':round(sbc_score,1) if sbc_score is not None else None,
            'roce_persistence':round(persistence,1) if persistence is not None else None,
        },
    }
