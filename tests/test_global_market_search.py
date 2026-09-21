from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
GLOBAL = ROOT / "market-global-search.js"
MARKET = ROOT / "market.js"
GLOBAL_CSS = ROOT / "market-global-search.css"
BOOTSTRAP = ROOT / "market-company-brief.js"
SW = ROOT / "sw.js"
WORKER_ROUTER = ROOT / "worker-router.js"


class GlobalMarketSearchTests(unittest.TestCase):
    def test_javascript_syntax(self):
        subprocess.run(["node", "--check", str(GLOBAL)], check=True, cwd=ROOT)
        subprocess.run(["node", "--check", str(MARKET)], check=True, cwd=ROOT)

    def test_exact_unknown_ticker_requires_provider_identity(self):
        text = GLOBAL.read_text(encoding="utf-8")
        self.assertIn("/quote?ticker=", text)
        self.assertIn("/market?ticker=", text)
        self.assertIn("function exactProviderIdentity(ticker,payload)", text)
        self.assertIn("provider===requested", text)
        self.assertIn("canonical===requested", text)
        self.assertIn("retrieval===requested", text)
        self.assertIn("identity_verified:true", text)
        self.assertIn("Provider identity mismatch", text)

    def test_name_search_is_separate_from_daily_catalogue(self):
        text = GLOBAL.read_text(encoding="utf-8")
        self.assertIn("${base}/search?q=", text)
        self.assertNotIn("query1.finance.yahoo.com/v1/finance/search", text)
        self.assertIn("PESQUISA GLOBAL · LIVE", text)
        self.assertNotIn("stocks-index.json", text)


    def test_name_search_uses_worker_proxy_not_browser_yahoo(self):
        text = GLOBAL.read_text(encoding="utf-8")
        router = WORKER_ROUTER.read_text(encoding="utf-8")
        self.assertIn("${base}/search?q=", text)
        self.assertNotIn("query1.finance.yahoo.com/v1/finance/search", text)
        self.assertIn("async function handleNameSearch(request)", router)
        self.assertIn("https://query1.finance.yahoo.com/v1/finance/search", router)
        self.assertIn("url.pathname === '/search'", router)

    def test_verified_broker_alias_keeps_hon_hai_searchable(self):
        text = GLOBAL.read_text(encoding="utf-8")
        self.assertIn("function brokerAliasSearch(query)", text)
        self.assertIn("ticker:'HHPD.IL'", text)
        self.assertIn("broker_symbols:Object.freeze(['HHPD'])", text)
        self.assertIn("'hon hai precision industry'", text)
        self.assertIn("'foxconn'", text)
        self.assertIn("const target=aliasTicker||q", text)
        self.assertIn("const rows=await validateExactTicker(target)", text)
        self.assertIn("brokerAliasSearch", text)

    def test_removed_parallel_dossier_formatters_do_not_return(self):
        text = GLOBAL.read_text(encoding="utf-8")
        self.assertNotIn("const money =", text)
        self.assertNotIn("const pct =", text)
        self.assertNotIn("const num =", text)
        self.assertNotIn("const compact =", text)

    def test_remote_search_delegates_to_canonical_dossier_owner(self):
        text = GLOBAL.read_text(encoding="utf-8")
        market = MARKET.read_text(encoding="utf-8")
        self.assertIn("market?.upsertRemoteStock", text)
        self.assertIn("nav?.openCompany", text)
        self.assertIn("market.upsertRemoteStock({", text)
        self.assertIn("await nav.openCompany(ticker,{origin:'market'", text)
        self.assertIn("market.openTicker(ticker)", text)
        self.assertIn("provider_symbol:ticker", text)
        self.assertIn("function upsertRemoteStock(row={})", market)
        self.assertIn("_remoteTransient:true", market)
        self.assertIn("_dossierHydrated:true", market)
        self.assertIn("upsertRemoteStock,toggleWatch", market)
        self.assertNotIn("content.innerHTML=", text)
        self.assertNotIn("DOSSIER GLOBAL · LIVE", text)
        self.assertNotIn("Não tem ainda Score Vestra pré-calculado", text)

    def test_remote_dossier_ignores_stale_async_responses(self):
        text = GLOBAL.read_text(encoding="utf-8")
        self.assertIn("let remoteOpenSeq = 0;", text)
        self.assertIn("const request=++remoteOpenSeq;", text)
        self.assertIn("request===remoteOpenSeq", text)
        self.assertIn("txt(sh.dataset.ticker).toUpperCase()===ticker", text)
        self.assertIn("if(request!==remoteOpenSeq) return false;", text)

    def test_remote_dossier_fetch_has_a_bounded_deadline(self):
        text = GLOBAL.read_text(encoding="utf-8")
        self.assertIn("const REMOTE_FETCH_TIMEOUT_MS = 12000;", text)
        self.assertIn("async function fetchRemoteWithDeadline", text)
        self.assertIn("typeof AbortController==='function'", text)
        self.assertIn("Promise.race([request,timeout])", text)
        self.assertIn("controller?.abort()", text)
        self.assertIn("Timeout a carregar dados globais.", text)
        self.assertIn("fetchRemoteWithDeadline(base+'/market?ticker='+encodeURIComponent(ticker)", text)

    def test_search_validation_fetches_have_short_deadlines(self):
        text = GLOBAL.read_text(encoding="utf-8")
        self.assertIn("const SEARCH_FETCH_TIMEOUT_MS = 6000;", text)
        self.assertIn("/quote?ticker=", text)
        self.assertIn("SEARCH_FETCH_TIMEOUT_MS, 'Timeout a validar ticker.'", text)
        self.assertIn("SEARCH_FETCH_TIMEOUT_MS, 'Timeout na pesquisa global.'", text)

    def test_central_learning_fetch_has_deadline_and_retry_cleanup(self):
        text = GLOBAL.read_text(encoding="utf-8")
        self.assertIn("const LEARN_FETCH_TIMEOUT_MS = 8000;", text)
        self.assertIn("async function learnCentral(row, timeoutMs=LEARN_FETCH_TIMEOUT_MS)", text)
        self.assertIn("/learned-universe", text)
        self.assertIn("learnedPosted.delete(ticker);", text)

    def test_enter_validation_cannot_open_after_search_context_changes(self):
        text = GLOBAL.read_text(encoding="utf-8")
        self.assertIn("let enterOpenSeq = 0;", text)
        self.assertIn("function invalidatePendingEnterOpen(){ enterOpenSeq += 1; }", text)
        self.assertIn("const enterRequest=++enterOpenSeq", text)
        self.assertIn("enterRequest!==enterOpenSeq||txt(input.value).toUpperCase()!==q", text)
        self.assertIn("async function openRemoteTicker(ticker,options={})", text)

    def test_bootstrap_loads_current_module(self):
        text = BOOTSTRAP.read_text(encoding="utf-8")
        self.assertIn("market-learned-universe.js?v=3.0", text)
        self.assertIn("market-global-search.js?v=2.1", text)
        self.assertIn("market-data-health.js?v=1.3", text)

    def test_presentation_has_static_css_owner_and_offline_reachability(self):
        text = GLOBAL.read_text(encoding="utf-8")
        css = GLOBAL_CSS.read_text(encoding="utf-8")
        sw = SW.read_text(encoding="utf-8")
        self.assertIn("market-global-search.css?v=1.0", text)
        self.assertNotIn("document.createElement('style')", text)
        self.assertIn('.vestra-global-search{', css)
        self.assertIn('.vestra-global-search__row{', css)
        self.assertIn('"./market-global-search.css"', sw)
        self.assertIn("version:'2.1'", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
