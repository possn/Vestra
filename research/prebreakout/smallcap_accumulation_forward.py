"""Experimental accumulation cohort; no production signal or probability."""
from datetime import date, timedelta
import math
from research.prebreakout.smallcap_watch_forward import _outcome, _finite_positive, HORIZONS

POLICY="accumulation_v2"
def _num(v):
    return type(v) in (int,float) and math.isfinite(v)

def candidate(row, now):
    if row.get("status")!="evaluable_ohlcv" or row.get("verified_prebreakout_setup"):
        return False
    e=row.get("technical_evidence_shadow") or {}
    g=row.get("technical_prebreakout_lineage") or {}
    a=row.get("technical_base_anchor") or {}
    turnover=row.get("average_dollar_volume_20_usd")
    if not _num(turnover) or turnover<1_000_000 or row.get("currency")!="USD":
        return False
    try:
        age=(now.date()-date.fromisoformat(row["last_session"])).days
    except (KeyError,ValueError,TypeError):
        return False
    if not 0<age<=7 or a.get("session")!=row["last_session"]:
        return False
    if g.get("unbroken_prebreakout_position") is not True or g.get("prior_confirmed_breakouts_in_base")!=0:
        return False
    impulse=g.get("prebase_impulse_pct")
    if (g.get("prebase_volume_lineage_complete") is not True
            or type(g.get("prior_confirmed_breakouts_before_base")) is not int
            or g["prior_confirmed_breakouts_before_base"]!=0
            or not _num(impulse) or impulse>=25):
        return False
    # Independent accumulation hypothesis: no MA requirement, but no
    # observed pivot crossing. Thresholds are exploratory, fixed at capture.
    atr=e.get("atr14_to_prior46")
    obv=e.get("normalized_obv_change20")
    cmf=e.get("chaikin_money_flow20")
    rs=e.get("relative_return_20_vs_spy_pct")
    dist=g.get("distance_to_pivot_pct")
    close=a.get("adjusted_close")
    pivot=a.get("adjusted_pivot_high")
    high=a.get("observed_last_high")
    return (all(_num(v) for v in (atr,obv,cmf,rs,dist,close,pivot,high))
            and 0<atr<.8 and 0<obv<=1 and 0<cmf<=1 and rs>0
            and 0<=dist<=8 and 0<close<=pivot and close<=high<=pivot
            and abs(100*(pivot/close-1)-dist)<.002)

def reconcile_accumulation(previous,current,fresh_histories,spy_history,now):
    prior=previous.get("accumulation_episodes",[]) if isinstance(previous,dict) else []
    cutoff=(now-timedelta(days=150)).date().isoformat()
    episodes={}
    for row in prior:
        if (isinstance(row,dict) and row.get("policy")==POLICY
                and isinstance(row.get("episode_id"),str)
                and isinstance(row.get("anchor_session"),str)
                and cutoff<=row["anchor_session"]<now.date().isoformat()
                and _finite_positive(row.get("anchor_close"))
                and _finite_positive(row.get("anchor_spy_close"))
                and isinstance(row.get("outcomes"),dict)):
            episodes[row["episode_id"]]={**row,"outcomes":dict(row["outcomes"])}
    matched=[]
    for row in current.get("observations",[]):
        if not candidate(row,now):
            continue
        ticker=row["ticker"]
        day=row["last_session"]
        matched.append(ticker)
        history=fresh_histories.get(ticker)
        if not history or history[-1][0]!=day:
            continue
        close=history[-1][1]
        spy=spy_history.get(day)
        a=row["technical_base_anchor"]
        if not _finite_positive(close) or not _finite_positive(spy) or abs(close/a["adjusted_close"]-1)>.001:
            continue
        if any(e["ticker"]==ticker and e["anchor_session"]>=(now-timedelta(days=95)).date().isoformat() for e in episodes.values()):
            continue
        key=f"{POLICY}:{ticker}:{day}"
        episodes[key]={"episode_id":key,"policy":POLICY,"ticker":ticker,
            "anchor_session":day,"captured_at":now.isoformat(),
            "anchor_close":close,"anchor_spy_close":spy,
            "anchor_pivot":a["adjusted_pivot_high"],
            "anchor_lineage":row["technical_prebreakout_lineage"],
            "anchor_technical_evidence":row["technical_evidence_shadow"],
            "outcomes":{},"research_only_not_signal":True}
    for e in episodes.values():
        history=fresh_histories.get(e["ticker"])
        for h in HORIZONS:
            if str(h) not in e["outcomes"]:
                result=_outcome(e,history,spy_history,h,now)
                if result is not None:
                    e["outcomes"][str(h)]=result
    ordered=sorted(episodes.values(),key=lambda e:(e["anchor_session"],e["ticker"]))[-400:]
    return {"accumulation_episodes":ordered,
            "accumulation_audit":{"policy":POLICY,"matched_tickers":sorted(set(matched)),
            "episodes":len(ordered),"matured_by_horizon":{str(h):sum(str(h) in e["outcomes"] for e in ordered) for h in HORIZONS},
            "research_only_not_signal":True,"no_predictive_validation":True,
            "prebase_lineage_required":True}}
