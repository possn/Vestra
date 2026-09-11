from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "app-runtime-bridge.js"
UPDATE = ROOT / "app-update-manager.js"
BOOT = ROOT / "market-company-brief.js"
INDEX = ROOT / "index.html"


class RuntimeWorkerRefreshV2Tests(unittest.TestCase):
    def test_javascript_syntax(self):
        subprocess.run(["node", "--check", str(BRIDGE)], check=True, cwd=ROOT)
        subprocess.run(["node", "--check", str(UPDATE)], check=True, cwd=ROOT)

    def test_bridge_has_canonical_worker_fallback(self):
        text = BRIDGE.read_text(encoding="utf-8")
        self.assertIn("https://delicate-bar-cc80.pedrossnunes.workers.dev", text)
        self.assertIn("workerUrl: CANONICAL_WORKER_URL", text)
        self.assertIn("version: '1.1'", text)

    def test_update_manager_is_navigation_only_and_never_wipes_runtime(self):
        text = UPDATE.read_text(encoding="utf-8")
        self.assertIn("document.getElementById('btnForceUpdate')", text)
        self.assertIn("current.cloneNode(true)", text)
        self.assertIn("current.replaceWith(button)", text)
        self.assertIn("document.addEventListener('click'", text)
        self.assertIn("}, true);", text)
        self.assertIn("version: '1.5'", text)
        self.assertIn("stopImmediatePropagation", text)
        self.assertIn("DOMContentLoaded', reclaimAfterAppSetup", text)
        self.assertIn("vestra:app-ready', reclaimAfterAppSetup", text)
        self.assertNotIn("appLoadingOverlay", text)
        self.assertNotIn("serviceWorker", text)
        self.assertNotIn("getRegistration", text)
        self.assertNotIn("getRegistrations", text)
        self.assertNotIn(".unregister(", text)
        self.assertNotIn("caches.keys", text)

    def test_index_is_single_service_worker_lifecycle_owner(self):
        text = INDEX.read_text(encoding="utf-8")
        self.assertIn("navigator.serviceWorker.getRegistration().then(reg => { if (reg) reg.update(); });", text)
        self.assertIn("navigator.serviceWorker.addEventListener('controllerchange'", text)

    def test_bootstrap_loads_current_runtime_modules(self):
        text = BOOT.read_text(encoding="utf-8")
        self.assertIn("app-runtime-bridge.js?v=1.1", text)
        self.assertIn("app-update-manager.js?v=1.5", text)
        self.assertIn("market-learned-universe.js?v=2.0", text)
        self.assertIn("market-global-search.js?v=1.2", text)
        self.assertIn("market-data-health.js?v=1.2", text)
        self.assertIn("loadDataHealth();", text)
        self.assertLess(text.index("loadAppUpdateManager();"), text.index("loadLearnedUniverse();"))
        self.assertIn("window.VestraMarketCompanyBrief=Object.freeze", text)
        self.assertNotIn("quote-refresh-performance.js", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
