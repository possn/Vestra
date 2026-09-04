"""Retry hygiene for Yahoo fundamentals retrieval.

A hard symbol failure (explicit delisted/no-timezone/404 identity failure) should
not consume the same retry budget as a transient 429, timeout or transport error.
This wrapper changes retry policy only within the current pipeline run. Nothing
is persisted: every ticker is eligible for a fresh first attempt on the next run.
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


def is_hard_symbol_error(error) -> bool:
    text = str(error or "").strip().lower()
    if not text:
        return False
    return any(marker in text for marker in HARD_ERROR_MARKERS)


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

        for attempt in range(max(0, int(retries))):
            failed = [
                tk for tk in requested
                if getattr(by_ticker.get(tk), "error", None)
                and not is_hard_symbol_error(getattr(by_ticker.get(tk), "error", None))
            ]
            if not failed:
                break

            failure_ratio = len(failed) / max(1, len(requested))
            if len(requested) > 250 and failure_ratio >= 0.25:
                module.log.warning(
                    "Broad transient Yahoo failure: %d/%d (%.1f%%). Skipping bulk retry pass to keep build bounded.",
                    len(failed), len(requested), failure_ratio * 100,
                )
                break

            backoff = min(45, 6 * (2 ** attempt))
            module.log.info(
                "Retrying %d transient ticker(s), pass %d/%d (waiting %ds first)",
                len(failed), attempt + 1, retries, backoff,
            )
            sleeper(backoff)

            # Preserve the current sequential retry behavior after a throttle.
            for i, tk in enumerate(failed):
                rows = original([tk], pause=0.0, workers_override=1, retries=0)
                if rows:
                    retry = rows[0]
                    by_ticker[tk] = retry
                if pause:
                    sleeper(pause)
                if (i + 1) % 50 == 0:
                    module.log.info("retry pass %d: %d/%d", attempt + 1, i + 1, len(failed))

        still_failed = [tk for tk in requested if getattr(by_ticker.get(tk), "error", None)]
        hard_failed = [tk for tk in still_failed if is_hard_symbol_error(getattr(by_ticker.get(tk), "error", None))]
        transient_failed = [tk for tk in still_failed if tk not in set(hard_failed)]
        if still_failed:
            module.log.warning(
                "%d/%d tickers still failed (%d hard identity, %d transient)",
                len(still_failed), len(requested), len(hard_failed), len(transient_failed),
            )

        return [by_ticker[tk] for tk in requested if tk in by_ticker]

    module._vestra_original_fetch_many = original
    module.fetch_many = fetch_many_hygienic
    module._vestra_yahoo_retry_hygiene_installed = True
    return fetch_many_hygienic
