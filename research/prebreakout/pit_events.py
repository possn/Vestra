#!/usr/bin/env python3
"""Offline point-in-time event definitions. No production scanner dependencies.

Input rows MUST be sorted completed exchange sessions with genuine OHLCV.
No downloaded current constituents, live quotes, or synthetic histories.
"""
from __future__ import annotations

from datetime import date
import math


def validate_bars(bars: list[dict]) -> None:
    """Fail closed on missing/out-of-order bars, nonfinite values and invalid OHLC."""
    previous = None
    for bar in bars:
        if not isinstance(bar, dict):
            raise ValueError("invalid bar")
        try:
            day = date.fromisoformat(str(bar["date"])[:10])
            op, high, low, close, volume = (float(bar[x]) for x in
                                              ("open", "high", "low", "close", "volume"))
        except (KeyError, TypeError, ValueError, OverflowError) as exc:
            raise ValueError("incomplete OHLCV") from exc
        if previous is not None and day <= previous:
            raise ValueError("unordered or duplicate sessions")
        if not all(math.isfinite(x) for x in (op, high, low, close, volume)):
            raise ValueError("nonfinite OHLCV")
        if not (low > 0 and low <= min(op, close) <= max(op, close) <= high and volume >= 0):
            raise ValueError("invalid OHLCV bounds")
        previous = day


def breakout_outcome(bars: list[dict], signal_index: int, pivot: float,
                     horizon: int, volume_multiple: float = 1.5) -> dict:
    """Research label strictly after the as-of signal session.

    Crossing: future CLOSE > published pivot * 1.005, above previous close,
    close location in upper quartile, volume >= multiple of 20 PRIOR sessions.
    A confirmed event needs complete prior volume. Any insufficient forward
    horizon is pending (even if an early breakout is visible), avoiding
    mismatched matured denominators.
    """
    validate_bars(bars)
    if not isinstance(signal_index, int) or not isinstance(horizon, int):
        raise ValueError("indices must be integers")
    if signal_index < 20 or signal_index >= len(bars) or horizon not in (5, 10, 20):
        raise ValueError("invalid signal index or horizon")
    if not isinstance(pivot, (float, int)) or not math.isfinite(pivot) or pivot <= 0:
        raise ValueError("invalid pivot")
    if len(bars) - signal_index - 1 < horizon:
        return {"status": "pending", "horizon_matured": False, "event_date": None}
    for i in range(signal_index + 1, signal_index + horizon + 1):
        current, previous = bars[i], bars[i - 1]
        high, low, close = (float(current[k]) for k in ("high", "low", "close"))
        prev_close = float(previous["close"])
        prior = [float(b["volume"]) for b in bars[i-20:i]]
        if any(v <= 0 for v in prior):
            return {"status": "unverified_volume", "horizon_matured": False,
                    "event_date": None}
        if (high > low and close > pivot * 1.005 and close > prev_close
                and (close - low) / (high - low) >= 0.75
                and float(current["volume"]) >= volume_multiple * sum(prior)/20):
            return {"status": "confirmed", "horizon_matured": True,
                    "event_date": current["date"]}
    return {"status": "not_confirmed", "horizon_matured": True, "event_date": None}


def purged_chronological_indices(events: list[dict], test_start: str,
                                 test_end: str, embargo_sessions: int = 20) -> dict:
    """Split on GLOBAL trading-session ordinal, purging overlapping labels.

    Events require integer signal_session and label_end_session ordinals on a
    single explicitly documented reference trading calendar. A training
    event must have completely matured before test_start minus embargo.
    Test observations are in [test_start, test_end) by ISO date.
    """
    if not isinstance(embargo_sessions, int) or embargo_sessions < 0:
        raise ValueError("invalid embargo")
    begin, stop = date.fromisoformat(test_start), date.fromisoformat(test_end)
    if begin >= stop:
        raise ValueError("invalid split range")
    test = [i for i, row in enumerate(events)
            if begin <= date.fromisoformat(row["signal_date"]) < stop]
    if not test:
        return {"train": [], "test": [], "status": "no_test_events"}
    first_test_ordinal = min(events[i]["signal_session"] for i in test)
    train = []
    for i, row in enumerate(events):
        signal = row["signal_session"]
        end = row["label_end_session"]
        if not isinstance(signal, int) or not isinstance(end, int) or end < signal:
            raise ValueError("invalid event lifetime")
        if end < first_test_ordinal - embargo_sessions:
            train.append(i)
    return {"train": train, "test": test,
            "status": "split_only_not_out_of_sample_validation"}
