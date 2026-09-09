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

A previously published ESEF row is also an exact identity cache. ISIN + LEI are
stable issuer identifiers, so the same ticker may reuse them on the next run when
(and only when) the previous row explicitly cites ESEF / filings.xbrl.org. This
avoids re-resolving an already verified identity through Yahoo/GLEIF every day,
while remaining fail-closed and never matching issuers by company name.
"""
from __future__ import annotations

import json
import logging
import os
import re

from esef_enrich_v416 import enrich as _enrich_esef
from lse_identity import diagnostics as _lse_diagnostics

log = logging.getLogger("esef_enrich")

_DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "stocks.json")
_ISIN_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")
_LEI_RE = re.compile(r"^[A-Z0-9]{20}$")
_ESEF_SOURCE = "ESEF / filings.xbrl.org"


def _verified_identity_cache(path=_DATA_PATH):
    """Return exact ticker -> (ISIN, LEI) from previously verified ESEF rows."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            payload = json.load(fh)
    except Exception:
        return {}

    rows = payload.get("stocks") if isinstance(payload, dict) else None
    if not isinstance(rows, list):
        return {}

    out = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        ticker = str(row.get("ticker") or "").strip().upper()
        sources = row.get("data_sources") or []
        isin = str(row.get("isin") or "").strip().upper()
        lei = str(row.get("lei") or "").strip().upper()
        if not ticker or _ESEF_SOURCE not in sources:
            continue
        if not _ISIN_RE.match(isin) or not _LEI_RE.match(lei):
            continue
        out[ticker] = (isin, lei)
    return out


def _attach_verified_identities(raw, cache):
    hits = 0
    for model in raw:
        ticker = str(getattr(model, "ticker", "") or "").strip().upper()
        identity = cache.get(ticker)
        if not identity:
            continue
        # Temporary private markers are consumed by the official adapter and do
        # not become a new evidence source in the published dossier.
        setattr(model, "_verified_esef_isin", identity[0])
        setattr(model, "_verified_esef_lei", identity[1])
        hits += 1
    return hits


def enrich(raw, priority=None, max_nonpriority=180):
    priority_set = {str(x or "").upper() for x in (priority or [])}
    identity_cache = _verified_identity_cache()
    cache_hits = _attach_verified_identities(raw, identity_cache)
    if cache_hits:
        log.info("Prior verified ESEF identity cache: %d exact ticker hit(s)", cache_hits)

    enriched = _enrich_esef(raw, priority=priority_set, max_nonpriority=max_nonpriority)
    lse_diag = _lse_diagnostics()
    if lse_diag:
        log.info("LSE identity diagnostics: %s", lse_diag)
    else:
        log.info("LSE identity diagnostics: no LSE identity requests recorded")
    return enriched


__all__ = ["enrich"]
