"""Canonical market-pipeline launcher with Yahoo throttle coordination installed.

The data pipeline itself remains in run.py. This launcher changes only the two
rate-limit hooks owned by fundamentals.py, then executes run.py as __main__ so
its existing error logging, pipeline-log flushing and exit semantics are kept.
"""
from __future__ import annotations

import runpy
import time

from yahoo_rate_limit import RateLimitCoordinator


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


def main():
    install_rate_limit_coordinator()
    runpy.run_module("run", run_name="__main__")


if __name__ == "__main__":
    main()
