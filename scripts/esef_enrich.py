"""Compatibility shim for European enrichment.

The public pipeline imports ``esef_enrich.enrich``.  v4.17 keeps that stable
while chaining the current filings.xbrl.org adapter with the targeted Yahoo
statement fallback.  German listings are promoted in the fallback queue because
filings.xbrl.org coverage for Germany is known to be incomplete.

No source overwrites an observed value: both enrichers only fill missing fields.
"""
from __future__ import annotations

from esef_enrich_v416 import enrich as _enrich_esef
from gap_retrieval import enrich as _enrich_gap


def enrich(raw, priority=None, max_nonpriority=180):
    priority_set = {str(x or "").upper() for x in (priority or [])}

    # First use exact ISIN -> LEI -> ESEF/UKSEF identity and official IFRS facts.
    raw = _enrich_esef(raw, priority=priority_set, max_nonpriority=max_nonpriority)

    # filings.xbrl.org explicitly has incomplete German coverage.  Do not scrape
    # paid/register pages or fuzzy-match issuers; instead promote sparse German
    # listings into the bounded statement fallback queue.  The fallback reads
    # Yahoo statement tables and only derives a metric when all required
    # statement inputs are present.
    german = {
        str(getattr(m, "ticker", "") or "").upper()
        for m in raw
        if str(getattr(m, "ticker", "") or "").upper().endswith(".DE")
    }
    gap_priority = priority_set | german
    raw = _enrich_gap(raw, priority=gap_priority, max_rows=320, threshold=72.0)
    return raw


__all__ = ["enrich"]
