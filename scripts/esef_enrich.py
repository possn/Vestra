"""Compatibility shim for official European filing enrichment.

The public pipeline imports ``esef_enrich.enrich``. This shim deliberately owns
only the official filings.xbrl.org / UKSEF pass. Yahoo annual and quarterly
statement recovery is orchestrated once by ``run.py`` immediately afterwards.
Keeping those fallbacks out of this shim prevents duplicate statement requests,
which otherwise amplify Yahoo throttling without adding evidence.

The official adapter remains fail-closed and fills only missing values.
"""
from __future__ import annotations

from esef_enrich_v416 import enrich as _enrich_esef


def enrich(raw, priority=None, max_nonpriority=180):
    priority_set = {str(x or "").upper() for x in (priority or [])}
    return _enrich_esef(raw, priority=priority_set, max_nonpriority=max_nonpriority)


__all__ = ["enrich"]
