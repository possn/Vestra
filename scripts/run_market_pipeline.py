"""Canonical market-pipeline launcher with request coordination installed.

The data pipeline itself remains in run.py. This launcher changes only runtime
request-control hooks owned by fundamentals.py, analyst.py and SEC enrichment,
then executes run.py as __main__ so its existing error logging, pipeline-log
flushing and exit semantics are kept.
"""
from __future__ import annotations

import os
import runpy
import threading
import time

from yahoo_rate_limit import RateLimitCoordinator
from yahoo_retry_hygiene import install as install_yahoo_retry_hygiene
from sec_worker_fallback import install as install_sec_worker_fallback


def install_rate_limit_coordinator(module=None, coordinator=None, *, clock=None, sleeper=None):
    """Install incident-coalesced cooldown hooks into the fundamentals module.

    `module`, `clock` and `sleeper` are injectable only to keep the runtime
    contract testable without Yahoo/network access. Production uses the real
    fundamentals module and wall clock.
    """
    if module is None:
        import fundamentals as module
    if coordinator is None:
        coordinator = RateLimitCoordinator(
            incident_window_seconds=2.0,
            quiet_reset_seconds=120.0,
            base_backoff_seconds=10,
            max_backoff_seconds=60,
        )
    clock = clock or time.time
    sleeper = sleeper or time.sleep

    def wait_for_cooldown():
        remaining = coordinator.remaining(clock())
        if remaining > 0:
            sleeper(remaining)

    def register_rate_limit_hit():
        decision = coordinator.register(clock())
        if decision.new_incident:
            module.log.warning(
                "Yahoo rate-limit detected — pausing fetch workers for %ds (strike %d)",
                decision.backoff_seconds,
                decision.strike,
            )

    module._wait_for_cooldown = wait_for_cooldown
    module._register_rate_limit_hit = register_rate_limit_hit
    module._rate_limit_coordinator = coordinator
    return coordinator


def install_analyst_request_gate(module=None, max_concurrent=None):
    """Bound simultaneous Yahoo analyst endpoint calls without changing evidence.

    Analyst enrichment fans up to eight ticker workers into several Yahoo
    analysis endpoints per ticker. yfinance can absorb crumb/auth failures
    internally, so an exception-only circuit breaker cannot reliably see every
    401/429 event. Bounding the actual endpoint-call concurrency is deterministic
    and leaves ticker selection, module order, returned values and missing-data
    semantics untouched.
    """
    if module is None:
        import analyst as module

    if max_concurrent is None:
        max_concurrent = int(os.getenv("FINSCANNER_ANALYST_ENDPOINT_CONCURRENCY", "3"))
    max_concurrent = max(1, min(8, int(max_concurrent)))

    original = getattr(module, "_vestra_original_safe_call", module._safe_call)
    gate = threading.BoundedSemaphore(max_concurrent)

    def gated_safe_call(fn):
        with gate:
            return original(fn)

    module._vestra_original_safe_call = original
    module._safe_call = gated_safe_call
    module._analyst_request_gate = gate
    module._analyst_request_gate_limit = max_concurrent
    return gate


def main():
    # Keep network-backed SEC dependencies out of module import time. Several
    # runtime contract tests intentionally import this launcher without installing
    # the full pipeline requirements; production imports the Archives lane only
    # when main() is actually executed.
    from sec_archives_runtime import install as install_sec_archives_fallback

    install_rate_limit_coordinator()
    install_yahoo_retry_hygiene()
    install_analyst_request_gate()
    install_sec_worker_fallback()
    install_sec_archives_fallback()
    runpy.run_module("run", run_name="__main__")


if __name__ == "__main__":
    main()
