"""Correct the bounded SEC capital-risk document selection order.

capital_risk._scan_docs intentionally prioritises filing classes before applying
its max-doc budget, but its internal secondary sort is oldest-first. This runtime
adapter preserves the exact existing class priority and risk rules while choosing
the newest filings inside each class before handing the bounded subset to the
canonical scanner.

Because the canonical scanner receives at most ``max_docs`` rows, its subsequent
sort cannot evict a newer filing from the selected evidence set. No flag rules,
severity logic, date window, issuer selection, Score or Risk Gate cap changes.
"""
from __future__ import annotations

FORM_PRIORITY = {
    "8-K": 0,
    "6-K": 0,
    "424B5": 1,
    "424B3": 1,
    "S-3": 2,
    "F-3": 2,
    "S-1": 2,
    "F-1": 2,
    "10-K": 3,
    "20-F": 3,
    "DEF 14A": 4,
}


def select_recent_priority(rows, max_docs=8):
    """Keep form-class priority, newest-first inside each priority class."""
    limit = max(0, int(max_docs))
    if limit == 0:
        return []
    ranked = [dict(row) for row in (rows or []) if isinstance(row, dict)]
    # Stable two-pass sort: recency descending first, then form class ascending.
    ranked.sort(key=lambda row: str(row.get("date") or ""), reverse=True)
    ranked.sort(key=lambda row: FORM_PRIORITY.get(str(row.get("form") or ""), 9))
    return ranked[:limit]


def install(module=None):
    if module is None:
        import capital_risk as module
    if getattr(module, "_vestra_capital_risk_scan_order_installed", False):
        return module._scan_docs

    original = module._scan_docs

    def recent_first_scan(client, cik, rows, max_docs=8):
        selected = select_recent_priority(rows, max_docs=max_docs)
        return original(client, cik, selected, max_docs=max_docs)

    module._vestra_original_scan_docs_before_recency_fix = original
    module._scan_docs = recent_first_scan
    module._vestra_capital_risk_scan_order_installed = True
    return recent_first_scan
