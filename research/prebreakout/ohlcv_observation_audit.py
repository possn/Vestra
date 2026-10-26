#!/usr/bin/env python3
"""Independent OHLCV observation audit. It does not authenticate vendors or certify alpha."""
from __future__ import annotations
from collections import Counter
from datetime import date
from decimal import Decimal, InvalidOperation

REQUIRED = ("symbol", "session", "open", "high", "low", "close", "volume")


def audit_ohlcv_rows(rows, *, reference_sessions, evaluation_date=None):
    """Fail closed for malformed prices, duplicates and out-of-calendar observations.

    Sessions are ISO dates. The caller MUST supply an independently audited
    exchange calendar; passing a calendar derived from rows defeats this check.
    No assumption is made that missing sessions imply missing trades: a suspended,
    delisted or not-yet-listed security requires separate point-in-time verification.
    """
    failures = []
    if reference_sessions is None:
        return {"admitted": False, "failures": ["missing_reference_sessions"], "rows": 0}
    try:
        calendar = [date.fromisoformat(s) for s in reference_sessions]
        if not calendar or len(calendar) != len(set(calendar)) or calendar != sorted(calendar):
            failures.append("invalid_reference_sessions")
        cutoff = date.fromisoformat(evaluation_date) if evaluation_date else None
    except (TypeError, ValueError, AttributeError):
        return {"admitted": False, "failures": ["invalid_reference_sessions_or_cutoff"], "rows": 0}
    valid_sessions = set(calendar)
    seen = set()
    counts = Counter()
    previous = {}
    count = 0
    try:
        iterator = iter(rows)
    except TypeError:
        return {"admitted": False, "failures": ["invalid_rows"], "rows": 0}
    for row in iterator:
        count += 1
        if not isinstance(row, dict) or any(k not in row for k in REQUIRED):
            failures.append("invalid_row_schema")
            continue
        symbol = row["symbol"]
        if not isinstance(symbol, str) or not symbol.strip():
            failures.append("invalid_symbol")
            continue
        try:
            d = date.fromisoformat(row["session"])
        except (TypeError, ValueError):
            failures.append("invalid_session")
            continue
        if d not in valid_sessions:
            failures.append("session_outside_calendar")
        if cutoff and d > cutoff:
            failures.append("future_session")
        key = (symbol, d)
        if key in seen:
            failures.append("duplicate_symbol_session")
        seen.add(key)
        if symbol in previous and d <= previous[symbol]:
            failures.append("nonmonotonic_symbol_sessions")
        previous[symbol] = d
        values = {}
        for k in ("open", "high", "low", "close", "volume"):
            try:
                v = Decimal(str(row[k]))
                if not v.is_finite():
                    raise InvalidOperation()
                values[k] = v
            except (InvalidOperation, ValueError, TypeError):
                failures.append("invalid_numeric")
                break
        if len(values) != 5:
            continue
        o, h, l, c, v = (values[k] for k in ("open", "high", "low", "close", "volume"))
        if min(o, h, l, c) <= 0 or v < 0:
            failures.append("invalid_price_or_volume")
        if h < max(o, c, l) or l > min(o, c, h):
            failures.append("inconsistent_ohlc")
        counts[symbol] += 1
    if not count:
        failures.append("empty_rows")
    return {
        "admitted": not failures,
        "failures": sorted(set(failures)),
        "rows": count,
        "symbols": len(counts),
        "interpretation": "structural_ohlcv_audit_only_not_pit_vendor_or_alpha_certification",
    }
