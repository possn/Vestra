"""Compatibility shim for European enrichment.

The public pipeline imports ``esef_enrich.enrich``. v4.18 keeps that stable
while chaining the current filings.xbrl.org adapter with two bounded Yahoo
statement fallbacks: annual first, then quarterly/TTM for the residual gaps.
German listings are promoted because filings.xbrl.org coverage for Germany is
known to be incomplete.

No source overwrites an observed value: all enrichers only fill missing fields.
"""
from __future__ import annotations

from esef_enrich_v416 import enrich as _enrich_esef
from gap_retrieval import enrich as _enrich_gap
from quarterly_gap_retrieval import enrich as _enrich_quarterly_gap


def enrich(raw, priority=None, max_nonpriority=180):
    priority_set = {str(x or "").upper() for x in (priority or [])}

    # 1) Exact ISIN -> LEI -> ESEF/UKSEF identity and official IFRS facts.
    raw = _enrich_esef(raw, priority=priority_set, max_nonpriority=max_nonpriority)

    # 2) Annual Yahoo statements for sparse rows. Germany is promoted because
    # public ESEF aggregation is known to be incomplete there.
    german = {
        str(getattr(m, "ticker", "") or "").upper()
        for m in raw
        if str(getattr(m, "ticker", "") or "").upper().endswith(".DE")
    }
    gap_priority = priority_set | german
    raw = _enrich_gap(raw, priority=gap_priority, max_rows=320, threshold=72.0)

    # 3) Quarterly/TTM recovery for whatever is still sparse after the annual
    # pass. This can recover current margins, cash flow and balance-sheet ratios
    # when Yahoo exposes quarterly statements but not a complete annual table.
    raw = _enrich_quarterly_gap(raw, priority=gap_priority, max_rows=220, threshold=65.0)
    return raw


__all__ = ["enrich"]
