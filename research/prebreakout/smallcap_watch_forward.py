"""Prospective follow-up of *observed* small-cap watch episodes, never signals.

The anchor is frozen at the first publication. Future returns are filled only
from a later independent download; unobserved sessions remain unknown.
"""
from datetime import datetime, timedelta, timezone
import math

HORIZONS=(5,10,20,60)
MAX_AGE_DAYS=150
MAX_EPISODES=400


def _finite_positive(value):
    return type(value) in (int,float) and math.isfinite(value) and value>0


def _outcome(anchor, history, spy_history, horizon, now):
    """Demand exactly N later observed ticker sessions and matching SPY dates."""
    if not isinstance(history,list) or not isinstance(spy_history,dict):return None
    days=[row[0] for row in history]
    if len(days)!=len(set(days)) or days!=sorted(days):return None
    anchor_day=anchor["anchor_session"]
    if anchor_day not in days:return None
    index=days.index(anchor_day)
    forward=history[index+1:index+horizon+1]
    if len(forward)<horizon:return None
    if forward[-1][0]>=now.date().isoformat():return None
    prices=[row[1] for row in forward]
    if not all(_finite_positive(x) for x in prices):return None
    if any(day not in spy_history or not _finite_positive(spy_history[day]) for day,_ in forward):
        return None
    old_close=history[index][1]
    if not _finite_positive(old_close) or abs(old_close/anchor["anchor_close"]-1)>.001:
        return None  # Adjusted history changed since capture; cannot compare bases.
    old_spy=spy_history.get(anchor_day)
    if not _finite_positive(old_spy) or abs(old_spy/anchor["anchor_spy_close"]-1)>.001:
        return None
    ret=prices[-1]/anchor["anchor_close"]-1
    bench=spy_history[forward[-1][0]]/anchor["anchor_spy_close"]-1
    running=[anchor["anchor_close"]]+prices
    peak=running[0]
    max_drawdown=0.0
    for close in running:
        peak=max(peak,close)
        max_drawdown=min(max_drawdown,close/peak-1)
    return {"last_session":forward[-1][0],"return_pct":round(100*ret,4),
            "spy_return_pct":round(100*bench,4),
            "excess_return_pct_points":round(100*(ret-bench),4),
            "max_drawdown_pct":round(100*max_drawdown,4),
            "completed_aligned_sessions":horizon,
            "price_basis":"yfinance_auto_adjusted_rechecked_within_0_1pct"}


def reconcile(previous, current, fresh_histories, spy_history, now):
    """Keep immutable anchors; mature outcomes without inventing absent bars."""
    prior=previous.get("prospective_watch_episodes",[]) if isinstance(previous,dict) else []
    episodes={}
    cutoff=(now-timedelta(days=MAX_AGE_DAYS)).date().isoformat()
    for row in prior if isinstance(prior,list) else []:
        if not isinstance(row,dict):continue
        key=row.get("episode_id")
        if (not isinstance(key,str) or key in episodes or
            not isinstance(row.get("anchor_session"),str) or row["anchor_session"]<cutoff or
            not _finite_positive(row.get("anchor_close")) or
            not _finite_positive(row.get("anchor_spy_close"))):continue
        episodes[key]=row
    for watch in current.get("geometry_watch_observations",[]):
        ticker=watch.get("ticker")
        day=watch.get("last_session")
        history=fresh_histories.get(ticker)
        if (not isinstance(history,list) or not history or history[-1][0]!=day or
            day>=now.date().isoformat()):continue
        close=history[-1][1]
        spy_close=spy_history.get(day) if isinstance(spy_history,dict) else None
        if not _finite_positive(close) or not _finite_positive(spy_close):continue
        # One anchor per ticker per 60-session observation cycle. Do not
        # manufacture a fresh episode on every four-hour collection slot.
        if any(e.get("ticker")==ticker and e["anchor_session"]>=
               (now-timedelta(days=95)).date().isoformat() for e in episodes.values()):continue
        key=f"{ticker}:{day}"
        episodes[key]={"episode_id":key,"ticker":ticker,"anchor_session":day,
            "captured_at":now.isoformat(),"anchor_close":round(close,6),
            "anchor_spy_close":round(spy_close,6),"anchor_status":watch["status"],
            "anchor_technical_evidence":watch.get("technical_evidence"),
            "anchor_base_width_pass":watch["base_width_pass"],
            "anchor_contractions_pass":watch["contractions_pass"],
            "outcomes":{},"research_only_not_signal":True}
    for episode in episodes.values():
        ticker=episode["ticker"]
        history=fresh_histories.get(ticker)
        if not isinstance(history,list):continue
        for horizon in HORIZONS:
            key=str(horizon)
            if key in episode["outcomes"]:continue
            observed=_outcome(episode,history,spy_history,horizon,now)
            if observed is not None:
                episode["outcomes"][key]=observed
    ordered=sorted(episodes.values(),key=lambda row:(row["anchor_session"],row["ticker"]))[-MAX_EPISODES:]
    mature={str(h):sum(str(h) in row["outcomes"] for row in ordered) for h in HORIZONS}
    return {"prospective_watch_episodes":ordered,
            "prospective_watch_audit":{
                "episodes":len(ordered),"matured_by_horizon":mature,
                "pending_by_horizon":{str(h):len(ordered)-mature[str(h)] for h in HORIZONS},
                "no_unobserved_zero_returns_or_success_probability":True,
                "partial_geometry_experimental_not_verified_signal":True,
                "forward_prices_only_from_later_provider_observation":True,
                "not_pit_corporate_action_verified":True}}
