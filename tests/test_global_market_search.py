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

    def test_bootstrap_loads_current_module(self):
        text = BOOTSTRAP.read_text(encoding="utf-8")
        self.assertIn("market-learned-universe.js?v=2.0", text)
        self.assertIn("market-global-search.js?v=1.3", text)
        self.assertIn("market-data-health.js?v=1.2", text)
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
        self.assertIn("version:'1.3'", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
