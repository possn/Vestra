"""Runtime installer that chains official EDGAR Archives after CompanyFacts.

Keeping this composition in the launcher avoids editing run.py's pipeline call
site. The existing sec_enrich.enrich remains first; Archives only sees rows that
were not already enriched by a successful CompanyFacts response.
"""
from __future__ import annotations

import logging

import sec_archives_enrich


def _archive_candidate_order(rows, priority=None):
    """Return a copy ordered for bounded EDGAR fallback work.

    Priority tickers remain first. Remaining rows are ranked by the number of
    fundamental fields still missing, then by ticker for deterministic runs.
    Objects themselves are not copied, so the Archives enricher can mutate the
    canonical metrics objects without reordering the pipeline's returned list.
    """
    priority = {str(item).upper() for item in (priority or set())}

    def key(metrics_obj):
        ticker = str(getattr(metrics_obj, "ticker", "") or "").upper()
        return (
            0 if ticker in priority else 1,
            -int(sec_archives_enrich._candidate_missing(metrics_obj)),
            ticker,
        )

    return sorted(list(rows or []), key=key)


class _ReplayArchiveClient:
    """Cache budget-planning master-index text for the real enrichment pass."""

    def __init__(self, inner):
        self.inner = inner
        self._text_cache = {}

    @property
    def requests(self):
        return int(getattr(self.inner, "requests", 0) or 0)

    def text(self, url, timeout=25):
        if url in self._text_cache:
            return self._text_cache[url]
        value = self.inner.text(url, timeout=timeout)
        self._text_cache[url] = value
        return value

    def content(self, url, timeout=25):
        return self.inner.content(url, timeout=timeout)


def _effective_nonpriority_cap(rows, cmap, filings, requested, priority=None):
    """Return the raw-row cap needed to reach ``requested`` filing-backed rows.

    sec_archives_enrich historically increments its non-priority counter before
    checking whether the CIK has an eligible filing. A filing-less issuer can
    therefore consume budget without any filing request. We keep the underlying
    parser untouched and calculate the raw-row cap that corresponds to the same
    requested number of *filing-backed* candidates.
    """
    requested = max(0, int(requested))
    if requested == 0:
        return 0
    priority = {str(item).upper() for item in (priority or set())}
    raw_slots = 0
    filing_backed = 0

    for metrics_obj in rows or []:
        ticker = str(getattr(metrics_obj, "ticker", "") or "").upper()
        if not ticker or ticker in priority or "." in ticker:
            continue
        if not sec_archives_enrich.is_equity_candidate(getattr(metrics_obj, "quote_type", None)):
            continue
        if getattr(metrics_obj, "sec_edgar_enriched", False):
            continue
        cik = cmap.get(ticker)
        if not cik:
            continue
        if sec_archives_enrich._candidate_missing(metrics_obj) < 2:
            continue

        raw_slots += 1
        if filings.get(int(cik)):
            filing_backed += 1
            if filing_backed >= requested:
                break
    return raw_slots


def _budgeted_archive_enrich(rows, priority=None, max_nonpriority=None):
    requested = (
        sec_archives_enrich.DEFAULT_MAX_NONPRIORITY
        if max_nonpriority is None
        else max(0, int(max_nonpriority))
    )
    cached_map = sec_archives_enrich._read_ticker_snapshot(sec_archives_enrich.TICKER_MAP_SNAPSHOT)
    if not cached_map:
        return sec_archives_enrich.enrich(rows, priority=priority, max_nonpriority=requested)
    cmap, _snapshot = cached_map

    inner = sec_archives_enrich.ArchiveClient()
    client = _ReplayArchiveClient(inner)
    quarters = sec_archives_enrich.recent_quarters()
    index_texts = []
    planning_complete = True
    for year, quarter in quarters:
        try:
            index_texts.append(client.text(sec_archives_enrich.master_index_url(year, quarter), timeout=30))
        except Exception:
            # Do not make the planning layer a new availability dependency. The
            # normal enricher gets its usual budget and may retry/recover.
            planning_complete = False
            break

    effective = requested
    if planning_complete:
        filings = sec_archives_enrich.latest_filings_by_cik(index_texts)
        if filings:
            effective = _effective_nonpriority_cap(
                rows,
                cmap,
                filings,
                requested,
                priority=priority,
            )
            if effective != requested:
                sec_archives_enrich.log.info(
                    "SEC Archives filing-backed budget: requested=%d raw_cap=%d",
                    requested,
                    effective,
                )

    return sec_archives_enrich.enrich(
        rows,
        priority=priority,
        max_nonpriority=effective,
        client=client,
        quarters=quarters,
    )


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
        ordered = _archive_candidate_order(rows, priority=priority)
        _budgeted_archive_enrich(ordered, priority=priority)
        return rows

    module._vestra_companyfacts_enrich = original
    module.enrich = combined_enrich
    module._vestra_sec_archives_installed = True
    return combined_enrich
