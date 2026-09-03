import importlib.util
from pathlib import Path
import sys
import types
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

MODULE_PATH = SCRIPTS / "run_market_pipeline.py"
spec = importlib.util.spec_from_file_location("run_market_pipeline", MODULE_PATH)
runtime = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = runtime
spec.loader.exec_module(runtime)


class _Log:
    def __init__(self):
        self.messages = []

    def warning(self, fmt, *args):
        self.messages.append(fmt % args)


class YahooRateLimitRuntimeTests(unittest.TestCase):
    def _install(self, times):
        module = types.SimpleNamespace(log=_Log())
        sleeps = []
        values = iter(times)
        coordinator = runtime.RateLimitCoordinator(
            incident_window_seconds=2.0,
            quiet_reset_seconds=120.0,
            base_backoff_seconds=10,
            max_backoff_seconds=60,
        )
        runtime.install_rate_limit_coordinator(
            module,
            coordinator,
            clock=lambda: next(values),
            sleeper=sleeps.append,
        )
        return module, coordinator, sleeps

    def test_same_burst_worker_hits_share_one_strike_and_one_log(self):
        module, coordinator, _ = self._install([100.0, 100.2, 101.9])
        module._register_rate_limit_hit()
        module._register_rate_limit_hit()
        module._register_rate_limit_hit()

        snap = coordinator.snapshot()
        self.assertEqual(snap["strike"], 1)
        self.assertEqual(snap["cooldown_until"], 110.0)
        self.assertEqual(len(module.log.messages), 1)
        self.assertIn("strike 1", module.log.messages[0])

    def test_separate_incidents_keep_existing_backoff_progression(self):
        module, coordinator, _ = self._install([100.0, 103.0, 106.0, 109.0])
        for _ in range(4):
            module._register_rate_limit_hit()

        snap = coordinator.snapshot()
        self.assertEqual(snap["strike"], 4)
        self.assertEqual(snap["cooldown_until"], 169.0)
        self.assertEqual(len(module.log.messages), 4)
        self.assertIn("10s (strike 1)", module.log.messages[0])
        self.assertIn("60s (strike 4)", module.log.messages[-1])

    def test_wait_hook_sleeps_only_remaining_cooldown(self):
        module, coordinator, sleeps = self._install([104.0])
        coordinator.register(100.0)
        module._wait_for_cooldown()
        self.assertEqual(sleeps, [6.0])


if __name__ == "__main__":
    unittest.main()
