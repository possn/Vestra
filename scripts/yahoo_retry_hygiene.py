"""Retry hygiene for Yahoo fundamentals retrieval.

A hard symbol failure (explicit delisted/no-timezone/404 identity failure) should
not consume the same retry budget as a transient 429, timeout or transport error.
During a real Yahoo throttle, yfinance can also fail the heavy ``info`` endpoint
while ``fast_info``/history still recovers only price/identity. Those rows have no
explicit ``error`` and used to look like successful full-fundamental fetches. This
wrapper gives extremely sparse price-only rows one bounded retry after a recorded
throttle incident, while preserving the usable fallback if the retry is worse.
Nothing is persisted: every ticker is eligible for a fresh first attempt next run.
"""
from __future__ import annotations

import time

HARD_ERROR_MARKERS = (
    "possibly delisted",
    "symbol may be delisted",
    "no timezone found",
    "404 client error",
    "quote not found",
    "no price data found",
)

# Fields normally populated by Yahoo's heavy quoteSummary/info path. Requiring
# *all* of them to be absent keeps the degradation detector intentionally narrow:
# this is not a generic "low coverage" retry policy.
INFO_OBSERVATION_FIELDS = (
    "sector",
    "industry",
    "market_cap",
    "roe",
    "roa",
    "profit_margin",
    "operating_margin",
    "gross_margin",
    "revenue_growth",
    "earnings_growth",
    "free_cash_flow",
    "operating_cash_flow",
    "current_ratio",
    "quick_ratio",
    "debt_to_equity",
    "trailing_pe",
    "forward_pe",
    "price_to_book",
    "enterprise_to_ebitda",
)


def is_hard_symbol_error(error) -> bool:
    text = str(error or "").strip().lower()
    if not text:
        return False
    return any(marker in text for marker in HARD_ERROR_MARKERS)


def _throttle_incident_seen(module) -> bool:
    coordinator = getattr(module, "_rate_limit_coordinator", None)
    snapshot = getattr(coordinator, "snapshot", None)
    if not callable(snapshot):
        return False
    try:
        state = snapshot() or {}
        return int(state.get("strike") or 0) > 0
    except Exception:
        return False


def _info_observation_count(row) -> int:
    if row is None:
        return 0
    return sum(getattr(row, field, None) is not None for field in INFO_OBSERVATION_FIELDS)


def is_suspect_price_only_fallback(row) -> bool:
    """True only for an apparently usable row with price but no info evidence.

    ETF/crypto rows are excluded because their fundamental shape differs by
    design. A row with any normal info-derived observation is not considered a
    silent degradation and is left alone.
    """
    if row is None or getattr(row, "error", None):
        return False
    if getattr(row, "current_price", None) is None:
        return False
    quote_type = str(getattr(row, "quote_type", "") or "").strip().upper()
    if quote_type in {"ETF", "CRYPTO", "MUTUALFUND", "INDEX"}:
        return False
    return _info_observation_count(row) == 0


def _prefer_retry(original_row, retry_row):
    """Use the retry only if it is strictly more useful than the fallback row."""
    if retry_row is None or getattr(retry_row, "error", None):
        return original_row
    if original_row is None or getattr(original_row, "error", None):
        return retry_row
    if _info_observation_count(retry_row) > _info_observation_count(original_row):
        return retry_row
    return original_row


