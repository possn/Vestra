#!/usr/bin/env python3
"""Pre-registered illustrative compression watch, offline only; NOT validated alpha.

Consumes ascending, adjusted, *as-of available* daily OHLCV rows. No tuning,
probabilities, order execution, UI integration or fabricated missing volume.
The source adapter must independently guarantee instrument identity, venue,
adjustments, complete trading sessions, and timestamp availability.
"""
from __future__ import annotations
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from datetime import datetime, timezone
from prospective_shadow_journal import canonical, append_signal

RULE_ID="compression-volume-watch-v0"
MODEL_VERSION="prebreakout-shadow-v0"
MIN_BARS=65


def _positive(value, *, allow_zero=False):
    try:
        v=Decimal(str(value))
        if not v.is_finite() or (v<0 if allow_zero else v<=0):
            raise ValueError("nonpositive")
        return v
    except (InvalidOperation, TypeError) as e:
        raise ValueError("invalid numeric observation") from e


def evaluate_watch(rows, *, issuer_id, source, source_available_at_utc, captured_at_utc):
    """Compute one watch candidate from immutable, nonfuture full-session observations.

    Requires >=65 daily bars; uses latest 20 vs previous 40 close-to-close
    return ranges, average daily volume on those periods, and current close
    above 50-session average. All thresholds are hypotheses, not fitted facts.
    """
    if not isinstance(rows,list) or len(rows)<MIN_BARS:
        return {"status":"INSUFFICIENT_HISTORY","watch":False}
    if not all(isinstance(x,str) and x.strip() for x in (issuer_id,source)):
        raise ValueError("missing identity/source")
    cap=datetime.fromisoformat(captured_at_utc.replace("Z","+00:00"))
    avail=datetime.fromisoformat(source_available_at_utc.replace("Z","+00:00"))
    if cap.tzinfo is None or avail.tzinfo is None or avail>cap:
        raise ValueError("source not available at capture")
    parsed=[]
    seen=set()
    from datetime import date
    last=None
    for r in rows:
        if not isinstance(r,dict) or not all(k in r for k in ("session","open","high","low","close","volume")):
            raise ValueError("incomplete OHLCV")
        d=date.fromisoformat(r["session"])
        if d in seen or (last is not None and d<=last) or d>cap.date():
            raise ValueError("duplicate, unordered or future session")
        seen.add(d);last=d
        o,h,l,c=(_positive(r[k]) for k in ("open","high","low","close"))
        vol=_positive(r["volume"],allow_zero=True)
        if h<max(o,c,l) or l>min(o,c,h):
            raise ValueError("inconsistent OHLC")
        parsed.append((d,o,h,l,c,vol))
    last65=parsed[-65:]
    base=last65[-20:]
    prior=last65[-60:-20]
    def span(part):
        closes=[x[4] for x in part]
        return (max(closes)-min(closes))/min(closes)
    compression=span(base) <= span(prior)*Decimal("0.55")
    volume_contract=sum(x[5] for x in base)/Decimal(len(base)) < (
        sum(x[5] for x in prior)/Decimal(len(prior)))*Decimal("0.85")
    moving_average=sum(x[4] for x in last65[-50:])/Decimal(50)
    trend=last65[-1][4] > moving_average
    watch=bool(compression and volume_contract and trend)
    # Features are hashed, not stored as historical performance evidence.
    features={"signal_session":str(last65[-1][0]),"compression":compression,
              "volume_contract":volume_contract,"above_ma50":trend,
              "rule_id":RULE_ID}
    signal={"issuer_id":issuer_id,"signal_session":str(last65[-1][0]),
            "model_version":MODEL_VERSION,"rule_id":RULE_ID,
            "source":source,"source_available_at_utc":source_available_at_utc,
            "features_sha256":sha256(canonical(features).encode()).hexdigest()}
    return {"status":"RESEARCH_WATCH_UNVALIDATED" if watch else "NO_WATCH",
            "watch":watch,"signal":signal if watch else None,
            "criteria":features,"interpretation":"hypothesis_not_calibrated_probability"}


def record_watch(journal_path, rows, *, issuer_id, source, source_available_at_utc, now=None):
    """Only records true candidates on caller-managed private durable storage."""
    moment=now or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        raise ValueError("naive capture")
    result=evaluate_watch(rows,issuer_id=issuer_id,source=source,
                          source_available_at_utc=source_available_at_utc,
                          captured_at_utc=moment.astimezone(timezone.utc).isoformat())
    if not result["watch"]:
        return {"status":result["status"],"journal_written":False}
    saved=append_signal(journal_path,result["signal"],now=moment)
    return {"status":saved["status"],"journal_written":True,
            "record_sha256":saved["record_sha256"]}
