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

    def test_exact_unknown_ticker_uses_worker_quote_and_market(self):
        text = GLOBAL.read_text(encoding="utf-8")
        self.assertIn("/quote?ticker=", text)
        self.assertIn("/market?ticker=", text)
        self.assertIn("validateExactTicker", text)
        self.assertIn("openRemoteTicker", text)

    def test_name_search_is_separate_from_daily_catalogue(self):
        text = GLOBAL.read_text(encoding="utf-8")
        self.assertIn("/v1/finance/search", text)
        self.assertIn("PESQUISA GLOBAL · LIVE", text)
        self.assertNotIn("stocks-index.json", text)

    def test_remote_dossier_does_not_fake_vestra_score(self):
        text = GLOBAL.read_text(encoding="utf-8")
        self.assertIn("Não tem ainda Score Vestra pré-calculado", text)
        self.assertIn("próximo pipeline diário promove-a para o universo oficial", text)
        self.assertNotIn("score: 50", text)

    def test_remote_dossier_ignores_stale_async_responses(self):
        text = GLOBAL.read_text(encoding="utf-8")
        self.assertIn("let remoteOpenSeq = 0;", text)
        self.assertIn("const request=++remoteOpenSeq;", text)
        self.assertIn("request===remoteOpenSeq", text)
        self.assertIn("txt(sh.dataset.ticker).toUpperCase()===ticker", text)
        self.assertGreaterEqual(text.count("if(!ownsRemoteOpen(request,sh,ticker))return;"), 4)

    def test_remote_dossier_fetch_has_a_bounded_deadline(self):
        text = GLOBAL.read_text(encoding="utf-8")
        self.assertIn("const REMOTE_FETCH_TIMEOUT_MS = 12000;", text)
        self.assertIn("async function fetchRemoteWithDeadline", text)
        self.assertIn("typeof AbortController==='function'", text)
        self.assertIn("Promise.race([request,timeout])", text)
        self.assertIn("controller?.abort()", text)
        self.assertIn("Timeout a carregar dados globais.", text)
        self.assertIn("await fetchRemoteWithDeadline(`${base}/market?ticker=", text)
        self.assertNotIn("await fetch(`${base}/market?ticker=", text)
        self.assertIn("if(!ownsRemoteOpen(request,sh,ticker))return;\n      content.innerHTML=", text)

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
        self.assertNotIn("const response = await fetch(`${base}/learned-universe`", text)

    def test_enter_validation_cannot_open_after_search_context_changes(self):
        text = GLOBAL.read_text(encoding="utf-8")
        self.assertIn("let enterOpenSeq = 0;", text)
        self.assertIn("function invalidatePendingEnterOpen(){ enterOpenSeq += 1; }", text)
        self.assertIn("const enterRequest=++enterOpenSeq", text)
        self.assertIn("enterRequest!==enterOpenSeq||txt(input.value).toUpperCase()!==q", text)
        self.assertIn("if(e.target?.id==='marketSearch'){invalidatePendingEnterOpen();schedule(e.target.value);}", text)
        self.assertIn("async function openRemoteTicker(ticker){\n    invalidatePendingEnterOpen();", text)

    def test_bootstrap_loads_current_module(self):
        text = BOOTSTRAP.read_text(encoding="utf-8")
        self.assertIn("market-learned-universe.js?v=2.1", text)
        self.assertIn("market-global-search.js?v=1.7", text)
        self.assertIn("market-data-health.js?v=1.3", text)
        self.assertIn("loadLearnedUniverse();", text)
        self.assertIn("loadDataHealth();", text)
        self.assertIn("window.VestraMarketCompanyBrief=Object.freeze", text)

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
        self.assertIn("version:'1.7'", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
