"""Runtime installer that chains official EDGAR Archives after CompanyFacts.

Keeping this composition in the launcher avoids editing run.py's pipeline call
site. The existing sec_enrich.enrich remains first; Archives only sees rows that
were not already enriched by a successful CompanyFacts response.
"""
from __future__ import annotations

import logging

import sec_archives_enrich


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
        return sec_archives_enrich.enrich(rows, priority=priority)

    module._vestra_companyfacts_enrich = original
    module.enrich = combined_enrich
    module._vestra_sec_archives_installed = True
    return combined_enrich
