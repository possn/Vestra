"""Exact Yahoo ticker -> ISIN resolution from official Euronext equity listings.

This is a fallback identity source for ESEF enrichment when Yahoo does not
provide an ISIN. It queries the public Euronext equities list with the exact
trading symbol, validates the expected market for the Yahoo suffix, and accepts
only one unique valid ISIN. There is no issuer-name or fuzzy matching.

Supported markets are the Euronext venues already represented by Vestra's
Yahoo suffix map: Paris, Amsterdam, Brussels, Lisbon, Milan and Oslo. Network or
HTML-layout failures degrade to ``None`` and never block the pipeline.
"""
from __future__ import annotations

from io import StringIO
import logging
import re

log = logging.getLogger("euronext_identity")

EURONEXT_EQUITIES_URL = "https://live.euronext.com/en/products/equities/list"
UA = "Vestra/4.23 (+https://github.com/possn/Vestra)"
ISIN_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")
SYMBOL_RE = re.compile(r"^[A-Z0-9][A-Z0-9.\-]{0,19}$")

SUFFIX_MARKET = {
    ".PA": "Euronext Paris",
    ".AS": "Euronext Amsterdam",
    ".BR": "Euronext Brussels",
    ".LS": "Euronext Lisbon",
    ".MI": "Euronext Milan",
    ".OL": "Oslo Børs",
}

_CACHE: dict[str, str | None] = {}
_LAST_DIAGNOSTICS: dict[str, int] = {}


def _session():
    import requests

    s = requests.Session()
    s.headers.update({
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
        "Referer": "https://live.euronext.com/",
    })
    return s


def _parts(ticker: str) -> tuple[str, str] | None:
    text = str(ticker or "").strip().upper()
    for suffix, market in SUFFIX_MARKET.items():
        if text.endswith(suffix):
            symbol = text[: -len(suffix)]
            if symbol and SYMBOL_RE.match(symbol):
                return symbol, market
            return None
    return None


def _norm_col(value) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").strip().lower()).strip()


def _market_matches(actual: str, expected: str) -> bool:
    a = " ".join(str(actual or "").replace("ø", "o").replace("Ø", "O").split()).casefold()
    e = " ".join(str(expected or "").replace("ø", "o").replace("Ø", "O").split()).casefold()
    return a == e or a.startswith(e + " ")


def _extract_exact_isin(body: str, symbol: str, expected_market: str) -> str | None:
    """Parse Euronext tables and accept one exact symbol+market identity only."""
    try:
        import pandas as pd

        tables = pd.read_html(StringIO(str(body or "")))
    except Exception:
        return None

    matches: set[str] = set()
    for df in tables:
        columns = {str(c): _norm_col(c) for c in df.columns}
        symbol_col = next((raw for raw, norm in columns.items() if norm in {"symbol", "ticker"}), None)
        isin_col = next((raw for raw, norm in columns.items() if norm == "isin"), None)
        market_col = next((raw for raw, norm in columns.items() if norm == "market"), None)
        if not symbol_col or not isin_col or not market_col:
            continue
        for _, row in df.iterrows():
            returned_symbol = str(row.get(symbol_col) or "").strip().upper()
            if returned_symbol != symbol:
                continue
            if not _market_matches(str(row.get(market_col) or ""), expected_market):
                continue
            isin = str(row.get(isin_col) or "").strip().upper()
            if ISIN_RE.match(isin):
                matches.add(isin)

    return next(iter(matches)) if len(matches) == 1 else None


def diagnostics() -> dict[str, int]:
    return dict(_LAST_DIAGNOSTICS)


def resolve_isin(ticker: str, session=None, refresh: bool = False) -> str | None:
    parts = _parts(ticker)
    if not parts:
        return None
    symbol, expected_market = parts
    cache_key = str(ticker or "").strip().upper()
    if not refresh and cache_key in _CACHE:
        return _CACHE[cache_key]

    _LAST_DIAGNOSTICS["requests"] = _LAST_DIAGNOSTICS.get("requests", 0) + 1
    try:
        s = session or _session()
        r = s.get(
            EURONEXT_EQUITIES_URL,
            params={"combine": symbol},
            timeout=25,
        )
        r.raise_for_status()
        isin = _extract_exact_isin(r.text, symbol, expected_market)
    except Exception as exc:
        _LAST_DIAGNOSTICS["failures"] = _LAST_DIAGNOSTICS.get("failures", 0) + 1
        log.debug("Euronext identity unavailable for %s: %s", cache_key, exc)
        isin = None

    if isin:
        _LAST_DIAGNOSTICS["hits"] = _LAST_DIAGNOSTICS.get("hits", 0) + 1
    else:
        _LAST_DIAGNOSTICS["misses"] = _LAST_DIAGNOSTICS.get("misses", 0) + 1
    _CACHE[cache_key] = isin
    return isin


__all__ = ["resolve_isin", "diagnostics", "SUFFIX_MARKET"]
