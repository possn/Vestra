import importlib
import pathlib
import sys
import types


ROOT = pathlib.Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

# fundamentals imports yfinance at module import time; use a tiny stub because
# these tests exercise only the rate-limit coordinator wiring, never network IO.
sys.modules.setdefault("yfinance", types.SimpleNamespace())

fundamentals = importlib.import_module("fundamentals")


def _fresh_coordinator():
    fundamentals._rate_limit_coordinator = fundamentals.RateLimitCoordinator(
        incident_window_seconds=2.0,
        quiet_reset_seconds=120.0,
        base_backoff_seconds=10,
        max_backoff_seconds=60,
    )


def test_simultaneous_rate_limit_hits_share_one_strike(monkeypatch):
    _fresh_coordinator()
    times = iter([100.0, 100.2, 101.9])
    monkeypatch.setattr(fundamentals.time, "time", lambda: next(times))

    fundamentals._register_rate_limit_hit()
    fundamentals._register_rate_limit_hit()
    fundamentals._register_rate_limit_hit()

    snap = fundamentals._rate_limit_coordinator.snapshot()
    assert snap["strike"] == 1
    assert snap["cooldown_until"] == 110.0


def test_separate_rate_limit_incidents_escalate_once_each(monkeypatch):
    _fresh_coordinator()
    times = iter([100.0, 103.0, 106.0, 109.0])
    monkeypatch.setattr(fundamentals.time, "time", lambda: next(times))

    for _ in range(4):
        fundamentals._register_rate_limit_hit()

    snap = fundamentals._rate_limit_coordinator.snapshot()
    assert snap["strike"] == 4
    assert snap["cooldown_until"] == 169.0


def test_wait_for_cooldown_uses_coordinator_remaining(monkeypatch):
    _fresh_coordinator()
    fundamentals._rate_limit_coordinator.register(100.0)
    monkeypatch.setattr(fundamentals.time, "time", lambda: 104.0)
    slept = []
    monkeypatch.setattr(fundamentals.time, "sleep", slept.append)

    fundamentals._wait_for_cooldown()

    assert slept == [6.0]
