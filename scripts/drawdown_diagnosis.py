"""Vestra v6.4 — explainable drawdown diagnosis.

Diagnoses likely drivers of a large price drawdown using only evidence already
collected by Vestra. This is not causal proof and does not alter Score Vestra.
"""
from __future__ import annotations


def _n(v):
    try:
        if v is None or v == "": return None
        x=float(v); return x if x==x else None
    except Exception: return None


def _clamp(x,lo=0.0,hi=100.0): return max(lo,min(hi,float(x)))


def _price(row):
    hist=row.get("price_history_1y") or []
    closes=[]
    for item in hist:
        try:
            v=item.get("close") if isinstance(item,dict) else item
            v=float(v)
            if v>0: closes.append(v)
        except Exception: pass
    cur=_n(row.get("current_price"))
    if cur is None and closes: cur=closes[-1]
    if not closes or cur is None or cur<=0: return None
    high=max(closes); low=min(closes)
    return {"drawdown_pct":(cur/high-1)*100.0,"above_low_pct":(cur/low-1)*100.0}


def assess(row: dict) -> dict:
    if str(row.get("quote_type") or "").upper() in ("ETF","CRYPTO","MUTUALFUND"):
        return {}
    p=_price(row)
    if not p or p["drawdown_pct"]>-12:
        return {"drawdown_diagnosis_status":"not_material","drawdown_diagnosis":[],"drawdown_primary_driver":None,"drawdown_driver_trend":"stable"}

    drivers=[]
    def add(key,label,strength,trend,evidence):
        if strength<=0: return
        drivers.append({"key":key,"label":label,"strength":round(_clamp(strength),1),"trend":trend,"evidence":[x for x in evidence if x][:4]})

    rev=_n(row.get("revenue_growth")); rev_acc=_n(row.get("revenue_yoy_acceleration_pp")); margin=_n(row.get("net_margin_yoy_change_pp")); execs=_n(row.get("execution_pct")); eq=_n(row.get("earnings_quality_pct"))
    op=0; ev=[]
    if rev is not None and rev<-0.15: op+=35; ev.append(f"Receita {rev*100:.0f}% YoY")
    elif rev is not None and rev<-0.05: op+=20; ev.append(f"Receita {rev*100:.0f}% YoY")
    if rev_acc is not None and rev_acc<-8: op+=22; ev.append(f"Aceleração receita {rev_acc:+.1f} pp")
    if margin is not None and margin<-3: op+=22; ev.append(f"Margem {margin:+.1f} pp")
    if execs is not None and execs<45: op+=12; ev.append(f"Execução {execs:.0f}/100")
    if eq is not None and eq<45: op+=10; ev.append(f"Qualidade lucros {eq:.0f}/100")
    optrend="improving" if ((rev_acc or 0)>=5 or (margin or 0)>=1) else "deteriorating" if ((rev_acc or 0)<-5 or (margin or 0)<-2) else "stable"
    add("operating","Deterioração operacional",op,optrend,ev)

    est=_n(row.get("estimate_momentum_score")); estsig=str(row.get("estimate_signal") or "").lower(); breadth=_n(row.get("estimate_revision_breadth_pct")); surprise=_n(row.get("earnings_surprise_score")); eev=[]; es=0
    if estsig=="deteriorating": es+=35; eev.append(f"Momentum estimativas {est:.0f}/100" if est is not None else "Estimativas a deteriorar")
    if breadth is not None and breadth<-25: es+=25; eev.append(f"Breadth revisões {breadth:.0f}%")
    if surprise is not None and surprise<40: es+=15; eev.append(f"Surpresas {surprise:.0f}/100")
    if str(row.get("thesis_direction") or "").lower()=="down": es+=12; eev.append("Tese quantitativa a piorar")
    etrend="improving" if estsig=="improving" else "deteriorating" if estsig=="deteriorating" else "stable"
    add("expectations","Reset de expectativas",es,etrend,eev)

    bal=_n(row.get("balance_pct")); gate=str(row.get("risk_gate") or "clear").lower(); cap=str(row.get("capital_structure_risk") or "clear").lower(); flags=set(row.get("risk_flags") or [])|set(row.get("capital_structure_flags") or [])
    bs=0; bev=[]
    if gate=="severe": bs+=45; bev.append("Risk Gate severe")
    elif gate=="high": bs+=32; bev.append("Risk Gate high")
    elif gate=="watch": bs+=12; bev.append("Risk Gate watch")
    if cap in ("high","severe"): bs+=30; bev.append(f"Capital structure {cap}")
    if bal is not None and bal<40: bs+=20; bev.append(f"Balanço {bal:.0f}/100")
    if "zombie_coverage" in flags: bs+=25; bev.append("Cobertura de juros frágil")
    add("balance","Balanço / financiamento",bs,"deteriorating" if bs>=35 else "stable",bev)

    dil=_n(row.get("diluted_shares_yoy")); ds=0; dev=[]
    if dil is not None and dil>0.50: ds+=50; dev.append(f"Diluição +{dil*100:.0f}% YoY")
    elif dil is not None and dil>0.20: ds+=35; dev.append(f"Diluição +{dil*100:.0f}% YoY")
    elif dil is not None and dil>0.08: ds+=18; dev.append(f"Diluição +{dil*100:.0f}% YoY")
    if "severe_dilution" in flags: ds=max(ds,55); dev.append("Severe dilution flag")
    elif "material_dilution" in flags: ds=max(ds,38); dev.append("Material dilution flag")
    if any("reverse" in str(x).lower() or "atm" in str(x).lower() or "warrant" in str(x).lower() or "convert" in str(x).lower() for x in flags): ds+=15; dev.append("Financiamento dilutivo / reverse split")
    add("dilution","Diluição / oferta de ações",ds,"deteriorating" if ds>=30 else "stable",dev)

    val=str(row.get("valuation_signal") or "").lower(); value=_n(row.get("value_pct")); fv=_n(row.get("fair_value_upside_pct")); vs=0; vev=[]
    if val=="undervalued": vs+=32; vev.append("Valuation atual abaixo do fair range")
    elif val=="fair": vs+=18; vev.append("Valuation atual normalizada")
    if value is not None and value>=65: vs+=22; vev.append(f"Value {value:.0f}/100")
    if fv is not None and fv>=20: vs+=22; vev.append(f"Upside fair value {fv:.0f}%")
    if op>=35 or es>=35 or bs>=35: vs*=0.55
    add("multiple","Compressão de múltiplos",vs,"improving" if val=="undervalued" else "stable",vev)

    drivers.sort(key=lambda x:x["strength"],reverse=True)
    company_specific=max([x["strength"] for x in drivers],default=0)
    if company_specific<28:
        drivers.append({"key":"market","label":"Mercado / setor (proxy residual)","strength":round(_clamp(55-company_specific),1),"trend":"stable","evidence":["Pouca evidência company-specific suficiente para explicar a queda"]})
        drivers.sort(key=lambda x:x["strength"],reverse=True)

    primary=drivers[0] if drivers else None
    trend=primary.get("trend") if primary else "stable"
    status="mixed" if len(drivers)>=2 and drivers[1]["strength"]>=0.8*drivers[0]["strength"] else "identified" if primary else "insufficient"
    return {
        "drawdown_diagnosis_status":status,
        "drawdown_primary_driver":primary.get("key") if primary else None,
        "drawdown_primary_label":primary.get("label") if primary else None,
        "drawdown_driver_trend":trend,
        "drawdown_from_high_pct":round(p["drawdown_pct"],2),
        "drawdown_above_low_pct":round(p["above_low_pct"],2),
        "drawdown_diagnosis":drivers[:5],
    }
