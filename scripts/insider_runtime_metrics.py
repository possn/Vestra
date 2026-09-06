"""Runtime-only observability for SEC Form 4 enrichment.

This module does not change ticker selection, retries, SEC URLs, parsed values,
cache contents, or insider semantics. It only counts the transport work already
performed by insiders.py so production logs can distinguish time spent on
submissions discovery, immutable Archive documents and filing-cache reuse.
"""
from __future__ import annotations

import threading
import time


def install(module=None, clock=None):
    if module is None:
        import insiders as module
    if getattr(module, "_vestra_insider_metrics_installed", False):
        return getattr(module, "_vestra_insider_metrics", None)

    clock = clock or time.monotonic
    lock = threading.Lock()
    metrics = {
        "submissions_requests": 0,
        "submissions_failures": 0,
        "archive_requests": 0,
        "archive_failures": 0,
        "other_requests": 0,
        "other_failures": 0,
        "cache_hits": 0,
        "cache_misses": 0,
    }

    original_get = module._get
    original_cached_filing = module._cached_filing
    original_annotate = module.annotate

    def classify(url):
        text = str(url or "")
        if "/submissions/CIK" in text:
            return "submissions"
        if "/Archives/edgar/data/" in text:
            return "archive"
        return "other"

    def observed_get(url, timeout=25):
        lane = classify(url)
        with lock:
            metrics[f"{lane}_requests"] += 1
        try:
            return original_get(url, timeout=timeout)
        except Exception:
            with lock:
                metrics[f"{lane}_failures"] += 1
            raise

    def observed_cached_filing(cik, filing, ticker):
        result = original_cached_filing(cik, filing, ticker)
        with lock:
            metrics["cache_hits" if result is not None else "cache_misses"] += 1
        return result

    def observed_annotate(tickers, pause=0.0):
        with lock:
            for key in metrics:
                metrics[key] = 0
        started = clock()
        try:
            return original_annotate(tickers, pause=pause)
        finally:
            elapsed = max(0.0, float(clock() - started))
            with lock:
                snapshot = dict(metrics)
            module.log.info(
                "Insider transport summary: elapsed=%.1fs submissions=%d failures=%d archives=%d failures=%d cache_hits=%d cache_misses=%d other=%d failures=%d",
                elapsed,
                snapshot["submissions_requests"],
                snapshot["submissions_failures"],
                snapshot["archive_requests"],
                snapshot["archive_failures"],
                snapshot["cache_hits"],
                snapshot["cache_misses"],
                snapshot["other_requests"],
                snapshot["other_failures"],
            )

    module._vestra_original_insider_get = original_get
    module._vestra_original_cached_filing = original_cached_filing
    module._vestra_original_annotate = original_annotate
    module._get = observed_get
    module._cached_filing = observed_cached_filing
    module.annotate = observed_annotate
    module._vestra_insider_metrics = metrics
    module._vestra_insider_metrics_installed = True
    return metrics
