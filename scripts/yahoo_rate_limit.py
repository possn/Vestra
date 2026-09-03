"""Thread-safe Yahoo rate-limit incident coordinator.

This module is deliberately independent from fundamentals.py so the coalescing
policy can be unit-tested before it is wired into the production fetch path.
It contains no network calls and no market-data semantics.
"""
from __future__ import annotations

from dataclasses import dataclass
import threading


@dataclass(frozen=True)
class RateLimitDecision:
    new_incident: bool
    strike: int
    backoff_seconds: int
    cooldown_until: float


class RateLimitCoordinator:
    """Coalesce simultaneous 429s into one incident and escalate only by incident.

    Multiple workers can observe the same upstream throttle within milliseconds.
    Those observations must share one strike/backoff instead of independently
    escalating 10s -> 20s -> 40s -> 60s for a single Yahoo event.
    """

    def __init__(
        self,
        *,
        incident_window_seconds: float = 2.0,
        quiet_reset_seconds: float = 120.0,
        base_backoff_seconds: int = 10,
        max_backoff_seconds: int = 60,
    ):
        if incident_window_seconds < 0:
            raise ValueError("incident_window_seconds must be >= 0")
        if quiet_reset_seconds <= 0:
            raise ValueError("quiet_reset_seconds must be > 0")
        if base_backoff_seconds <= 0 or max_backoff_seconds <= 0:
            raise ValueError("backoff values must be > 0")
        if base_backoff_seconds > max_backoff_seconds:
            raise ValueError("base_backoff_seconds cannot exceed max_backoff_seconds")

        self.incident_window_seconds = float(incident_window_seconds)
        self.quiet_reset_seconds = float(quiet_reset_seconds)
        self.base_backoff_seconds = int(base_backoff_seconds)
        self.max_backoff_seconds = int(max_backoff_seconds)
        self._lock = threading.Lock()
        self._strike = 0
        self._last_incident_at: float | None = None
        self._cooldown_until = 0.0

    def register(self, now: float) -> RateLimitDecision:
        now = float(now)
        with self._lock:
            last = self._last_incident_at
            if last is not None and now - last > self.quiet_reset_seconds:
                self._strike = 0
                last = None

            same_incident = (
                last is not None
                and now >= last
                and now - last <= self.incident_window_seconds
            )

            if same_incident:
                backoff = min(
                    self.max_backoff_seconds,
                    self.base_backoff_seconds * (2 ** max(0, self._strike - 1)),
                )
                return RateLimitDecision(
                    new_incident=False,
                    strike=self._strike,
                    backoff_seconds=backoff,
                    cooldown_until=self._cooldown_until,
                )

            self._strike += 1
            self._last_incident_at = now
            backoff = min(
                self.max_backoff_seconds,
                self.base_backoff_seconds * (2 ** (self._strike - 1)),
            )
            self._cooldown_until = max(self._cooldown_until, now + backoff)
            return RateLimitDecision(
                new_incident=True,
                strike=self._strike,
                backoff_seconds=backoff,
                cooldown_until=self._cooldown_until,
            )

    def remaining(self, now: float) -> float:
        with self._lock:
            return max(0.0, self._cooldown_until - float(now))

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "strike": self._strike,
                "last_incident_at": self._last_incident_at,
                "cooldown_until": self._cooldown_until,
            }
