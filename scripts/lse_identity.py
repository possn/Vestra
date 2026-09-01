"""Exact UK ticker -> ISIN resolution from official London Stock Exchange data.

Primary identity path: the public LSE instrument endpoint used by the current
price explorer resolves one TIDM directly and returns its ISIN. This avoids
enumerating the entire exchange and remains exact/fail-closed.

The older public workbook discovery remains only as a compatibility fallback.
No fuzzy company-name matching is allowed. Ambiguous identities are discarded.
Network/API/workbook failures degrade to ``None`` and never block the pipeline.
HTTP/spreadsheet dependencies are imported lazily so architecture tests stay light.
"""
from __future__ import annotations

import html
import io
import logging
import re
from urllib.parse import quote, urljoin

log = logging.getLogger("lse_identity")

LSE_BASE = "https://www.londonstockexchange.com"
LSE_API_BASE = "https://api.londonstockexchange.com"
LSE_INSTRUMENT_ENDPOINT = f"{LSE_API_BASE}/api/gw/lse/instruments/alldata"
LSE_DISCOVERY_PAGES = (
    f"{LSE_BASE}/equities-trading/asset-classes/shares-trading/sets",
    f"{LSE_BASE}/equities-trading/asset-classes/shares-trading/setsqx-and-seaq",
    f"{LSE_BASE}/reports?tab=instruments",
    f"{LSE_BASE}/reports?tab=issuers",
    f"{LSE_BASE}/equities-trading/asset-classes/shares-trading/uk-and-european-securities",
)
# Compatibility alias retained for tests/older callers.
LSE_SECURITIES_PAGE = LSE_DISCOVERY_PAGES[-1]
UA = "Vestra/4.22 (+https://github.com/possn/Vestra)"
ISIN_RE = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")
TIDM_RE = re.compile(r"^[A-Z0-9][A-Z0-9.\-]{0,14}$")
_HREF_RE = re.compile(r"href=[\"']([^\"']+)[\"']", re.IGNORECASE)
_XLS_RE = re.compile(r"(?:https?:)?(?:\\?/\\?/|/)[^\"'<>\s]+?\.(?:xlsx|xls)(?:\?[^\"'<>\s]*)?", re.IGNORECASE)

_CACHE: dict[str, str] | None = None
_DIRECT_CACHE: dict[str, str | None] = {}
_LAST_DIAGNOSTICS: dict[str, int] = {}


def _session():
    import requests
    s = requests.Session()
    s.headers.update({
        "User-Agent": UA,
        "Accept": "application/json,text/html,application/xhtml+xml,*/*;q=0.8",
        "Origin": LSE_BASE,
        "Referer": f"{LSE_BASE}/",
    })
    return s


def _norm_col(value) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").strip().lower()).strip()


def _tidm_from_ticker(ticker: str) -> str | None:
    text = str(ticker or "").strip().upper()
    if not text.endswith(".L"):
        return None
    tidm = text[:-2]
    return tidm if TIDM_RE.match(tidm) else None


def _extract_direct_identity(payload, requested_tidm: str) -> tuple[str, str] | None:
    """Validate one official LSE instrument payload without fuzzy matching."""
    if not isinstance(payload, dict):
        return None
    returned_tidm = str(payload.get("tidm") or payload.get("code") or "").strip().upper()
    requested = str(requested_tidm or "").strip().upper()
    if not returned_tidm or returned_tidm != requested:
        return None
    isin = str(payload.get("isin") or "").strip().upper()
    if not ISIN_RE.match(isin):
        return None
    return returned_tidm, isin


def _resolve_direct(ticker: str, session=None, refresh: bool = False) -> str | None:
    """Resolve a Yahoo ``*.L`` ticker using the current official LSE TIDM API."""
    tidm = _tidm_from_ticker(ticker)
    if not tidm:
        return None
    if not refresh and tidm in _DIRECT_CACHE:
        return _DIRECT_CACHE[tidm]

    try:
        s = session or _session()
    except Exception as exc:
        # Dependency-light callers/tests may deliberately inject a prebuilt exact
        # map without installing requests. Preserve that compatibility path.
        log.debug("LSE direct session unavailable for %s: %s", tidm, exc)
        return None

    # A small exact compatibility alternative covers the historic class-share
    # punctuation convention. Conflicting valid answers fail closed.
    candidates = list(dict.fromkeys((tidm, tidm.replace("-", "."))))
    matches: set[str] = set()
    requests_made = 0
    failures = 0
    for candidate in candidates:
        if not TIDM_RE.match(candidate):
            continue
        url = f"{LSE_INSTRUMENT_ENDPOINT}/{quote(candidate, safe='')}"
        requests_made += 1
        try:
            r = s.get(url, timeout=25)
            r.raise_for_status()
            identity = _extract_direct_identity(r.json(), candidate)
        except Exception as exc:
            failures += 1
            log.debug("LSE direct identity unavailable %s: %s", candidate, exc)
            continue
        if identity:
            matches.add(identity[1])

    _LAST_DIAGNOSTICS["direct_requests"] = _LAST_DIAGNOSTICS.get("direct_requests", 0) + requests_made
    _LAST_DIAGNOSTICS["direct_failures"] = _LAST_DIAGNOSTICS.get("direct_failures", 0) + failures
    if len(matches) == 1:
        result = next(iter(matches))
        _DIRECT_CACHE[tidm] = result
        _LAST_DIAGNOSTICS["direct_hits"] = _LAST_DIAGNOSTICS.get("direct_hits", 0) + 1
        return result
    if len(matches) > 1:
        _LAST_DIAGNOSTICS["direct_ambiguous"] = _LAST_DIAGNOSTICS.get("direct_ambiguous", 0) + 1
        log.warning("LSE direct identity returned conflicting ISINs for %s", tidm)
    _DIRECT_CACHE[tidm] = None
    return None


