"""Vestra v4.4 valuation engine.

Produces an explainable fair-value RANGE, not a point target. The engine uses
observable peer-relative anchors already present in the Vestra dataset and
refuses to fabricate a value when the underlying economics do not support one.

Supported anchors:
- trailing P/E vs same-sector median;
- forward P/E vs same-sector median;
- P/B vs same-sector median;
- FCF yield vs same-sector median;
- dividend yield vs same-sector median for utilities/income-heavy models.

The result is deliberately separate from analyst price targets. Structural-risk
flags can make a numerical range non-actionable even when the stock looks cheap.
"""
from __future__ import annotations

import statistics


def _n(v):
    try:
        x=float(v)
        return x if x == x and x not in (float('inf'), float('-inf')) else None
    except (TypeError, ValueError):
        return None


def _implied_by_multiple(price, current_multiple, peer_multiple):
    p=_n(price); cur=_n(current_multiple); peer=_n(peer_multiple)
    if p is None or p <= 0 or cur is None or cur <= 0 or peer is None or peer <= 0:
        return None
    value=p * (peer / cur)
    if value <= 0 or value > p * 5.0:
        return None
    return value


def _implied_by_yield(price, current_yield, peer_yield):
    p=_n(price); cur=_n(current_yield); peer=_n(peer_yield)
    if p is None or p <= 0 or cur is None or cur <= 0 or peer is None or peer <= 0:
        return None
    value=p * (cur / peer)
    if value <= 0 or value > p * 5.0:
        return None
    return value


