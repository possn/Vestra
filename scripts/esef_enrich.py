"""Compatibility shim for official European filing enrichment.

The public pipeline imports ``esef_enrich.enrich``. This shim deliberately owns
only the official filings.xbrl.org / UKSEF pass. Yahoo annual and quarterly
statement recovery is orchestrated once by ``run.py`` immediately afterwards.
Keeping those fallbacks out of this shim prevents duplicate statement requests,
which otherwise amplify Yahoo throttling without adding evidence.

The official adapter remains fail-closed and fills only missing values. The
London Stock Exchange resolver already keeps bounded in-memory diagnostics; this
shim emits them after each official pass so a production run can distinguish
network/API failures from exact-identity misses without making extra requests.
"""
from __future__ import annotations

import logging

from esef_enrich_v416 import enrich as _enrich_esef
from lse_identity import diagnostics as _lse_diagnostics

log = logging.getLogger("esef_enrich")


def enrich(raw, priority=None, max_nonpriority=180):
    priority_set = {str(x or "").upper() for x in (priority or [])}
    enriched = _enrich_esef(raw, priority=priority_set, max_nonpriority=max_nonpriority)
    lse_diag = _lse_diagnostics()
    if lse_diag:
        log.info("LSE identity diagnostics: %s", lse_diag)
    else:
        log.info("LSE identity diagnostics: no LSE identity requests recorded")
    return enriched


__all__ = ["enrich"]
