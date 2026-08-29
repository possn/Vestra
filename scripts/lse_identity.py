"""Exact UK ticker -> ISIN resolution from official London Stock Exchange files.

The LSE publishes weekly XLS/XLSX security lists for SETS, SETSqx and EQS.
This module discovers those official downloads, builds an exact TIDM -> ISIN map,
and exposes a conservative resolver for Yahoo-style ``*.L`` tickers.

No fuzzy company-name matching is allowed. Ambiguous TIDMs are discarded.
Network or workbook failures degrade to ``None`` and never block the pipeline.
"""
from __future__ import annotations

import io
import logging
import re
from urllib.parse import urljoin

import pandas as pd
import requests

log = logging.getLogger("lse_identity")

LSE_SECURITIES_PAGE = (
    "https://www.londonstockexchange.com/equities-trading/asset-classes/"
    "shares-trading/uk-and-european-securities"
)
UA = "Vestra/4.20 (+https://github.com/possn/Vestra)"
ISIN_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")
_DOWNLOAD_RE = re.compile(
    r"href=[\"']([^\"']+\.(?:xlsx|xls)(?:\?[^\"']*)?)[\"']",
    re.IGNORECASE,
)

_CACHE: dict[str, str] | None = None


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept": "text/html,application/xhtml+xml,*/*;q=0.8"})
    return s


def _norm_col(value) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").strip().lower()).strip()


def _discover_workbook_urls(session: requests.Session) -> list[str]:
    try:
        r = session.get(LSE_SECURITIES_PAGE, timeout=25)
        r.raise_for_status()
    except Exception as exc:
        log.warning("LSE securities page unavailable: %s", exc)
        return []

    urls = []
    for href in _DOWNLOAD_RE.findall(r.text or ""):
        url = urljoin(LSE_SECURITIES_PAGE, href)
        low = url.lower()
        # Limit the resolver to the official share-trading security lists. Other
        # LSE workbooks on the page (business parameters, market makers, etc.)
        # are irrelevant and can contain unrelated codes.
        if any(token in low for token in ("sets", "setsqx", "eqs", "securit")):
            urls.append(url)
    return list(dict.fromkeys(urls))


def _pick_columns(df: pd.DataFrame) -> tuple[str | None, str | None]:
    columns = {str(c): _norm_col(c) for c in df.columns}
    isin_col = next((raw for raw, norm in columns.items() if norm == "isin" or "isin code" in norm), None)
    code_priority = (
        "tidm", "epic", "tradable instrument display mnemonic",
        "display mnemonic", "mnemonic", "code", "symbol",
    )
    code_col = None
    for wanted in code_priority:
        code_col = next((raw for raw, norm in columns.items() if norm == wanted), None)
        if code_col:
            break
    return code_col, isin_col


def _pairs_from_workbook(content: bytes) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    try:
        book = pd.ExcelFile(io.BytesIO(content))
    except Exception as exc:
        log.debug("LSE workbook open failed: %s", exc)
        return pairs

    for sheet in book.sheet_names:
        try:
            df = book.parse(sheet_name=sheet, dtype=str)
        except Exception:
            continue
        code_col, isin_col = _pick_columns(df)
        if not code_col or not isin_col:
            continue
        for code, isin in zip(df[code_col], df[isin_col]):
            tidm = str(code or "").strip().upper()
            isin_text = str(isin or "").strip().upper()
            if not tidm or tidm in {"NAN", "NONE"}:
                continue
            if not ISIN_RE.match(isin_text):
                continue
            pairs.append((tidm, isin_text))
    return pairs


def build_map(session: requests.Session | None = None) -> dict[str, str]:
    s = session or _session()
    candidates: dict[str, set[str]] = {}
    urls = _discover_workbook_urls(s)
    for url in urls:
        try:
            r = s.get(url, timeout=35)
            r.raise_for_status()
            pairs = _pairs_from_workbook(r.content)
        except Exception as exc:
            log.debug("LSE workbook unavailable %s: %s", url, exc)
            continue
        for tidm, isin in pairs:
            candidates.setdefault(tidm, set()).add(isin)

    # One TIDM must identify exactly one ISIN. Ambiguous rows are deliberately
    # excluded instead of guessing which instrument the Yahoo ticker meant.
    resolved = {tidm: next(iter(isins)) for tidm, isins in candidates.items() if len(isins) == 1}
    log.info("LSE identity map: %d exact TIDM->ISIN mappings from %d workbook(s)", len(resolved), len(urls))
    return resolved


def get_map(session: requests.Session | None = None, refresh: bool = False) -> dict[str, str]:
    global _CACHE
    if refresh or _CACHE is None:
        _CACHE = build_map(session)
    return _CACHE


def resolve_isin(ticker: str, session: requests.Session | None = None) -> str | None:
    text = str(ticker or "").strip().upper()
    if not text.endswith(".L"):
        return None
    tidm = text[:-2]
    mapping = get_map(session)
    # Yahoo sometimes represents a London share class with '-' while the LSE
    # TIDM can contain '.'. Both candidates remain exact lookups.
    candidates = list(dict.fromkeys((tidm, tidm.replace("-", "."))))
    matches = {mapping[c] for c in candidates if c in mapping}
    return next(iter(matches)) if len(matches) == 1 else None


__all__ = ["build_map", "get_map", "resolve_isin"]
