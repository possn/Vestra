from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
GLOBAL = ROOT / "market-global-search.js"
BOOTSTRAP = ROOT / "market-company-brief.js"


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
        self.assertNotIn("score: 50", text)

    def test_bootstrap_loads_module(self):
        text = BOOTSTRAP.read_text(encoding="utf-8")
        self.assertIn("market-global-search.js?v=1.0", text)
        self.assertIn("loadGlobalMarketSearch();", text)
        self.assertIn("version:'1.4'", text)


if __name__ == "__main__":
    unittest.main(verbosity=2)
