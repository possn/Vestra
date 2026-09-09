"""Runtime installer that chains official EDGAR Archives after CompanyFacts.

Keeping this composition in the launcher avoids editing run.py's pipeline call
site. The existing sec_enrich.enrich remains first; Archives only sees rows that
were not already enriched by a successful CompanyFacts response.
"""
from __future__ import annotations

import logging

import sec_archives_enrich


# Run #96 attempted 511 Archive candidates because priority holdings were exempt
# from the 300 non-priority cap. Keep the balanced total below that observed
# workload while reserving meaningful capacity for scanner dossiers. Run #98
# showed that requiring two missing fields was too restrictive (313 eligible,
# only 259 published SEC rows), so any genuine remaining fundamental gap is now
# eligible; ranking + the 500-row ceiling still keep work bounded.
ARCHIVE_TOTAL_CANDIDATE_BUDGET = 500
ARCHIVE_PRIORITY_SHARE = 0.40
ARCHIVE_MIN_MISSING = 1


def _is_archive_candidate(metrics_obj):
    ticker = str(getattr(metrics_obj, "ticker", "") or "").upper()
    if not ticker or "." in ticker:
        return False
    if not sec_archives_enrich.is_equity_candidate(getattr(metrics_obj, "quote_type", None)):
        return False
    if getattr(metrics_obj, "sec_edgar_enriched", False):
        return False
    return int(sec_archives_enrich._candidate_missing(metrics_obj)) >= ARCHIVE_MIN_MISSING


def _archive_candidate_order(rows, priority=None):
    """Return incomplete US equity candidates ordered for bounded EDGAR fallback.

    Priority tickers remain first, but a fully covered holding does not consume
    the budget merely because it is in the portfolio. Remaining rows are ranked
    by missing fundamentals, then ticker for deterministic runs.
    Objects themselves are not copied.
    """
    priority = {str(item).upper() for item in (priority or set())}
    candidates = [row for row in (rows or []) if _is_archive_candidate(row)]

    def key(metrics_obj):
        ticker = str(getattr(metrics_obj, "ticker", "") or "").upper()
        return (
            0 if ticker in priority else 1,
            -int(sec_archives_enrich._candidate_missing(metrics_obj)),
            ticker,
        )

    return sorted(candidates, key=key)


def _balanced_archive_candidates(rows, priority=None, total_budget=ARCHIVE_TOTAL_CANDIDATE_BUDGET,
                                 priority_share=ARCHIVE_PRIORITY_SHARE):
    """Select a bounded mixture of incomplete holdings and scanner rows.

    The portfolio keeps a reserved share, while the scanner keeps the rest.
    Unused capacity is handed to the other pool, ranked by missing fundamentals.
    Total selected work never exceeds ``total_budget``.
    """
    priority_set = {str(item).upper() for item in (priority or set())}
    total_budget = max(0, int(total_budget))
    priority_share = min(1.0, max(0.0, float(priority_share)))
    if total_budget == 0:
        return [], set()

    eligible = [row for row in (rows or []) if _is_archive_candidate(row)]

    def gap_key(metrics_obj):
        return (
            -int(sec_archives_enrich._candidate_missing(metrics_obj)),
            str(getattr(metrics_obj, "ticker", "") or "").upper(),
        )

    priority_pool = sorted(
        [row for row in eligible if str(getattr(row, "ticker", "") or "").upper() in priority_set],
        key=gap_key,
    )
    scanner_pool = sorted(
        [row for row in eligible if str(getattr(row, "ticker", "") or "").upper() not in priority_set],
        key=gap_key,
    )

    priority_reserve = min(total_budget, int(round(total_budget * priority_share)))
    scanner_reserve = total_budget - priority_reserve
    selected_priority = priority_pool[:priority_reserve]
    selected_scanner = scanner_pool[:scanner_reserve]

    used_ids = {id(row) for row in selected_priority + selected_scanner}
    remaining_slots = total_budget - len(used_ids)
    if remaining_slots > 0:
        overflow = sorted(
            [row for row in eligible if id(row) not in used_ids],
            key=gap_key,
        )
        for row in overflow[:remaining_slots]:
            ticker = str(getattr(row, "ticker", "") or "").upper()
            if ticker in priority_set:
                selected_priority.append(row)
            else:
                selected_scanner.append(row)

    selected = sorted(
        selected_priority + selected_scanner,
        key=lambda row: (
            0 if str(getattr(row, "ticker", "") or "").upper() in priority_set else 1,
            *gap_key(row),
        ),
    )
    selected_priority_set = {
        str(getattr(row, "ticker", "") or "").upper() for row in selected_priority
    }
    sec_archives_enrich.log.info(
        "SEC Archives candidate selector: eligible=%d selected=%d priority=%d scanner=%d budget=%d",
        len(eligible), len(selected), len(selected_priority), len(selected_scanner), total_budget,
    )
    return selected, selected_priority_set


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
        if sec_archives_enrich._candidate_missing(metrics_obj) < ARCHIVE_MIN_MISSING:
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
        selected, selected_priority = _balanced_archive_candidates(rows, priority=priority)
        scanner_count = max(0, len(selected) - len(selected_priority))
        _budgeted_archive_enrich(
            selected,
            priority=selected_priority,
            max_nonpriority=scanner_count,
        )
        return rows

    module._vestra_companyfacts_enrich = original
    module.enrich = combined_enrich
    module._vestra_sec_archives_installed = True
    return combined_enrich