"""Vestra v4.6 intelligent scanner overlays.

Scanner strategies do not alter the core Vestra score. They combine already
computed evidence into transparent screening tags with per-strategy scores and
short reasons. Missing data are never interpreted as zero evidence.
"""
from __future__ import annotations


def _n(v):
    try:
        if v is None or v == "": return None
        x=float(v)
        return x if x==x else None
    except Exception:
        return None


def _clamp(v, lo=0.0, hi=100.0):
    return max(lo,min(hi,float(v)))


def _low52(row):
    hist=row.get("price_history_1y") or []
    closes=[]
    for x in hist:
        try:
            v=x.get("close") if isinstance(x,dict) else x
            v=float(v)
            if v>0: closes.append(v)
        except Exception: pass
    cur=_n(row.get("current_price"))
    if cur is None and closes: cur=closes[-1]
    if not closes or cur is None or cur<=0: return None
    low=min(closes)
    return {"low":low,"above_pct":(cur/low-1)*100.0}


def _dividend_growth(row):
    hist=row.get("annual_dividend_history") or []
    vals=[]
    for item in hist[:6]:
        try:
            if isinstance(item,dict): v=item.get("value",item.get("dividend",item.get("amount")))
            else: v=item
            v=float(v)
            if v>=0: vals.append(v)
        except Exception: pass
    if len(vals)<2: return None
    comps=[newer/older-1 for newer,older in zip(vals,vals[1:]) if older>0]
    return sum(comps)/len(comps) if comps else None


def assess(row: dict) -> dict:
    if str(row.get("quote_type") or "").upper() in ("ETF","CRYPTO","MUTUALFUND"):
        return {"scanner_tags":[],"scanner_results":{}}
    score=_n(row.get("score")); quality=_n(row.get("quality_pct")); value=_n(row.get("value_pct")); conf=_n(row.get("confidence_score"))
    gate=str(row.get("risk_gate") or "clear").lower(); rev=_n(row.get("revenue_growth")); dilution=_n(row.get("diluted_shares_yoy"))
    margin_delta=_n(row.get("net_margin_yoy_change_pp")); rev_accel=_n(row.get("revenue_yoy_acceleration_pp")); thesis=str(row.get("thesis_direction") or "")
    delta30=_n(row.get("thesis_score_delta_30d")); valuation=str(row.get("valuation_signal") or ""); mos=_n(row.get("margin_of_safety_pct"))
    est=_n(row.get("estimate_momentum_score")); est_signal=str(row.get("estimate_signal") or ""); buy_count=_n(row.get("insider_buy_count_30d")) or 0
    buy_val=_n(row.get("insider_buy_value_30d")) or 0; sell_val=_n(row.get("insider_sell_value_30d")) or 0
    div_yield=_n(row.get("dividend_yield")); div_cover=_n(row.get("dividend_fcf_coverage")); low52=_low52(row); div_growth=_dividend_growth(row)
    low52_status=str(row.get("low52_status") or ""); low52_score=_n(row.get("low52_score")); low52_reasons=list(row.get("low52_reasons") or [])
    flags=set(row.get("risk_flags") or []); safe_gate=gate in ("clear","watch"); results={}
    def add(key,label,parts,reasons):
        vals=[float(p) for p in parts if p is not None]
        if vals: results[key]={"label":label,"score":round(_clamp(sum(vals)/len(vals)),1),"reasons":reasons[:4]}
    if safe_gate and (quality or 0)>=65 and (conf or 0)>=60 and (score or 0)>=62 and (valuation in ("undervalued","fair") or (mos is not None and mos>=8) or (value or 0)>=60):
        add("qarp","Quality at a Reasonable Price",[quality,score,conf,(value or 50),_clamp(50+(mos or 0))],[f"Qualidade {quality:.0f}/100",f"Score {score:.0f}/100",f"Confiança {conf:.0f}/100",f"Margem de segurança {mos:.0f}%" if mos is not None else "Valuation favorável vs pares"])
    if low52 and low52["above_pct"]<=15 and low52_status in ("opportunity","watch") and low52_score is not None:
        add("fallen_angels","Fallen Angels",[low52_score,quality,conf,score],low52_reasons or [f"{max(0,low52['above_pct']):.1f}% acima do mínimo 52s","Sem deterioração estrutural dominante"])
    if low52 and low52["above_pct"]<=5 and low52_status=="opportunity" and low52_score is not None:
        add("lows_intact","Mínimos 52s · fundamentos intactos",[low52_score,quality,conf,score],low52_reasons or [f"{max(0,low52['above_pct']):.1f}% acima do mínimo 52s","Risk Gate sem alerta alto/severo"])
    if est_signal=="improving" and (est or 0)>=65 and gate not in ("high","severe"):
        breadth=_n(row.get("estimate_revision_breadth_pct")); add("positive_revisions","Revisões positivas",[est,breadth,conf],[f"Momentum de expectativas {est:.0f}/100",f"Breadth {breadth:.0f}%" if breadth is not None else "Revisões de EPS a subir",f"Confiança {conf:.0f}/100" if conf is not None else "Overlay de analistas"])
    if gate not in ("high","severe") and buy_count>=1 and buy_val>sell_val and (buy_count>=2 or buy_val>=100000):
        add("insider_accumulation","Insider Accumulation",[_clamp(45+buy_count*8+min(30,buy_val/100000)),conf,score],[f"{int(buy_count)} compras open-market",f"Compras líquidas ~{buy_val-sell_val:,.0f} USD",f"Score {score:.0f}/100" if score is not None else "Sem score suficiente"])
    turnaround_signal=(delta30 is not None and delta30>=3) or ((rev_accel or 0)>=5 and (margin_delta or 0)>=1)
    if turnaround_signal and gate!="severe" and (conf or 0)>=55 and (score or 0)>=45 and thesis!="down":
        add("turnarounds","Turnarounds",[_clamp(55+(delta30 or 0)*3+(rev_accel or 0)*0.5+(margin_delta or 0)*3),conf,score],[f"Δ score 30d +{delta30:.1f}" if delta30 is not None else "Execução a acelerar",f"Aceleração receita {rev_accel:+.1f} pp" if rev_accel is not None else "Receita a melhorar",f"Margem {margin_delta:+.1f} pp" if margin_delta is not None else "Margens estabilizadas"])
    if div_yield is not None and div_yield>0 and safe_gate and (quality or 0)>=55 and (conf or 0)>=55 and (dilution is None or dilution<=0.05) and (div_cover is None or div_cover>=1.0) and (div_growth is None or div_growth>=0):
        add("dividend_growers","Dividend Growers",[quality,conf,_clamp(50+(div_growth or 0)*200),_clamp(45+div_yield*700),score],[f"Dividend yield {div_yield*100:.1f}%",f"Qualidade {quality:.0f}/100",f"Cobertura FCF {div_cover:.2f}×" if div_cover is not None else "Sem sinal de payout descoberto","Sem diluição material"])
    ordered=sorted(results.items(),key=lambda kv:kv[1]["score"],reverse=True)
    return {"scanner_tags":[k for k,_ in ordered],"scanner_results":dict(ordered),"scanner_best":ordered[0][0] if ordered else None,"scanner_best_score":ordered[0][1]["score"] if ordered else None}
