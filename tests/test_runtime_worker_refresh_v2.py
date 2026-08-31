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

    def test_update_intercepts_legacy_handler_without_overlay(self):
        text = UPDATE.read_text(encoding="utf-8")
        self.assertIn("document.addEventListener('click', captureForceUpdate, true)", text)
        self.assertIn("event.stopImmediatePropagation()", text)
        self.assertNotIn("appLoadingOverlay", text)
        self.assertNotIn("getRegistrations", text)
        self.assertNotIn("unregister", text)
        self.assertNotIn("caches.keys", text)

    def test_bootstrap_bumps_runtime_modules(self):
        text = BOOT.read_text(encoding="utf-8")
        self.assertIn("app-runtime-bridge.js?v=1.1", text)
        self.assertIn("app-update-manager.js?v=1.1", text)
        self.assertIn("version:'1.6'", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
