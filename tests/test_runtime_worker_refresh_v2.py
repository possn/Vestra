from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "app-runtime-bridge.js"
UI_CORE = ROOT / "app-ui-core.js"
BOOT = ROOT / "market-company-brief.js"
INDEX = ROOT / "index.html"


class RuntimeWorkerRefreshV2Tests(unittest.TestCase):
    def test_javascript_syntax(self):
        subprocess.run(["node", "--check", str(BRIDGE)], check=True, cwd=ROOT)
        subprocess.run(["node", "--check", str(UI_CORE)], check=True, cwd=ROOT)

    def test_bridge_has_canonical_worker_fallback(self):
        text = BRIDGE.read_text(encoding="utf-8")
        self.assertIn("https://delicate-bar-cc80.pedrossnunes.workers.dev", text)
        self.assertIn("workerUrl: CANONICAL_WORKER_URL", text)
        self.assertIn("version: '1.1'", text)

    def test_update_owner_is_navigation_only_and_never_wipes_runtime(self):
        text = UI_CORE.read_text(encoding="utf-8")
        self.assertIn("function installSafeUpdateGuard()", text)
        self.assertIn("document.addEventListener('click'", text)
        self.assertIn("}, true);", text)
        self.assertIn("stopImmediatePropagation", text)
        self.assertIn("window.location.replace", text)
        self.assertNotIn("serviceWorker", text)
        self.assertNotIn("getRegistration", text)
        self.assertNotIn("getRegistrations", text)
        self.assertNotIn(".unregister(", text)
        self.assertNotIn("caches.keys", text)

    def test_index_is_single_service_worker_lifecycle_owner(self):
        text = INDEX.read_text(encoding="utf-8")
        self.assertIn("navigator.serviceWorker.getRegistration().then(reg => { if (reg) reg.update(); });", text)
        self.assertIn("navigator.serviceWorker.addEventListener('controllerchange'", text)
        self.assertNotIn("location.reload()", text)
        self.assertIn("__vestraServiceWorkerUpdated", text)
        self.assertLess(text.index('src="app-ui-core.js'), text.index('src="app.js'))
        self.assertNotIn("app-update-manager.js", text)

    def test_bootstrap_loads_current_runtime_modules(self):
        text = BOOT.read_text(encoding="utf-8")
        self.assertIn("app-runtime-bridge.js?v=1.1", text)
        self.assertNotIn("app-update-manager.js", text)
        self.assertNotIn("loadAppUpdateManager", text)
        self.assertIn("market-learned-universe.js?v=3.0", text)
        self.assertIn("market-global-search.js?v=2.0", text)
        self.assertIn("market-data-health.js?v=1.3", text)
        self.assertIn("loadDataHealth();", text)
        self.assertIn("loadLearnedUniverse();", text)
        self.assertIn("window.VestraMarketCompanyBrief=Object.freeze", text)
        self.assertNotIn("quote-refresh-performance.js", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
