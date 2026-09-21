from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / 'market-company-brief.js').read_text(encoding='utf-8')


class MarketCompanyBriefLoaderRetryTests(unittest.TestCase):
    def test_dependency_script_loader_has_bounded_deadline(self):
        self.assertIn("const SCRIPT_LOAD_TIMEOUT_MS=8000;", SOURCE)
        self.assertIn("timeoutId=setTimeout(fail,SCRIPT_LOAD_TIMEOUT_MS)", SOURCE)
        self.assertIn("scriptLoadTimeoutMs:SCRIPT_LOAD_TIMEOUT_MS", SOURCE)

    def test_failure_removes_stuck_script_and_retries_once(self):
        self.assertIn("if(s.isConnected)s.remove();", SOURCE)
        self.assertIn("if(attempt<1&&typeof setTimeout==='function')", SOURCE)
        self.assertIn("loadScript(id,src,ready,onload,attempt+1)", SOURCE)
        self.assertIn("s.addEventListener('error',onError,{once:true})", SOURCE)

    def test_existing_script_is_watched_and_cleaned_up(self):
        self.assertIn("const existing=document.getElementById(id);", SOURCE)
        self.assertIn("const s=existing||document.createElement('script');", SOURCE)
        self.assertIn("s.removeEventListener('load',onLoad);", SOURCE)
        self.assertIn("s.removeEventListener('error',onError);", SOURCE)
        self.assertIn("clearTimeout(timeoutId)", SOURCE)

    def test_load_without_expected_global_is_retryable(self):
        self.assertIn("const isReady=()=>typeof ready==='function'?!!ready():!!ready;", SOURCE)
        self.assertIn("if(!isReady()){fail();return;}", SOURCE)
        self.assertIn("()=>window.VestraGlobalMarketSearch", SOURCE)
        self.assertIn("()=>window.VestraLearnedUniverse", SOURCE)
        self.assertIn("()=>window.VestraRuntimeBridge", SOURCE)

    def test_runtime_version_and_existing_dependency_chain_are_preserved(self):
        self.assertIn("market-global-search.js?v=2.1", SOURCE)
        self.assertIn("market-learned-universe.js?v=3.0", SOURCE)
        self.assertIn("app-runtime-bridge.js?v=1.1", SOURCE)
        self.assertIn("loadRuntimeBridge();", SOURCE)
        self.assertIn("version:'2.1'", SOURCE)


if __name__ == '__main__':
    unittest.main(verbosity=2)
