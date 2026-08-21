"""Persist a compact daily history of physical-metals observations."""
from __future__ import annotations
import datetime as dt
import json
from pathlib import Path

MAX_DAYS = 730

def load(path):
    p=Path(path)
    if not p.exists(): return {"version":1,"days":[]}
    try:
        x=json.loads(p.read_text())
        return x if isinstance(x,dict) else {"version":1,"days":[]}
    except Exception:
        return {"version":1,"days":[]}

def _snapshot(payload, date):
    phys=payload.get("physical",{}) or {}
    cg=(phys.get("comex",{}) or {}).get("gold",{}) or {}
    cs=(phys.get("comex",{}) or {}).get("silver",{}) or {}
    dl=phys.get("deliveries",{}) or {}
    dg=dl.get("gold",{}) or {}; ds=dl.get("silver",{}) or {}
    cot=(phys.get("positioning",{}) or {}).get("gold",{}) or {}
    return {"date":date,
      "gold_registered_oz":cg.get("registered_oz"), "gold_eligible_oz":cg.get("eligible_oz"), "gold_total_oz":cg.get("total_oz"),
      "silver_registered_oz":cs.get("registered_oz"), "silver_eligible_oz":cs.get("eligible_oz"), "silver_total_oz":cs.get("total_oz"),
      "gold_daily_delivery_notices":dg.get("daily_notices"), "gold_mtd_delivery_notices":dg.get("month_to_date_notices"),
      "silver_daily_delivery_notices":ds.get("daily_notices"), "silver_mtd_delivery_notices":ds.get("month_to_date_notices"),
      "gold_mm_net_pct_oi":cot.get("managed_money_net_pct_oi")}

def update(hist,payload,date=None):
    date=date or dt.date.today().isoformat()
    days=[d for d in hist.get("days",[]) if d.get("date")!=date]
    days.append(_snapshot(payload,date)); days=sorted(days,key=lambda d:d.get("date",""))[-MAX_DAYS:]
    return {"version":1,"days":days}

def save(hist,path):
    Path(path).write_text(json.dumps(hist,indent=2))

def _clamp(v, lo=0.0, hi=100.0):
    return max(lo, min(hi, float(v)))

def _linear(v, low, high, invert=False):
    if v is None or high == low: return None
    x = _clamp((float(v)-low)/(high-low)*100.0)
    return 100.0-x if invert else x

