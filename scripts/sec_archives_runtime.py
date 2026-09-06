"""Runtime installer that chains official EDGAR Archives after CompanyFacts.

Keeping this composition in the launcher avoids editing run.py's pipeline call
site. The existing sec_enrich.enrich remains first; Archives only sees rows that
were not already enriched by a successful CompanyFacts response.
"""
from __future__ import annotations

import logging

import sec_archives_enrich


def _archive_candidate_order(rows, priority=None):
    """Return a copy ordered for bounded EDGAR fallback work.

    Priority tickers remain first. Remaining rows are ranked by the number of
    fundamental fields still missing, then by ticker for deterministic runs.
    Objects themselves are not copied, so the Archives enricher can mutate the
    canonical metrics objects without reordering the pipeline's returned list.
    """
    priority = {str(item).upper() for item in (priority or set())}

    def key(metrics_obj):
        ticker = str(getattr(metrics_obj, "ticker", "") or "").upper()
        return (
            0 if ticker in priority else 1,
            -int(sec_archives_enrich._candidate_missing(metrics_obj)),
            ticker,
        )

    return sorted(list(rows or []), key=key)


def install(module=None):
    if module is None:
        import sec_enrich as module
    if getattr(module, "_vestra_sec_archives_installed", False):
        return module.enrich

    original = module.enrich
    sec_archives_enrich.log.setLevel(logging.INFO)

    def combined_enrich(raw, *args, **kwargs):
        rows = original(raw, *args, **kwargs)
        priority = kwargs.get("priority")
        ordered = _archive_candidate_order(rows, priority=priority)
        sec_archives_enrich.enrich(ordered, priority=priority)
        return rows

    module._vestra_companyfacts_enrich = original
    module.enrich = combined_enrich
    module._vestra_sec_archives_installed = True
    return combined_enrich