def assess(row: dict) -> dict:
    price=_n(row.get('current_price'))
    model=str(row.get('score_model') or 'general')
    if price is None or price <= 0 or row.get('quote_type') in ('ETF','CRYPTO'):
        return {
            'valuation_model': model,
            'fair_value_low': None, 'fair_value_mid': None, 'fair_value_high': None,
            'fair_value_upside_pct': None, 'margin_of_safety_pct': None,
            'valuation_signal': 'insufficient', 'valuation_confidence': 'low',
            'valuation_methods': [],
            'valuation_note': 'Dados insuficientes para uma faixa de fair value explicável.'
        }

    methods=[]
    def add(name, value, weight=1.0):
        value=_n(value)
        if value is not None and value > 0:
            methods.append({'method':name,'fair_value':round(value,4),'weight':weight})

    if model in ('bank','insurance'):
        add('P/B vs setor', _implied_by_multiple(price,row.get('price_to_book'),row.get('sector_pb_median')), 1.6)
        add('P/E vs setor', _implied_by_multiple(price,row.get('trailing_pe'),row.get('sector_trailing_pe_median')), 0.8)
        add('Forward P/E vs setor', _implied_by_multiple(price,row.get('forward_pe'),row.get('sector_forward_pe_median')), 0.8)
    elif model == 'reit':
        add('P/B vs setor', _implied_by_multiple(price,row.get('price_to_book'),row.get('sector_pb_median')), 1.0)
        add('P/E vs setor (proxy)', _implied_by_multiple(price,row.get('trailing_pe'),row.get('sector_trailing_pe_median')), 0.6)
        add('Dividend yield vs setor', _implied_by_yield(price,row.get('dividend_yield'),row.get('sector_dividend_yield_median')), 0.8)
    elif model == 'utility':
        add('Forward P/E vs setor', _implied_by_multiple(price,row.get('forward_pe'),row.get('sector_forward_pe_median')), 1.2)
        add('P/E vs setor', _implied_by_multiple(price,row.get('trailing_pe'),row.get('sector_trailing_pe_median')), 1.0)
        add('Dividend yield vs setor', _implied_by_yield(price,row.get('dividend_yield'),row.get('sector_dividend_yield_median')), 1.2)
        add('FCF yield vs setor', _implied_by_yield(price,row.get('fcf_yield'),row.get('sector_fcf_yield_median')), 0.8)
    elif model == 'energy':
        add('P/E vs setor', _implied_by_multiple(price,row.get('trailing_pe'),row.get('sector_trailing_pe_median')), 0.9)
        add('Forward P/E vs setor', _implied_by_multiple(price,row.get('forward_pe'),row.get('sector_forward_pe_median')), 0.9)
        add('FCF yield vs setor', _implied_by_yield(price,row.get('fcf_yield'),row.get('sector_fcf_yield_median')), 1.4)
    elif model == 'biotech':
        add('Forward P/E vs setor', _implied_by_multiple(price,row.get('forward_pe'),row.get('sector_forward_pe_median')), 0.7)
        add('P/B vs setor (proxy)', _implied_by_multiple(price,row.get('price_to_book'),row.get('sector_pb_median')), 0.5)
    elif model == 'growth_tech':
        add('Forward P/E vs setor', _implied_by_multiple(price,row.get('forward_pe'),row.get('sector_forward_pe_median')), 1.5)
        add('P/E vs setor', _implied_by_multiple(price,row.get('trailing_pe'),row.get('sector_trailing_pe_median')), 0.8)
        add('FCF yield vs setor', _implied_by_yield(price,row.get('fcf_yield'),row.get('sector_fcf_yield_median')), 1.0)
    else:
        add('Forward P/E vs setor', _implied_by_multiple(price,row.get('forward_pe'),row.get('sector_forward_pe_median')), 1.1)
        add('P/E vs setor', _implied_by_multiple(price,row.get('trailing_pe'),row.get('sector_trailing_pe_median')), 1.0)
        add('P/B vs setor', _implied_by_multiple(price,row.get('price_to_book'),row.get('sector_pb_median')), 0.6)
        add('FCF yield vs setor', _implied_by_yield(price,row.get('fcf_yield'),row.get('sector_fcf_yield_median')), 1.1)

    if not methods:
        return {
            'valuation_model': model,
            'fair_value_low': None, 'fair_value_mid': None, 'fair_value_high': None,
            'fair_value_upside_pct': None, 'margin_of_safety_pct': None,
            'valuation_signal': 'insufficient', 'valuation_confidence': 'low',
            'valuation_methods': [],
            'valuation_note': ('Biotech sem earnings/FCF comparáveis: valuation genérico não é fiável.' if model=='biotech'
                               else 'Sem múltiplos/yields comparáveis suficientes para estimar fair value.')
        }

    vals=[m['fair_value'] for m in methods]
    wsum=sum(m['weight'] for m in methods)
    weighted=sum(m['fair_value']*m['weight'] for m in methods)/wsum
    median=statistics.median(vals)
    mid=(weighted+median)/2.0

    quality=_n(row.get('quality_pct')); growth=_n(row.get('growth_pct'))
    adj=0.0
    if model in ('general','growth_tech'):
        if quality is not None: adj += (quality-50.0)/50.0 * 0.05
        if growth is not None: adj += (growth-50.0)/50.0 * 0.07
        adj=max(-0.12,min(0.12,adj))
        mid *= (1.0+adj)

    dispersion=(max(vals)-min(vals))/max(mid,1e-9) if len(vals)>=2 else 0.0
    base_band=0.12 if len(vals)>=2 else 0.18
    band=min(0.28,max(base_band,dispersion/2.0))
    low=mid*(1.0-band); high=mid*(1.0+band)

    upside=(mid/price-1.0)*100.0
    mos=(low/price-1.0)*100.0
    conf_score=_n(row.get('confidence_score'))
    confidence_missing=conf_score is None
    risk_gate=str(row.get('risk_gate') or 'clear')
    if risk_gate in ('high','severe') or confidence_missing or conf_score < 50:
        signal='uncertain'
    elif upside >= 25:
        signal='undervalued'
    elif upside <= -20:
        signal='overvalued'
    else:
        signal='fair'

    if conf_score is not None and len(methods)>=3 and conf_score>=75 and dispersion<=0.35:
        vconf='high'
    elif conf_score is not None and len(methods)>=2 and conf_score>=55:
        vconf='medium'
    else:
        vconf='low'
    if risk_gate in ('high','severe'):
        vconf='low'

    note='Faixa peer-relative; não é DCF nem target de analistas.'
    if risk_gate in ('high','severe'):
        note='Faixa numérica não acionável enquanto persistirem riscos estruturais materiais.'
    elif confidence_missing:
        note='Faixa peer-relative disponível, mas confiança global ausente; interpretação conservadora.'
    elif model=='reit':
        note='Proxy peer-relative; AFFO/NAV não são inferidos quando não existem dados próprios.'
    elif model=='biotech':
        note='Biotech: faixa apenas quando existem âncoras contabilísticas comparáveis; pipeline/catalysts continuam essenciais.'

    return {
        'valuation_model': model,
        'fair_value_low': round(low,4), 'fair_value_mid': round(mid,4), 'fair_value_high': round(high,4),
        'fair_value_upside_pct': round(upside,1), 'margin_of_safety_pct': round(mos,1),
        'valuation_signal': signal, 'valuation_confidence': vconf,
        'valuation_methods': methods,
        'valuation_note': note,
    }
