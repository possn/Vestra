"""Best Opportunities Now overlay.

Combines independent Vestra signals into an explainable opportunity score.
This is a prioritisation/ranking aid, not an investment recommendation. Missing
signals are excluded rather than imputed.
"""
from __future__ import annotations


def _f(v):
    try:
        x=float(v)
        return x if x==x and abs(x)!=float('inf') else None
    except (TypeError, ValueError):
        return None


def _clip(x):
    return max(0.0,min(100.0,x))


def _weighted(parts):
    vals=[(v,w) for v,w in parts if v is not None]
    if not vals: return None
    den=sum(w for _,w in vals)
    return sum(v*w for v,w in vals)/den if den else None


def assess(row: dict) -> dict:
    score=_f(row.get('score'))
    conf=_f(row.get('confidence_score'))
    moat=_f(row.get('moat_score'))
    cap=_f(row.get('capital_allocation_intelligence_score'))
    qarp=_f(row.get('qarp_score'))
    trap=_f(row.get('value_trap_risk_score'))
    sector=_f(row.get('sector_native_score'))
    low52=_f(row.get('low52_opportunity_score'))
    recovery=_f(row.get('recovery_score'))
    valuation=_f(row.get('valuation_score'))

    trap_inverse=(100.0-trap) if trap is not None else None
    opp=_weighted([
        (score,.24),(conf,.12),(moat,.13),(cap,.10),(qarp,.16),
        (trap_inverse,.12),(sector,.06),(low52,.04),(recovery,.02),(valuation,.01)
    ])

    gate=str(row.get('risk_gate') or 'clear').lower()
    reasons=[]; cautions=[]
    if score is not None and score>=70: reasons.append('Score Vestra elevado')
    if conf is not None and conf>=70: reasons.append('Confiança dos dados robusta')
    if moat is not None and moat>=70: reasons.append('Persistência económica forte')
    if cap is not None and cap>=70: reasons.append('Boa disciplina de capital')
    if qarp is not None and qarp>=70: reasons.append('Qualidade a preço razoável')
    if trap is not None and trap<=35: reasons.append('Baixo risco de value trap')
    if sector is not None and sector>=70: reasons.append('Métricas fortes no modelo setorial')
    if low52 is not None and low52>=65: reasons.append('Queda de preço com contexto favorável')
    if recovery is not None and recovery>=65: reasons.append('Recuperação já com sinais de confirmação')

    if trap is not None and trap>=65: cautions.append('Risco elevado de value trap')
    if conf is not None and conf<50: cautions.append('Confiança dos dados limitada')
    if moat is not None and moat<40: cautions.append('Baixa persistência económica')
    if cap is not None and cap<40: cautions.append('Alocação de capital fraca')
    if gate in ('high','severe'): cautions.append('Risk Gate elevado')

    if opp is not None:
        if gate=='severe': opp=min(opp,35.0)
        elif gate=='high': opp=min(opp,49.0)
        if trap is not None and trap>=75: opp=min(opp,45.0)
        if conf is not None and conf<35: opp=min(opp,55.0)
        opp=round(_clip(opp),1)

    if opp is None: label='Dados insuficientes'
    elif opp>=78: label='Prioridade alta'
    elif opp>=66: label='Oportunidade forte'
    elif opp>=54: label='Interessante'
    elif opp>=42: label='Acompanhar'
    else: label='Baixa prioridade'

    return {
        'opportunity_score':opp,
        'opportunity_label':label,
        'opportunity_reasons':reasons[:4],
        'opportunity_cautions':cautions[:4],
        'opportunity_components':{
            'vestra_score':score,'confidence':conf,'moat':moat,'capital_allocation':cap,
            'qarp':qarp,'value_trap_inverse':trap_inverse,'sector_native':sector,
            'low52':low52,'recovery':recovery,'valuation':valuation,
        },
    }
