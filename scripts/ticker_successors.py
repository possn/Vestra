"""Exact corporate-action ticker successor map.

Historical portfolio symbols remain canonical for reconciliation, while current
market retrieval may use an officially confirmed successor ticker. Entries are
manual, exact and source-backed; no fuzzy/name-based inference is allowed.
"""
from __future__ import annotations

TICKER_SUCCESSORS = {
    "BITF": {
        "successor": "KEEL",
        "quote_type": "EQUITY",
        "effective_date": "2026-04-06",
        "source": "Keel Infrastructure / Bitfarms official rebrand",
    },
    "IINN": {
        "successor": "QTEX",
        "quote_type": "EQUITY",
        "effective_date": "2026-05-20",
        "source": "Inspira Technologies official Nasdaq ticker change",
    },
}


def successor_for(ticker):
    key = str(ticker or "").strip().upper()
    row = TICKER_SUCCESSORS.get(key)
    return dict(row) if row else None


def retrieval_symbol(ticker):
    key = str(ticker or "").strip().upper()
    row = TICKER_SUCCESSORS.get(key)
    return str(row.get("successor") if row else key).strip().upper()


__all__ = ["TICKER_SUCCESSORS", "successor_for", "retrieval_symbol"]
