from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / 'market-static-universe.js').read_text(encoding='utf-8')


class MarketEtfIntelligenceLoaderRetryTests(unittest.TestCase):
    def test_failed_etf_script_is_removed(self):
        self.assertIn("script.addEventListener('error', () => {", SOURCE)
        self.assertIn("if (script.isConnected) script.remove();", SOURCE)

    def test_shared_etf_promise_resets_after_settlement(self):
        self.assertIn("const finish = value => { etfIntelligencePromise = null; resolve(value); };", SOURCE)
        self.assertIn("script.addEventListener('load', () => finish(window.VestraEtfIntelligence || null), { once: true });", SOURCE)
        self.assertIn("finish(null);", SOURCE)

    def test_existing_inflight_script_still_deduplicates(self):
        self.assertIn("const existing = document.querySelector('script[data-vestra-etf-intelligence]');", SOURCE)
        self.assertIn("if (etfIntelligencePromise) return etfIntelligencePromise;", SOURCE)


if __name__ == '__main__':
    unittest.main(verbosity=2)
