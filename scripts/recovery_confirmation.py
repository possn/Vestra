from __future__ import annotations

def _n(v):
    try:
        if v is None or v == '': return None
        x=float(v); return x if x==x else None
    except Exception: return None

def _closes(row):
    out=[]
    for item in row.get('price_history_1y') or []:
        try:
            v=item.get('close') if isinstance(item,dict) else item
            v=float(v)
            if v>0: out.append(v)
        except Exception: pass
    return out

def _ret(c,d):
    return ((c[-1]/c[-d-1]-1)*100) if len(c)>d and c[-d-1]>0 else None

def assess(row):
    if str(row.get('quote_type') or '').upper() in ('ETF','CRYPTO','MUTUALFUND'): return {}
    c=_closes(row)
    if len(c)<22: return {'recovery_status':'insufficient','recovery_label':'Dados insuficientes','recovery_score':None}
    r20=_ret(c,20); r60=_ret(c,60)
    est=str(row.get('estimate_signal') or '').lower(); driver=str(row.get('drawdown_driver_trend') or 'stable').lower()
    rev=_n(row.get('revenue_yoy_acceleration_pp')); margin=_n(row.get('net_margin_yoy_change_pp')); rel=_n(row.get('sector_relative_return_1y_pct'))
    thesis=str(row.get('thesis_direction') or '').lower(); gate=str(row.get('risk_gate') or 'clear').lower()
    price=50+(max(-25,min(25,(r20 or 0)*2)))+(max(-15,min(15,(r60 or 0)*0.8)))
    fund=50; reasons=[]
    if est=='improving': fund+=16; reasons.append('expectativas a melhorar')
    elif est=='deteriorating': fund-=18; reasons.append('expectativas a piorar')
    if rev is not None: fund += 12 if rev>=5 else (-12 if rev<=-8 else 0)
    if margin is not None: fund += 10 if margin>=1 else (-10 if margin<=-3 else 0)
    if thesis=='up': fund+=8
    elif thesis=='down': fund-=8
    if driver=='improving': fund+=12; reasons.append('causa da queda a melhorar')
    elif driver=='deteriorating': fund-=15; reasons.append('causa da queda a piorar')
    if rel is not None: fund += 6 if rel>=5 else (-6 if rel<=-10 else 0)
    price=max(0,min(100,price)); fund=max(0,min(100,fund)); score=max(0,min(100,price*.48+fund*.52))
    if gate in ('high','severe') or row.get('low52_status')=='structural_risk': status='failed'; score=min(score,34)
    elif score>=76 and (r20 or 0)>3 and driver!='deteriorating' and est!='deteriorating': status='confirmed'
    elif score>=64 and (r20 or 0)>0: status='recovering'
    elif score>=52: status='stabilizing'
    elif (r20 or 0)>3 and fund<45: status='bounce_only'
    else: status='unconfirmed'
    labels={'confirmed':'Recuperação confirmada','recovering':'Recuperação em curso','stabilizing':'Estabilização','bounce_only':'Ressalto sem confirmação','unconfirmed':'Sem confirmação','failed':'Falha de recuperação'}
    return {'recovery_status':status,'recovery_label':labels[status],'recovery_score':round(score,1),'recovery_price_score':round(price,1),'recovery_fundamental_score':round(fund,1),'recovery_return_20d_pct':round(r20,2) if r20 is not None else None,'recovery_return_60d_pct':round(r60,2) if r60 is not None else None,'recovery_reasons':reasons[:5]}

def assess_universe(rows):
    for row in rows: row.update(assess(row))
    return rows
