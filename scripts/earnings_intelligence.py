"""Vestra v4.5 earnings & estimate intelligence overlay.

Analyst expectations remain OUTSIDE the core investment score because coverage
is uneven across countries and providers. This module turns the available
estimate/revision/surprise data into a transparent secondary signal that can
move faster than reported fundamentals.
"""
from __future__ import annotations


def _n(v):
    try:
        x=float(v)
        return x if x == x and x not in (float('inf'), float('-inf')) else None
    except (TypeError, ValueError):
        return None


def _clip(x, lo=0.0, hi=100.0):
    return max(lo,min(hi,x))


def _avg_weighted(parts):
    vals=[(v,w) for v,w in parts if v is not None]
    if not vals:
        return None
    ws=sum(w for _,w in vals)
    return sum(v*w for v,w in vals)/ws


def _revision_score(v):
    """Map -10%..+10% consensus change to 0..100, centred on 50."""
    x=_n(v)
    if x is None:
        return None
    # values are stored as fractions (0.05 = +5%)
    return _clip(50.0 + (x/0.10)*50.0)


def _surprise_score(v):
    x=_n(v)
    if x is None:
        return None
    return _clip(50.0 + (x/0.10)*50.0)


def assess(row: dict) -> dict:
    up=_n(row.get('analyst_eps_revisions_up_30d'))
    down=_n(row.get('analyst_eps_revisions_down_30d'))
    total=(up or 0)+(down or 0)
    breadth=None
    breadth_score=None
    if total>0:
        breadth=((up or 0)-(down or 0))/total
        breadth_score=50.0+50.0*breadth

    qrev=_n(row.get('analyst_eps_next_q_revision_30d_pct'))
    yrev=_n(row.get('analyst_eps_next_y_revision_30d_pct'))
    rev_score=_avg_weighted([(_revision_score(qrev),0.45),(_revision_score(yrev),0.55)])

    avg_surprise=_n(row.get('analyst_earnings_avg_surprise_4q'))
    latest_surprise=_n(row.get('analyst_latest_eps_surprise_pct'))
    beats=_n(row.get('analyst_earnings_beats_4q'))
    misses=_n(row.get('analyst_earnings_misses_4q'))
    streak=_n(row.get('analyst_earnings_beat_streak'))
    surprise_score=_avg_weighted([
        (_surprise_score(avg_surprise),0.55),
        (_surprise_score(latest_surprise),0.25),
        (_clip(50.0+12.5*((beats or 0)-(misses or 0))),0.15) if beats is not None or misses is not None else (None,0.15),
        (_clip(50.0+10.0*(streak or 0)),0.05) if streak is not None else (None,0.05),
    ])

    fwd_eps=_n(row.get('analyst_eps_next_y_growth'))
    fwd_rev=_n(row.get('analyst_revenue_next_y_growth'))
    growth_score=_avg_weighted([
        (_clip(50.0+(fwd_eps/0.30)*35.0),0.6) if fwd_eps is not None else (None,0.6),
        (_clip(50.0+(fwd_rev/0.30)*35.0),0.4) if fwd_rev is not None else (None,0.4),
    ])

    momentum=_avg_weighted([
        (rev_score,0.45),
        (breadth_score,0.25),
        (surprise_score,0.20),
        (growth_score,0.10),
    ])

    coverage=_n(row.get('analyst_coverage_pct')) or 0.0
    nq=_n(row.get('analyst_eps_next_q_analysts')) or 0.0
    ny=_n(row.get('analyst_eps_next_y_analysts')) or 0.0
    analyst_depth=max(nq,ny)
    available=sum(x is not None for x in (rev_score,breadth_score,surprise_score,growth_score))
    if available>=3 and coverage>=55 and analyst_depth>=5:
        confidence='high'
    elif available>=2 and coverage>=30:
        confidence='medium'
    else:
        confidence='low'

    if momentum is None:
        signal='insufficient'
    elif momentum>=65:
        signal='improving'
    elif momentum<=35:
        signal='deteriorating'
    else:
        signal='neutral'

    days=row.get('analyst_days_to_earnings')
    try: days=int(days) if days is not None else None
    except Exception: days=None
    event_risk='imminent' if days is not None and 0<=days<=3 else 'near' if days is not None and 0<=days<=14 else 'none'

    drivers=[]
    if qrev is not None and abs(qrev)>=0.02:
        drivers.append(f"EPS próximo trimestre revisto {qrev*100:+.1f}% em 30d.")
    if yrev is not None and abs(yrev)>=0.02:
        drivers.append(f"EPS próximo ano revisto {yrev*100:+.1f}% em 30d.")
    if breadth is not None and abs(breadth)>=0.25:
        drivers.append(f"Breadth de revisões {breadth*100:+.0f}% ({int(up or 0)} ↑ / {int(down or 0)} ↓).")
    if avg_surprise is not None and abs(avg_surprise)>=0.03:
        drivers.append(f"Surpresa EPS média 4Q {avg_surprise*100:+.1f}%.")
    if streak is not None and streak>=2:
        drivers.append(f"Sequência de {int(streak)} beats de EPS.")
    if event_risk in ('imminent','near'):
        drivers.append(f"Resultados em {days} dias: risco/catalisador próximo.")

    return {
        'estimate_momentum_score': round(momentum,1) if momentum is not None else None,
        'estimate_revision_score': round(rev_score,1) if rev_score is not None else None,
        'estimate_revision_breadth_pct': round(breadth*100,1) if breadth is not None else None,
        'earnings_surprise_score': round(surprise_score,1) if surprise_score is not None else None,
        'estimate_growth_score': round(growth_score,1) if growth_score is not None else None,
        'estimate_signal': signal,
        'estimate_confidence': confidence,
        'earnings_event_risk': event_risk,
        'earnings_intelligence_drivers': drivers[:5],
    }
