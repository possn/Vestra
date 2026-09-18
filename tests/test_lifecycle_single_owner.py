import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class LifecycleSingleOwnerTests(unittest.TestCase):
    def test_app_js_does_not_own_splash_visibility(self):
        app = (ROOT / "app.js").read_text(encoding="utf-8")
        self.assertNotIn('_splash.style.display = "flex"', app)
        self.assertNotIn('_splash.style.opacity = "0"', app)
        self.assertNotIn('const _splashStartedAt = performance.now()', app)
        self.assertIn('Splash visibility/release is owned exclusively by app-ui-core.js.', app)

    def test_initial_hydration_forces_real_view_render_before_ready(self):
        app = (ROOT / "app.js").read_text(encoding="utf-8")
        self.assertIn("const sync = !!(opts && opts.sync);", app)
        self.assertIn("scheduleRenderView(currentView, { force: true, sync });", app)
        self.assertIn("renderAll({ force: true, sync: true });", app)
        self.assertLess(
            app.index("renderAll({ force: true, sync: true });"),
            app.index("window.__vestraAppHydrated = true"),
        )

    def test_lifecycle_exit_saves_are_coalesced(self):
        app = (ROOT / "app.js").read_text(encoding="utf-8")
        self.assertIn("let lifecycleExitSavePromise = null;", app)
        self.assertIn("if (lifecycleExitSavePromise) return true;", app)
        self.assertIn("lifecycleExitSavePromise = Promise.resolve(saveStateAsync())", app)
        self.assertIn("window.addEventListener(\"pagehide\", saveStateOnLifecycleExit);", app)
        self.assertIn("window.addEventListener(\"beforeunload\", saveStateOnLifecycleExit);", app)


if __name__ == "__main__":
    unittest.main()