def _pressure_index(payload, hist):
    """Transparent 0-100 gold pressure index. Higher = tighter/more demand pressure.

    Components are reweighted only across available source-backed inputs:
    - registered inventory contraction (35%)
    - delivery-notice intensity vs registered inventory (25%)
    - Shanghai-vs-COMEX proxy premium (20%)
    - managed-money net positioning (10%)
    - central-bank net flow in latest WGC period (10%)
    Missing inputs reduce confidence; they are never imputed.
    """
    phys=payload.get("physical",{}) or {}
    comex=(phys.get("comex",{}) or {}).get("gold",{}) or {}
    delivery=(phys.get("deliveries",{}) or {}).get("gold",{}) or {}
    sge=(phys.get("shanghai",{}) or {}).get("gold_benchmark",{}) or {}
    cot=(phys.get("positioning",{}) or {}).get("gold",{}) or {}
    cb=phys.get("central_banks",{}) or {}
    trends=(payload.get("physical_history",{}) or {}).get("trends",{}).get("gold",{}) or {}

    components=[]
    def add(key,label,weight,raw,score,explain):
        if score is None: return
        components.append({"key":key,"label":label,"weight":weight,"raw":raw,"score":round(float(score),1),"explain":explain})

    inv=trends.get("registered_change_30d_pct")
    # +10% inventory growth => 0 pressure; -20% contraction => 100.
    add("inventory","Registered inventory",35,inv,_linear(inv,-20,10,True),
        "Contração do registered aumenta pressão; expansão reduz." if inv is not None else "")

    reg=comex.get("registered_oz")
    daily=delivery.get("daily_oz_equivalent")
    intensity=(float(daily)/float(reg)*100.0) if reg not in (None,0) and daily is not None else None
    # 0% => 0; 5% of registered equivalent in one day => 100 (context, not withdrawal).
    add("deliveries","Delivery intensity",25,intensity,_linear(intensity,0,5),
        "Notices/registered em equivalente contratual; não implica retirada do vault.")

    prem=sge.get("premium_vs_comex_front_pct")
    # -2% => 0; +5% => 100.
    add("shanghai","Shanghai proxy",20,prem,_linear(prem,-2,5),
        "SGE benchmark convertido vs futuro COMEX; proxy cross-market.")

    mm=cot.get("managed_money_net_pct_oi")
    # -20% net => 0; +30% net => 100. Positioning, not physical supply.
    add("positioning","Managed money",10,mm,_linear(mm,-20,30),
        "Posicionamento CFTC; componente de procura financeira, não de stock físico.")

    buyers=sum(float(x.get("tonnes",0) or 0) for x in cb.get("buyers",[]) if isinstance(x,dict)) if cb.get("status")=="ok" else None
    sellers=sum(float(x.get("tonnes",0) or 0) for x in cb.get("sellers",[]) if isinstance(x,dict)) if cb.get("status")=="ok" else None
    net_cb=(buyers+sellers) if buyers is not None and sellers is not None else None
    # -100t => 0; +100t => 100 within the displayed latest-period sample.
    add("central_banks","Central banks",10,net_cb,_linear(net_cb,-100,100),
        "Soma dos maiores compradores/vendedores disponíveis no último período WGC.")

    avail=sum(c["weight"] for c in components)
    if avail < 35:
        return {"status":"insufficient","score":None,"coverage_pct":avail,"components":components,
                "label":"dados insuficientes","method":"Índice só é mostrado com cobertura material de fontes oficiais."}
    score=sum(c["score"]*c["weight"] for c in components)/avail
    if score>=75: label="pressão elevada"
    elif score>=60: label="pressão moderadamente elevada"
    elif score>=40: label="equilíbrio"
    elif score>=25: label="pressão baixa"
    else: label="mercado físico folgado"
    return {"status":"ok","score":round(score,1),"coverage_pct":avail,"label":label,"components":components,
            "method":"0-100; média ponderada apenas dos componentes disponíveis. Não é previsão de preço nem sinal de compra/venda."}

def enrich(payload,hist):
    days=hist.get("days",[])
    if not days: return payload
    cur=days[-1]
    def pct(field, lookback):
        now=cur.get(field)
        if now in (None,0): return None
        target=None
        curdate=dt.date.fromisoformat(cur["date"])
        for d in reversed(days[:-1]):
            try: age=(curdate-dt.date.fromisoformat(d["date"])).days
            except Exception: continue
            if age>=lookback and d.get(field) not in (None,0): target=d; break
        if not target: return None
        prev=target[field]
        return round((now/prev-1)*100,1) if prev else None
    trends={}
    for metal in ("gold","silver"):
        field=f"{metal}_registered_oz"
        trends[metal]={"registered_change_7d_pct":pct(field,7),"registered_change_30d_pct":pct(field,30),"registered_change_365d_pct":pct(field,365)}
    payload["physical_history"]={"observations":len(days),"trends":trends,"recent":days[-60:]}
    pressure=_pressure_index(payload,hist)
    payload["physical_pressure_index"]=pressure
    # Persist today's computed index in the same history object for future charts.
    if days and pressure.get("score") is not None:
        days[-1]["gold_pressure_index"]=pressure.get("score")
        days[-1]["gold_pressure_coverage_pct"]=pressure.get("coverage_pct")
        payload["physical_history"]["recent"]=days[-60:]
    return payload