def _candidate_downloads(page_url: str, body: str) -> list[str]:
    # Compatibility fallback only. LSE pages historically used both normal
    # anchors and JSON-embedded document URLs.
    text = html.unescape(str(body or "")).replace("\\/", "/")
    raw = list(_HREF_RE.findall(text)) + list(_XLS_RE.findall(text))
    urls = []
    for href in raw:
        href = str(href or "").strip()
        if not href:
            continue
        if href.startswith("//"):
            href = "https:" + href
        url = urljoin(page_url, href)
        low = url.lower()
        if not low.startswith(("https://www.londonstockexchange.com/", "https://docs.londonstockexchange.com/")):
            continue
        if not re.search(r"\.(?:xlsx|xls)(?:\?|$)", low):
            continue
        if any(token in low for token in ("business-parameter", "business_parameter", "market-maker", "market_maker", "trading-statistic")):
            continue
        if any(token in low for token in ("sets", "setsqx", "seaq", "eqs", "securit", "instrument", "issuer")):
            urls.append(url)
    return list(dict.fromkeys(urls))


def _discover_workbook_urls(session) -> list[str]:
    urls: list[str] = []
    pages_ok = 0
    for page in LSE_DISCOVERY_PAGES:
        try:
            r = session.get(page, timeout=25)
            r.raise_for_status()
            pages_ok += 1
        except Exception as exc:
            log.info("LSE discovery page unavailable %s: %s", page, exc)
            continue
        urls.extend(_candidate_downloads(page, r.text or ""))
    out = list(dict.fromkeys(urls))
    _LAST_DIAGNOSTICS.update({"pages_ok": pages_ok, "workbooks_discovered": len(out)})
    if not out:
        log.info("LSE workbook fallback found 0 workbooks across %d/%d reachable pages", pages_ok, len(LSE_DISCOVERY_PAGES))
    else:
        log.info("LSE workbook fallback: %d workbook(s) across %d reachable page(s)", len(out), pages_ok)
    return out


def _pick_columns(columns) -> tuple[str | None, str | None]:
    normalized = {str(c): _norm_col(c) for c in columns}
    isin_col = next((raw for raw, norm in normalized.items() if norm == "isin" or "isin code" in norm), None)
    code_priority = (
        "tidm", "epic", "tradable instrument display mnemonic",
        "display mnemonic", "mnemonic", "code", "symbol",
    )
    code_col = None
    for wanted in code_priority:
        code_col = next((raw for raw, norm in normalized.items() if norm == wanted), None)
        if code_col:
            break
    return code_col, isin_col


def _pairs_from_workbook(content: bytes) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    try:
        import pandas as pd
        book = pd.ExcelFile(io.BytesIO(content))
    except Exception as exc:
        log.debug("LSE workbook open failed: %s", exc)
        return pairs

    for sheet in book.sheet_names:
        try:
            df = book.parse(sheet_name=sheet, dtype=str)
        except Exception:
            continue
        code_col, isin_col = _pick_columns(df.columns)
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


def build_map(session=None) -> dict[str, str]:
    s = session or _session()
    candidates: dict[str, set[str]] = {}
    urls = _discover_workbook_urls(s)
    parsed = 0
    pair_count = 0
    for url in urls:
        try:
            r = s.get(url, timeout=35)
            r.raise_for_status()
            pairs = _pairs_from_workbook(r.content)
        except Exception as exc:
            log.debug("LSE workbook unavailable %s: %s", url, exc)
            continue
        if pairs:
            parsed += 1
            pair_count += len(pairs)
        for tidm, isin in pairs:
            candidates.setdefault(tidm, set()).add(isin)

    resolved = {tidm: next(iter(isins)) for tidm, isins in candidates.items() if len(isins) == 1}
    ambiguous = sum(1 for isins in candidates.values() if len(isins) > 1)
    _LAST_DIAGNOSTICS.update({
        "workbooks_parsed": parsed,
        "pairs_seen": pair_count,
        "exact_mappings": len(resolved),
        "ambiguous_tidms": ambiguous,
    })
    log.info(
        "LSE workbook identity map: %d exact mappings, %d ambiguous, %d pair(s), %d/%d workbook(s) parsed",
        len(resolved), ambiguous, pair_count, parsed, len(urls),
    )
    return resolved


def get_map(session=None, refresh: bool = False) -> dict[str, str]:
    global _CACHE
    if refresh or _CACHE is None:
        _CACHE = build_map(session)
    return _CACHE


def diagnostics() -> dict[str, int]:
    return dict(_LAST_DIAGNOSTICS)


def resolve_isin(ticker: str, session=None) -> str | None:
    text = str(ticker or "").strip().upper()
    tidm = _tidm_from_ticker(text)
    if not tidm:
        return None

    # Production ESEF passes its live requests session and therefore takes the
    # direct API path. If an exact map was deliberately injected by a caller
    # (legacy tooling/tests), preserve it without opening a network dependency.
    direct = None if session is None and _CACHE is not None else _resolve_direct(text, session)
    if direct:
        return direct

    # Compatibility fallback: exact TIDM mapping only. This path is intentionally
    # secondary because public workbook links are no longer consistently exposed.
    mapping = get_map(session)
    candidates = list(dict.fromkeys((tidm, tidm.replace("-", "."))))
    matches = {mapping[c] for c in candidates if c in mapping}
    return next(iter(matches)) if len(matches) == 1 else None


__all__ = ["build_map", "get_map", "resolve_isin", "diagnostics"]
