"""Canonical market-pipeline launcher with request coordination installed.

The data pipeline itself remains in run.py. This launcher changes only runtime
request-control hooks owned by fundamentals.py, analyst.py, SEC enrichment,
London ESEF identity and independent physical-metals adapters, then executes
run.py as __main__ so its existing error logging, pipeline-log flushing and exit
semantics are kept.
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


def install_fetch_worker_cap(module=None, max_workers=None):
    """Enforce the workflow's Yahoo worker ceiling across every fetch batch.

    run.py intentionally uses explicit overrides for learned and portfolio names.
    A lower production ceiling must still win over those overrides; otherwise the
    workflow can advertise two workers while the portfolio batch silently uses
    three and recreates the throttle burst the ceiling was introduced to avoid.
    """
    if module is None:
        import fundamentals as module
    if getattr(module, "_vestra_fetch_worker_cap_installed", False):
        return module.fetch_many

    if max_workers is None:
        max_workers = int(os.getenv("FINSCANNER_FETCH_WORKERS", "4"))
    max_workers = max(1, min(4, int(max_workers)))
    original = module.fetch_many

    def capped_fetch_many(tickers, pause=0.0, workers_override=None, retries=3):
        requested = max_workers if workers_override is None else min(max_workers, max(1, int(workers_override)))
        return original(
            tickers,
            pause=pause,
            workers_override=requested,
            retries=retries,
        )

    module._vestra_original_fetch_many_before_worker_cap = original
    module.fetch_many = capped_fetch_many
    module._vestra_fetch_worker_cap_installed = True
    module._fetch_worker_cap = max_workers
    return capped_fetch_many


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
    # Keep network-backed dependencies out of module import time. Several runtime
    # contract tests intentionally import this launcher without installing the
    # full pipeline requirements; production imports those lanes only here.
    from sec_archives_runtime import install as install_sec_archives_fallback
    from physical_metals_runtime import install as install_parallel_physical_metals
    from lse_first_esef_runtime import install as install_lse_first_esef_identity

    install_rate_limit_coordinator()
    install_fetch_worker_cap()
    install_yahoo_retry_hygiene()
    install_analyst_request_gate()
    install_sec_worker_fallback()
    install_sec_archives_fallback()
    install_lse_first_esef_identity()
    install_parallel_physical_metals()
    runpy.run_module("run", run_name="__main__")


if __name__ == "__main__":
    main()
