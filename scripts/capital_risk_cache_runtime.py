"""Make capital-risk cache identity independent from SEC transport.

The same immutable SEC filing can be discovered through data.sec.gov/submissions
or through EDGAR Archives master.idx. The canonical scanner previously included
the transport-specific primary document / archive URL in its cache fingerprint,
so switching transport made an unchanged filing set look new and forced a full
rescan. This runtime hook fingerprints only immutable filing identity fields.

No candidate, document limit, phrase scanner, risk flag or score behavior changes.
"""
from __future__ import annotations

import hashlib

CACHE_VERSION = "capital-risk-v3-transport-stable-fingerprint-2026-09-06"


def install(module=None):
    if module is None:
        import capital_risk as module
    if getattr(module, "_vestra_transport_stable_cache_installed", False):
        return module._filings_fingerprint

    def stable_fingerprint(rows):
        parts = []
        for row in rows or []:
            parts.append("\x1f".join((
                str(row.get("accession") or ""),
                str(row.get("date") or ""),
                str(row.get("form") or ""),
            )))
        payload = "\x1e".join(sorted(parts)).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    module.CAPITAL_RISK_SCANNER_VERSION = CACHE_VERSION
    module._filings_fingerprint = stable_fingerprint
    module._vestra_transport_stable_cache_installed = True
    return stable_fingerprint
