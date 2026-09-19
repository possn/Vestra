from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
APP = (ROOT / "app.js").read_text(encoding="utf-8")


class StartupIdleWorkTests(unittest.TestCase):
    def test_idle_scheduler_prefers_request_idle_callback_with_bounded_timeout(self):
        self.assertIn("function scheduleWhenIdle(task, { timeoutMs = 1200, fallbackDelayMs = 450 } = {})", APP)
        self.assertIn('typeof window.requestIdleCallback === "function"', APP)
        self.assertIn("window.requestIdleCallback(run, { timeout:", APP)
        self.assertIn("setTimeout(run, Math.max(0, Number(fallbackDelayMs) || 0));", APP)

    def test_initial_noncritical_work_does_not_run_at_150ms(self):
        start = APP.index("// Deferred non-critical tasks.")
        end = APP.index("window.openDividendBaseModal", start)
        block = APP[start:end]
        self.assertIn("scheduleWhenIdle(() => {", block)
        self.assertIn("autoSnapshotIfNeeded()", block)
        self.assertIn("checkAndNotifyMaturities()", block)
        self.assertIn("autoRefreshQuotesIfStale()", block)
        self.assertIn("{ timeoutMs: 1200, fallbackDelayMs: 500 }", block)
        self.assertNotIn("}, 150);", block)

    def test_foreground_quote_refresh_is_idle_deferred(self):
        start = APP.index('document.addEventListener("visibilitychange"')
        end = APP.index('window.addEventListener("pagehide"', start)
        block = APP[start:end]
        self.assertIn("scheduleWhenIdle(", block)
        self.assertIn("autoRefreshQuotesIfStale()", block)
        self.assertIn("{ timeoutMs: 700, fallbackDelayMs: 250 }", block)
        self.assertNotIn("}, 100);", block)

    def test_hydration_boundary_stays_before_deferred_work(self):
        hydrated = APP.index("window.__vestraAppHydrated = true")
        idle = APP.index("// Deferred non-critical tasks.")
        self.assertLess(hydrated, idle)


if __name__ == "__main__":
    unittest.main(verbosity=2)
