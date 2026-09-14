from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / 'market-static-universe.js').read_text(encoding='utf-8')


class MarketStaticCompanionRetryTests(unittest.TestCase):
    def test_failed_companion_script_is_removed_before_retry(self):
        self.assertIn("script.addEventListener('error', () => {", SOURCE)
        self.assertIn("if (script.isConnected) script.remove();", SOURCE)

    def test_retry_is_bounded_to_one_automatic_attempt(self):
        self.assertIn("function loadCompanion(globalName, selector, src, datasetKey, attempt = 0)", SOURCE)
        self.assertIn("if (attempt < 1) setTimeout(() => loadCompanion(globalName, selector, src, datasetKey, attempt + 1), 1000);", SOURCE)

    def test_existing_or_ready_companion_still_deduplicates(self):
        self.assertIn("if (window[globalName] || document.querySelector(selector)) return;", SOURCE)


if __name__ == '__main__':
    unittest.main(verbosity=2)
