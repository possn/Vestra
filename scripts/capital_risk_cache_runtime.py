"""Make capital-risk cache identity independent from SEC transport.

The same immutable SEC filing can be discovered through data.sec.gov/submissions
or through EDGAR Archives master.idx. The canonical scanner previously included
the transport-specific primary document / archive URL in its cache fingerprint,
so switching transport made an unchanged filing set look new and forced a full
rescan. This runtime hook fingerprints only immutable filing identity fields.

A one-generation migration from the v2 cache is allowed only when today's exact
v2 fingerprint still matches the stored v2 fingerprint. If transport changed,
any filing changed, or the legacy record is otherwise ambiguous, migration fails
closed and the issuer is rescanned normally.

No candidate, document limit, phrase scanner, risk flag or score behavior changes.
"""
from __future__ import annotations

import hashlib
import json

CACHE_VERSION = "capital-risk-v3-transport-stable-fingerprint-2026-09-06"
LEGACY_CACHE_VERSION = "capital-risk-v2-archives-fallback-2026-09-06"


def _fingerprint(rows, include_transport: bool) -> str:
    parts = []
    for row in rows or []:
        fields = [
            str(row.get("accession") or ""),
            str(row.get("date") or ""),
            str(row.get("form") or ""),
        ]
        if include_transport:
            fields.append(str(row.get("doc") or row.get("archive_url") or ""))
        parts.append("\x1f".join(fields))
    payload = "\x1e".join(sorted(parts)).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def stable_fingerprint(rows) -> str:
    return _fingerprint(rows, include_transport=False)


def legacy_fingerprint(rows) -> str:
    return _fingerprint(rows, include_transport=True)


def install(module=None):
    if module is None:
        import capital_risk as module
    if getattr(module, "_vestra_transport_stable_cache_installed", False):
        return module._filings_fingerprint

    original_apply_previous = module._apply_previous_if_unchanged
    legacy_by_stable = {}

    def observed_stable_fingerprint(rows):
        stable = stable_fingerprint(rows)
        legacy_by_stable[stable] = legacy_fingerprint(rows)
        return stable

    def load_previous_with_safe_v2_migration(path=None):
        source = path or module.CACHE_PATH
        try:
            with open(source, "r", encoding="utf-8") as fh:
                payload = json.load(fh)
        except Exception:
            return {}
        version = str(payload.get("scanner_version") or "")
        if version not in {CACHE_VERSION, LEGACY_CACHE_VERSION}:
            return {}
        rows = payload.get("rows") or {}
        return {
            str(ticker).strip().upper(): dict(row)
            for ticker, row in rows.items()
            if ticker and isinstance(row, dict)
        }

    def apply_previous_with_safe_v2_migration(m, previous, fingerprint):
        if not isinstance(previous, dict):
            return False
        version = str(previous.get("scanner_version") or "")
        if version == CACHE_VERSION:
            return original_apply_previous(m, previous, fingerprint)
        if version != LEGACY_CACHE_VERSION:
            return False
        expected_legacy = legacy_by_stable.get(str(fingerprint))
        if not expected_legacy or previous.get("filings_fingerprint") != expected_legacy:
            return False
        for key in module.CACHE_FIELDS:
            setattr(m, key, previous.get(key))
        setattr(m, "capital_risk_checked", True)
        setattr(m, "capital_risk_reused", True)
        return True

    module.CAPITAL_RISK_SCANNER_VERSION = CACHE_VERSION
    module._filings_fingerprint = observed_stable_fingerprint
    module._load_previous = load_previous_with_safe_v2_migration
    module._apply_previous_if_unchanged = apply_previous_with_safe_v2_migration
    module._vestra_transport_stable_cache_installed = True
    module._vestra_legacy_cache_version = LEGACY_CACHE_VERSION
    return observed_stable_fingerprint


__all__ = [
    "CACHE_VERSION",
    "LEGACY_CACHE_VERSION",
    "stable_fingerprint",
    "legacy_fingerprint",
    "install",
]
