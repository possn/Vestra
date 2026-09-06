from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
BRIDGE = ROOT / "app-runtime-bridge.js"
UPDATE = ROOT / "app-update-manager.js"
BOOT = ROOT / "market-company-brief.js"


class RuntimeWorkerRefreshV2Tests(unittest.TestCase):
    def test_javascript_syntax(self):
        subprocess.run(["node", "--check", str(BRIDGE)], check=True, cwd=ROOT)
        subprocess.run(["node", "--check", str(UPDATE)], check=True, cwd=ROOT)

    def test_bridge_has_canonical_worker_fallback(self):
        text = BRIDGE.read_text(encoding="utf-8")
        self.assertIn("https://delicate-bar-cc80.pedrossnunes.workers.dev", text)
        self.assertIn("workerUrl: CANONICAL_WORKER_URL", text)
        self.assertIn("version: '1.1'", text)

    def test_update_replaces_legacy_handler_without_overlay(self):
        text = UPDATE.read_text(encoding="utf-8")
        self.assertIn("document.getElementById('btnForceUpdate')", text)
        self.assertIn("current.cloneNode(true)", text)
        self.assertIn("current.replaceWith(button)", text)
        self.assertIn("button.addEventListener('click'", text)
        self.assertIn("version: '1.2'", text)
        self.assertNotIn("document.addEventListener('click'", text)
        self.assertNotIn("stopImmediatePropagation", text)
        self.assertNotIn("appLoadingOverlay", text)
        self.assertNotIn("getRegistrations", text)
        self.assertNotIn(".unregister(", text)
        self.assertNotIn("caches.keys", text)

    def test_bootstrap_bumps_runtime_modules(self):
        text = BOOT.read_text(encoding="utf-8")
        self.assertIn("app-runtime-bridge.js?v=1.1", text)
        self.assertIn("app-update-manager.js?v=1.2", text)
        self.assertIn("market-learned-universe.js?v=2.0", text)
        self.assertIn("market-global-search.js?v=1.2", text)
        self.assertIn("market-data-health.js?v=1.0", text)
        self.assertIn("loadDataHealth();", text)
        self.assertLess(text.index("loadAppUpdateManager();"), text.index("loadLearnedUniverse();"))
        self.assertIn("version:'1.8'", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
