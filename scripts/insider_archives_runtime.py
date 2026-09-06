"""Fallback Form 4 discovery to official SEC Archives when data.sec.gov is blocked.

The SEC endpoint probe deliberately exports an empty ``SEC_USER_AGENT`` only when
all post-CIK API sentinels return 403. In that explicit state, retrying
``data.sec.gov/submissions`` once per US issuer creates hundreds of doomed
requests even though ``www.sec.gov/Archives`` remains reachable.

This runtime adapter changes transport only in that known-blocked state:
- API/submissions remains the preferred path whenever it is available;
- recent Form 4/4-A accessions are discovered once from official quarterly
  ``master.idx`` files, exact CIK only;
- already parsed immutable accessions continue to use insiders.py's existing
  cache;
- only uncached accessions download the immutable full-submission ``.txt`` and
  extract the embedded ownership XML.

No issuer selection, date window, transaction parsing, insider fields, Score or
Risk Gate semantics are changed.
"""
from __future__ import annotations

import datetime as dt
import os
import re

FORM4_FORMS = {"4", "4/A"}
DEFAULT_DAYS = 365
DEFAULT_QUARTERS = 5
_DOCUMENT_RE = re.compile(r"<DOCUMENT>(.*?)</DOCUMENT>", re.I | re.S)
_TYPE_RE = re.compile(r"<TYPE>\s*([^\r\n<]+)", re.I)
_XML_RE = re.compile(r"<XML>(.*?)</XML>", re.I | re.S)
_OWNERSHIP_RE = re.compile(r"(<(?:\?xml[^>]*>\s*)?<ownershipDocument\b.*?</ownershipDocument>)", re.I | re.S)


def _blocked_by_probe(environ=None) -> bool:
    env = os.environ if environ is None else environ
    return "SEC_USER_AGENT" in env and str(env.get("SEC_USER_AGENT") or "").strip() == ""


def _extract_ownership_xml(submission_text: str) -> bytes | None:
    """Extract the Form 4 ownership XML from an immutable SEC submission text."""
    text = str(submission_text or "")
    for block in _DOCUMENT_RE.findall(text):
        type_match = _TYPE_RE.search(block)
        form = str(type_match.group(1) if type_match else "").strip().upper()
        if form not in FORM4_FORMS:
            continue
        xml_match = _XML_RE.search(block)
        candidates = [xml_match.group(1)] if xml_match else [block]
        for candidate in candidates:
            own = _OWNERSHIP_RE.search(candidate)
            if own:
                return own.group(1).strip().encode("utf-8")
    own = _OWNERSHIP_RE.search(text)
    return own.group(1).strip().encode("utf-8") if own else None


def _archive_rows_by_cik(days=DEFAULT_DAYS, quarter_count=DEFAULT_QUARTERS, client=None):
    """Return exact CIK -> recent Form 4 rows from official EDGAR master indexes."""
    from sec_archives_enrich import ARCHIVES_BASE, ArchiveClient, master_index_url, parse_master_index, recent_quarters

    client = client or ArchiveClient()
    cutoff = dt.date.today() - dt.timedelta(days=int(days))
    grouped = {}
    loaded = 0
    for year, quarter in recent_quarters(count=int(quarter_count)):
        try:
            text = client.text(master_index_url(year, quarter), timeout=30)
        except Exception:
            continue
        loaded += 1
        for row in parse_master_index(text, allowed_forms=FORM4_FORMS):
            try:
                filed = dt.date.fromisoformat(str(row.get("filed") or ""))
            except Exception:
                continue
            if filed < cutoff:
                continue
            filename = str(row.get("filename") or "").strip()
            accession = str(row.get("accession") or "").strip()
            if not filename or not accession:
                continue
            grouped.setdefault(str(int(row["cik"])).zfill(10), []).append({
                "filing_date": str(row.get("filed") or ""),
                "accession": accession,
                "primary_document": "",
                "archive_submission_url": f"{ARCHIVES_BASE}{filename}",
            })
    for rows in grouped.values():
        rows.sort(key=lambda item: (item.get("filing_date") or "", item.get("accession") or ""), reverse=True)
    return grouped, loaded


def install(module=None, *, row_loader=None, environ=None):
    """Install the Archives transport only for an explicit uniform-403 probe state."""
    if module is None:
        import insiders as module
    if getattr(module, "_vestra_insider_archives_installed", False):
        return getattr(module, "_vestra_insider_archives_state", None)

    env = os.environ if environ is None else environ
    if not _blocked_by_probe(env):
        module._vestra_insider_archives_installed = True
        module._vestra_insider_archives_state = {"active": False, "reason": "api_not_explicitly_blocked"}
        return module._vestra_insider_archives_state

    row_loader = row_loader or _archive_rows_by_cik
    original_annotate = module.annotate
    original_recent_rows = module._recent_form4_rows
    original_fetch = module._fetch_structured_filing
    state = {"active": True, "rows_by_cik": None, "indexes_loaded": 0, "fallback_failed": False}

    def archive_recent_rows(cik, days):
        rows_by_cik = state.get("rows_by_cik")
        if rows_by_cik is None:
            return original_recent_rows(cik, days)
        return list(rows_by_cik.get(str(cik).zfill(10), []))

    def archive_fetch(cik, filing, ticker):
        url = str((filing or {}).get("archive_submission_url") or "").strip()
        if not url:
            return original_fetch(cik, filing, ticker)

        cached = module._cached_filing(cik, filing, ticker)
        if cached is not None:
            return cached
        try:
            response = module._get(url)
            xml = _extract_ownership_xml(response.text)
            if not xml:
                return [], 0, f"ownership XML not found in {url}"
            parsed, raw_count = module._parse_ownership_xml(xml, ticker, filing["accession"])
            if raw_count > 0 or parsed:
                module._store_cached_filing(cik, filing, parsed, raw_count)
                return parsed, raw_count, "archive_submission"
            return [], 0, f"valid ownership XML contained 0 non-derivative transactions ({url})"
        except Exception as exc:
            return [], 0, f"{type(exc).__name__}: {exc} (url={url})"

    def archive_annotate(tickers, pause=0.0):
        try:
            rows_by_cik, loaded = row_loader()
        except Exception as exc:
            rows_by_cik, loaded = {}, 0
            module.log.warning("Insider Archives discovery failed before Form 4 scan: %s", exc)
        if loaded <= 0:
            state["fallback_failed"] = True
            state["rows_by_cik"] = None
            module.log.warning("Insider Archives discovery unavailable; retaining submissions transport")
        else:
            state["rows_by_cik"] = rows_by_cik
            state["indexes_loaded"] = int(loaded)
            module.log.info(
                "Insider Archives discovery active: %d quarterly indexes; %d CIKs with recent Form 4 filings",
                int(loaded), len(rows_by_cik),
            )
        try:
            return original_annotate(tickers, pause=pause)
        finally:
            state["rows_by_cik"] = None

    module._vestra_original_recent_form4_rows = original_recent_rows
    module._vestra_original_fetch_structured_filing = original_fetch
    module._vestra_original_annotate_before_archives = original_annotate
    module._recent_form4_rows = archive_recent_rows
    module._fetch_structured_filing = archive_fetch
    module.annotate = archive_annotate
    module._vestra_insider_archives_installed = True
    module._vestra_insider_archives_state = state
    return state
