from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / 'market-static-universe.js').read_text(encoding='utf-8')


class MarketEtfIntelligenceLoaderRetryTests(unittest.TestCase):
    def test_failed_etf_script_is_removed_and_retryable(self):
        self.assertIn("const onError = () => discardAndFinish();", SOURCE)
        self.assertIn("if (script.isConnected) script.remove();", SOURCE)
        self.assertIn("etfIntelligencePromise = null;", SOURCE)

    def test_shared_etf_loader_has_bounded_deadline(self):
        self.assertIn("const ETF_INTELLIGENCE_LOAD_TIMEOUT_MS = 8000;", SOURCE)
        self.assertIn("timeoutId = setTimeout(discardAndFinish, ETF_INTELLIGENCE_LOAD_TIMEOUT_MS);", SOURCE)
        self.assertIn("if (timeoutId !== null && typeof clearTimeout === 'function') clearTimeout(timeoutId);", SOURCE)
        self.assertIn("etfIntelligenceLoadTimeoutMs: ETF_INTELLIGENCE_LOAD_TIMEOUT_MS", SOURCE)

    def test_loaded_script_without_api_is_removed_for_retry(self):
        self.assertIn("const api = window.VestraEtfIntelligence || null;", SOURCE)
        self.assertIn("if (!api) { discardAndFinish(); return; }", SOURCE)
        self.assertIn("script.removeEventListener('load', onLoad);", SOURCE)
        self.assertIn("script.removeEventListener('error', onError);", SOURCE)

    def test_existing_inflight_script_still_deduplicates(self):
        self.assertIn("const existing = document.querySelector('script[data-vestra-etf-intelligence]');", SOURCE)
        self.assertIn("if (etfIntelligencePromise) return etfIntelligencePromise;", SOURCE)

    def test_market_loading_still_awaits_optional_intelligence_only_within_deadline(self):
        self.assertIn("const etfReady = ensureMarketCompanions();", SOURCE)
        self.assertIn("return ensureEtfIntelligence();", SOURCE)
        self.assertIn("await etfReady;", SOURCE)
        self.assertIn("version: '1.21'", SOURCE)


if __name__ == '__main__':
    unittest.main(verbosity=2)
