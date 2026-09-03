import importlib.util
from pathlib import Path
import sys
import unittest


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "yahoo_rate_limit.py"
spec = importlib.util.spec_from_file_location("yahoo_rate_limit", MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)
RateLimitCoordinator = mod.RateLimitCoordinator


class YahooRateLimitCoordinatorTests(unittest.TestCase):
    def test_simultaneous_hits_are_one_incident(self):
        c = RateLimitCoordinator(incident_window_seconds=2.0)
        first = c.register(100.0)
        second = c.register(100.2)
        third = c.register(101.9)

        self.assertTrue(first.new_incident)
        self.assertEqual(first.strike, 1)
        self.assertEqual(first.backoff_seconds, 10)
        self.assertFalse(second.new_incident)
        self.assertFalse(third.new_incident)
        self.assertEqual(second.strike, 1)
        self.assertEqual(third.strike, 1)
        self.assertEqual(second.cooldown_until, 110.0)
        self.assertEqual(third.cooldown_until, 110.0)

    def test_separate_incidents_escalate_once_each(self):
        c = RateLimitCoordinator(incident_window_seconds=2.0)
        self.assertEqual(c.register(100.0).backoff_seconds, 10)
        self.assertEqual(c.register(103.0).backoff_seconds, 20)
        self.assertEqual(c.register(106.0).backoff_seconds, 40)
        fourth = c.register(109.0)
        self.assertEqual(fourth.strike, 4)
        self.assertEqual(fourth.backoff_seconds, 60)

    def test_quiet_period_resets_strikes(self):
        c = RateLimitCoordinator(quiet_reset_seconds=120.0)
        self.assertEqual(c.register(100.0).strike, 1)
        self.assertEqual(c.register(103.0).strike, 2)
        reset = c.register(224.0)
        self.assertTrue(reset.new_incident)
        self.assertEqual(reset.strike, 1)
        self.assertEqual(reset.backoff_seconds, 10)

    def test_remaining_never_goes_negative(self):
        c = RateLimitCoordinator()
        c.register(100.0)
        self.assertEqual(c.remaining(105.0), 5.0)
        self.assertEqual(c.remaining(111.0), 0.0)

    def test_out_of_order_observation_does_not_coalesce(self):
        c = RateLimitCoordinator()
        first = c.register(100.0)
        older_clock = c.register(99.5)
        self.assertEqual(first.strike, 1)
        self.assertTrue(older_clock.new_incident)
        self.assertEqual(older_clock.strike, 2)

    def test_invalid_configuration_fails_closed(self):
        with self.assertRaises(ValueError):
            RateLimitCoordinator(incident_window_seconds=-1)
        with self.assertRaises(ValueError):
            RateLimitCoordinator(quiet_reset_seconds=0)
        with self.assertRaises(ValueError):
            RateLimitCoordinator(base_backoff_seconds=61, max_backoff_seconds=60)


if __name__ == "__main__":
    unittest.main()
