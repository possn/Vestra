from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
GLOBAL = ROOT / "market-global-search.js"
GLOBAL_CSS = ROOT / "market-global-search.css"
BOOTSTRAP = ROOT / "market-company-brief.js"
SW = ROOT / "sw.js"


class GlobalMarketSearchTests(unittest.TestCase):
    def test_javascript_syntax(self):
        subprocess.run(["node", "--check", str(GLOBAL)], check=True, cwd=ROOT)

    def test_exact_unknown_ticker_requires_provider_identity(self):
        text = GLOBAL.read_text(encoding="utf-8")
        self.assertIn("/quote?ticker=", text)
        self.assertIn("function exactProviderIdentity(ticker,payload)", text)
        self.assertIn("provider===requested", text)
        self.assertIn("canonical===requested", text)
        self.assertIn("retrieval===requested", text)
        self.assertIn("identity_verified:true", text)
        self.assertNotIn("/market?ticker=", text)

    def test_name_search_preserves_exchange_qualified_provider_symbol(self):
        text = GLOBAL.read_text(encoding="utf-8")
        self.assertIn("/v1/finance/search", text)
        self.assertIn("ticker:txt(x.symbol).toUpperCase()", text)
        self.assertIn("PESQUISA GLOBAL · LIVE", text)
        self.assertNotIn("stocks-index.json", text)

    def test_global_result_hands_off_to_canonical_dossier(self):
        text = GLOBAL.read_text(encoding="utf-8")
        self.assertIn("market?.upsertExternalStock", text)
        self.assertIn("nav?.openCompany", text)
        self.assertIn("await market.ensureLoaded?.()", text)
        self.assertIn("const stock=market.upsertExternalStock({", text)
        self.assertIn("await nav.openCompany(ticker,{origin:'market'", text)
        self.assertNotIn("DOSSIER GLOBAL · LIVE", text)
        self.assertNotIn("content.innerHTML=", text)
        self.assertNotIn("remoteMetric(", text)

    def test_remote_open_ignores_stale_async_validation(self):
        text = GLOBAL.read_text(encoding="utf-8")
        self.assertIn("let remoteOpenSeq = 0;", text)
        self.assertIn("const request=++remoteOpenSeq;", text)
        self.assertGreaterEqual(text.count("request!==remoteOpenSeq"), 2)

    def test_search_validation_fetches_have_short_deadlines(self):
        text = GLOBAL.read_text(encoding="utf-8")
        self.assertIn("const SEARCH_FETCH_TIMEOUT_MS = 6000;", text)
        self.assertIn("`${base}/quote?ticker=${encodeURIComponent(ticker)}`", text)
        self.assertIn("SEARCH_FETCH_TIMEOUT_MS, 'Timeout a validar ticker.'", text)
        self.assertIn("SEARCH_FETCH_TIMEOUT_MS, 'Timeout na pesquisa global.'", text)
        self.assertNotIn("await fetch(`${base}/quote?ticker=", text)
        self.assertNotIn("const r = await fetch(u, {cache:'no-store'});", text)

    def test_central_learning_fetch_has_deadline_and_retry_cleanup(self):
        text = GLOBAL.read_text(encoding="utf-8")
        self.assertIn("const LEARN_FETCH_TIMEOUT_MS = 8000;", text)
        self.assertIn("async function learnCentral(row, timeoutMs=LEARN_FETCH_TIMEOUT_MS)", text)
        self.assertIn("await fetchRemoteWithDeadline(`${base}/learned-universe`", text)
        self.assertIn("timeoutMs, 'Timeout a guardar ticker aprendido.'", text)
        self.assertIn("learnedPosted.delete(ticker);", text)

    def test_enter_validation_cannot_open_after_search_context_changes(self):
        text = GLOBAL.read_text(encoding="utf-8")
        self.assertIn("let enterOpenSeq = 0;", text)
        self.assertIn("function invalidatePendingEnterOpen(){ enterOpenSeq += 1; }", text)
        self.assertIn("const enterRequest=++enterOpenSeq", text)
        self.assertIn("enterRequest!==enterOpenSeq||txt(input.value).toUpperCase()!==q", text)
        self.assertIn("async function openRemoteTicker(ticker,options={})", text)

    def test_bootstrap_loads_exact_identity_generation(self):
        text = BOOTSTRAP.read_text(encoding="utf-8")
        self.assertIn("market-learned-universe.js?v=3.0", text)
        self.assertIn("market-global-search.js?v=1.8", text)
        self.assertIn("market-data-health.js?v=1.3", text)
        self.assertIn("loadLearnedUniverse();", text)
        self.assertIn("loadDataHealth();", text)

    def test_presentation_has_static_css_owner_and_offline_reachability(self):
        text = GLOBAL.read_text(encoding="utf-8")
        css = GLOBAL_CSS.read_text(encoding="utf-8")
        sw = SW.read_text(encoding="utf-8")
        self.assertIn("market-global-search.css?v=1.0", text)
        self.assertNotIn("document.createElement('style')", text)
        self.assertNotIn('style.textContent', text)
        self.assertIn('.vestra-global-search{', css)
        self.assertIn('.vestra-global-search__row{', css)
        self.assertIn('"./market-global-search.css"', sw)
        self.assertIn("version:'1.8'", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
