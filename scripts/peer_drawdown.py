from __future__ import annotations
from statistics import median

def _return_1y(row):
    hist=row.get('price_history_1y') or []
    closes=[]
    for item in hist:
        try:
            v=item.get('close') if isinstance(item,dict) else item
            v=float(v)
            if v>0: closes.append(v)
        except Exception: pass
    if len(closes)<12 or closes[0]<=0: return None
    return (closes[-1]/closes[0]-1.0)*100.0

def assess_universe(rows):
    sector_returns={}; own={}
    for row in rows:
        if str(row.get('quote_type') or '').upper() in ('ETF','CRYPTO','MUTUALFUND'): continue
        sector=str(row.get('sector') or '').strip(); ret=_return_1y(row); ticker=str(row.get('ticker') or '')
        if sector and ret is not None:
            sector_returns.setdefault(sector,[]).append(ret); own[ticker]=ret
    medians={s:median(v) for s,v in sector_returns.items() if len(v)>=4}
    for row in rows:
        ticker=str(row.get('ticker') or ''); sector=str(row.get('sector') or '').strip(); r=own.get(ticker); peer=medians.get(sector); count=len(sector_returns.get(sector,[]))
        row['sector_relative_peer_count']=count
        if r is None or peer is None:
            row['sector_relative_return_1y_pct']=None; row['sector_median_return_1y_pct']=None; row['sector_relative_drawdown_label']='Sem comparação setorial suficiente'; continue
        rel=r-peer
        if rel<=-20: label='Queda sobretudo específica da empresa'; tone='idiosyncratic'
        elif rel<=-10: label='Empresa pior que o setor'; tone='underperforming'
        elif rel>=10: label='Empresa melhor que o setor'; tone='outperforming'
        else: label='Movimento próximo do setor'; tone='sector_led'
        row['return_1y_pct']=round(r,2); row['sector_median_return_1y_pct']=round(peer,2); row['sector_relative_return_1y_pct']=round(rel,2); row['sector_relative_drawdown_label']=label; row['sector_relative_drawdown_tone']=tone
    return rows
