from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / 'market-static-universe.js').read_text(encoding='utf-8')


class MarketStaticCompanionRetryTests(unittest.TestCase):
    def test_companion_script_has_bounded_deadline(self):
        self.assertIn("const COMPANION_LOAD_TIMEOUT_MS = 8000;", SOURCE)
        self.assertIn("timeoutId = setTimeout(fail, COMPANION_LOAD_TIMEOUT_MS);", SOURCE)
        self.assertIn("companionLoadTimeoutMs: COMPANION_LOAD_TIMEOUT_MS", SOURCE)

    def test_failed_or_stalled_companion_is_removed_before_retry(self):
        self.assertIn("const fail = () => {", SOURCE)
        self.assertIn("if (script.isConnected) script.remove();", SOURCE)
        self.assertIn("const onError = () => fail();", SOURCE)
        self.assertIn("script.addEventListener('error', onError, { once: true });", SOURCE)

    def test_success_clears_timeout_and_listener_ownership(self):
        self.assertIn("script.addEventListener('load', onLoad, { once: true });", SOURCE)
        self.assertIn("script.removeEventListener('load', onLoad);", SOURCE)
        self.assertIn("script.removeEventListener('error', onError);", SOURCE)
        self.assertIn("if (timeoutId !== null && typeof clearTimeout === 'function') clearTimeout(timeoutId);", SOURCE)
        self.assertIn("if (!window[globalName]) { fail(); return; }", SOURCE)

    def test_retry_is_bounded_to_one_automatic_attempt(self):
        self.assertIn("function loadCompanion(globalName, selector, src, datasetKey, attempt = 0)", SOURCE)
        self.assertIn("if (attempt < 1 && typeof setTimeout === 'function')", SOURCE)
        self.assertIn("setTimeout(() => loadCompanion(globalName, selector, src, datasetKey, attempt + 1), 1000);", SOURCE)

    def test_existing_or_ready_companion_still_deduplicates(self):
        self.assertIn("if (window[globalName] || document.querySelector(selector)) return;", SOURCE)

    def test_runtime_version_is_current(self):
        self.assertIn("version: '1.19'", SOURCE)


if __name__ == '__main__':
    unittest.main(verbosity=2)
