"""Prefer the official LSE identity endpoint for London-listed ESEF rows.

The canonical ESEF adapter historically asks Yahoo for ISIN first for every
eligible issuer and only falls back to the London Stock Exchange for ``*.L``
names. That is backwards for London equities: the official exact-TIDM endpoint
is the stronger identity source and avoids an unnecessary Yahoo request during a
pipeline already subject to Yahoo throttling. Non-London behavior is unchanged.
"""
from __future__ import annotations


def install(module=None):
    if module is None:
        import esef_enrich_v416 as module
    if getattr(module, "_vestra_lse_first_identity_installed", False):
        return module.resolve_isin_with_source

    original = module.resolve_isin_with_source

    def lse_first(ticker, session=None):
        text = str(ticker or "").strip().upper()
        if text.endswith(".L"):
            try:
                isin = module.resolve_lse_isin(text, session)
            except Exception:
                isin = None
            if isin:
                isin = str(isin).strip().upper()
                if module.ISIN_RE.match(isin):
                    return isin, "London Stock Exchange official instrument API"
        return original(ticker, session)

    module._vestra_original_resolve_isin_with_source = original
    module.resolve_isin_with_source = lse_first
    module._vestra_lse_first_identity_installed = True
    return lse_first
