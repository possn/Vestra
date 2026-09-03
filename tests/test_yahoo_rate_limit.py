import importlib.util
from pathlib import Path
import sys


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "yahoo_rate_limit.py"
spec = importlib.util.spec_from_file_location("yahoo_rate_limit", MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)
RateLimitCoordinator = mod.RateLimitCoordinator


def test_simultaneous_hits_are_one_incident():
    c = RateLimitCoordinator(incident_window_seconds=2.0)
    first = c.register(100.0)
    second = c.register(100.2)
    third = c.register(101.9)

    assert first.new_incident is True
    assert first.strike == 1
    assert first.backoff_seconds == 10
    assert second.new_incident is False
    assert third.new_incident is False
    assert second.strike == third.strike == 1
    assert second.cooldown_until == third.cooldown_until == 110.0


def test_separate_incidents_escalate_once_each():
    c = RateLimitCoordinator(incident_window_seconds=2.0)
    assert c.register(100.0).backoff_seconds == 10
    assert c.register(103.0).backoff_seconds == 20
    assert c.register(106.0).backoff_seconds == 40
    fourth = c.register(109.0)
    assert fourth.strike == 4
    assert fourth.backoff_seconds == 60


def test_quiet_period_resets_strikes():
    c = RateLimitCoordinator(quiet_reset_seconds=120.0)
    assert c.register(100.0).strike == 1
    assert c.register(103.0).strike == 2
    reset = c.register(224.0)
    assert reset.new_incident is True
    assert reset.strike == 1
    assert reset.backoff_seconds == 10


def test_remaining_never_goes_negative():
    c = RateLimitCoordinator()
    c.register(100.0)
    assert c.remaining(105.0) == 5.0
    assert c.remaining(111.0) == 0.0


def test_out_of_order_observation_does_not_coalesce():
    c = RateLimitCoordinator()
    first = c.register(100.0)
    older_clock = c.register(99.5)
    assert first.strike == 1
    assert older_clock.new_incident is True
    assert older_clock.strike == 2


def test_invalid_configuration_fails_closed():
    import pytest

    with pytest.raises(ValueError):
        RateLimitCoordinator(incident_window_seconds=-1)
    with pytest.raises(ValueError):
        RateLimitCoordinator(quiet_reset_seconds=0)
    with pytest.raises(ValueError):
        RateLimitCoordinator(base_backoff_seconds=61, max_backoff_seconds=60)