def install(module=None, *, sleeper=None):
    if module is None:
        import fundamentals as module

    if getattr(module, "_vestra_yahoo_retry_hygiene_installed", False):
        return module.fetch_many

    original = module.fetch_many
    sleeper = sleeper or time.sleep

    def fetch_many_hygienic(tickers, pause=0.0, workers_override=None, retries=3):
        requested = list(dict.fromkeys(tickers or []))
        if not requested:
            return []

        # Keep the existing first-pass concurrency and all fetch_one semantics,
        # but take ownership of retry selection so hard identity failures are not
        # needlessly repeated in the same run.
        first = original(
            requested,
            pause=pause,
            workers_override=workers_override,
            retries=0,
        )
        by_ticker = {row.ticker: row for row in first}

        hard = [
            tk for tk in requested
            if is_hard_symbol_error(getattr(by_ticker.get(tk), "error", None))
        ]
        if hard:
            module.log.info(
                "Yahoo retry hygiene: %d hard symbol failure(s) will not be retried in this run: %s",
                len(hard), ", ".join(hard[:12]) + ("…" if len(hard) > 12 else ""),
            )

        # A silent price-only fallback is only suspicious when the shared Yahoo
        # coordinator actually observed throttling during this pass. Retry each
        # such row at most once, independent of the normal explicit-error passes.
        degraded_pending = {
            tk for tk in requested
            if _throttle_incident_seen(module) and is_suspect_price_only_fallback(by_ticker.get(tk))
        }
        degraded_attempted: set[str] = set()
        if degraded_pending:
            module.log.info(
                "Yahoo retry hygiene: %d price-only row(s) flagged after throttle for one recovery attempt",
                len(degraded_pending),
            )

        for attempt in range(max(0, int(retries))):
            explicit_failed = [
                tk for tk in requested
                if getattr(by_ticker.get(tk), "error", None)
                and not is_hard_symbol_error(getattr(by_ticker.get(tk), "error", None))
            ]
            degraded = [
                tk for tk in requested
                if tk in degraded_pending and tk not in degraded_attempted
            ]
            retry_tickers = list(dict.fromkeys(explicit_failed + degraded))
            if not retry_tickers:
                break

            # Only explicit failures drive the broad-failure guard. Silent
            # fallbacks are usable rows and must never make the build look failed.
            failure_ratio = len(explicit_failed) / max(1, len(requested))
            if len(requested) > 250 and failure_ratio >= 0.25:
                module.log.warning(
                    "Broad transient Yahoo failure: %d/%d (%.1f%%). Skipping bulk retry pass to keep build bounded.",
                    len(explicit_failed), len(requested), failure_ratio * 100,
                )
                break

            backoff = min(45, 6 * (2 ** attempt))
            module.log.info(
                "Retrying %d Yahoo ticker(s), pass %d/%d (%d explicit, %d price-only; waiting %ds first)",
                len(retry_tickers), attempt + 1, retries, len(explicit_failed), len(degraded), backoff,
            )
            sleeper(backoff)

            # Preserve the current sequential retry behavior after a throttle.
            for i, tk in enumerate(retry_tickers):
                previous = by_ticker.get(tk)
                rows = original([tk], pause=0.0, workers_override=1, retries=0)
                if tk in degraded_pending:
                    degraded_attempted.add(tk)
                if rows:
                    retry = rows[0]
                    if tk in degraded_pending and not getattr(previous, "error", None):
                        by_ticker[tk] = _prefer_retry(previous, retry)
                    else:
                        by_ticker[tk] = retry
                if pause:
                    sleeper(pause)
                if (i + 1) % 50 == 0:
                    module.log.info("retry pass %d: %d/%d", attempt + 1, i + 1, len(retry_tickers))

        still_failed = [tk for tk in requested if getattr(by_ticker.get(tk), "error", None)]
        hard_failed = [tk for tk in still_failed if is_hard_symbol_error(getattr(by_ticker.get(tk), "error", None))]
        transient_failed = [tk for tk in still_failed if tk not in set(hard_failed)]
        if still_failed:
            module.log.warning(
                "%d/%d tickers still failed (%d hard identity, %d transient)",
                len(still_failed), len(requested), len(hard_failed), len(transient_failed),
            )

        recovered_degraded = sum(
            1 for tk in degraded_attempted
            if not is_suspect_price_only_fallback(by_ticker.get(tk))
        )
        if degraded_attempted:
            module.log.info(
                "Yahoo price-only recovery: attempted=%d improved=%d preserved_fallback=%d",
                len(degraded_attempted), recovered_degraded,
                len(degraded_attempted) - recovered_degraded,
            )

        return [by_ticker[tk] for tk in requested if tk in by_ticker]

    module._vestra_original_fetch_many = original
    module.fetch_many = fetch_many_hygienic
    module._vestra_yahoo_retry_hygiene_installed = True
    return fetch_many_hygienic
