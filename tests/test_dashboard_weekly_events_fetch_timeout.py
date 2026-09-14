from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "dashboard-weekly-events.js"
LOADER = ROOT / "market-static-universe.js"


class DashboardWeeklyEventsFetchTimeoutTests(unittest.TestCase):
    def setUp(self):
        self.runtime = RUNTIME.read_text(encoding="utf-8")
        self.loader = LOADER.read_text(encoding="utf-8")

    def test_macro_snapshot_fetch_has_a_bounded_deadline(self):
        self.assertIn("const MACRO_FETCH_TIMEOUT_MS = 5000;", self.runtime)
        self.assertIn("timeoutMs = MACRO_FETCH_TIMEOUT_MS", self.runtime)
        self.assertIn("Promise.race([request, timeout])", self.runtime)
        self.assertIn("setTimeout(() => resolve(null)", self.runtime)
        self.assertIn("clearTimeout(timeoutId)", self.runtime)

    def test_timeout_releases_shared_loader_for_retry(self):
        self.assertIn("if (macroLoading) return macroLoading;", self.runtime)
        self.assertIn("macroLoading = null;", self.runtime)
        self.assertLess(
            self.runtime.index("const payload = await Promise.race([request, timeout]);"),
            self.runtime.index("macroSnapshot = payload;"),
        )

    def test_schedule_render_cannot_wait_forever_on_macro_snapshot(self):
        self.assertIn("Promise.allSettled([marketLoad,loadMacroEvents()])", self.runtime)
        self.assertIn("macroFetchTimeoutMs:MACRO_FETCH_TIMEOUT_MS", self.runtime)

    def test_runtime_and_loader_versions_match(self):
        self.assertIn("const VERSION = '1.9';", self.runtime)
        self.assertIn("dashboard-weekly-events.js?v=1.9", self.loader)


if __name__ == "__main__":
    unittest.main(verbosity=2)
