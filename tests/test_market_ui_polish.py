from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class MarketUiPolishContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / 'market-ui-polish.js').read_text(encoding='utf-8')
        cls.dossier = (ROOT / 'market-dossier-controls.js').read_text(encoding='utf-8')
        cls.dossier_css = (ROOT / 'market-dossier-controls.css').read_text(encoding='utf-8')
        cls.loader = (ROOT / 'market-static-universe.js').read_text(encoding='utf-8')
        cls.analysis_tools = (ROOT / 'market-analysis-tools-runtime.js').read_text(encoding='utf-8')
        cls.analysis_tools_css = (ROOT / 'market-analysis-tools-runtime.css').read_text(encoding='utf-8')

    def test_dossier_geometry_has_one_owner_and_one_fixed_action_group(self):
        self.assertNotIn('right:max(calc(env(safe-area-inset-right) + 68px),68px)!important', self.source)
        self.assertNotIn('#marketSheet .market-close-persistent,', self.source)
        self.assertNotIn('market-detail-actions', self.source)
        self.assertNotIn("document.createElement('style')", self.source)
        self.assertNotIn('style.textContent', self.source)
        self.assertIn("market-dossier-controls.css?v=1.2", self.dossier)
        self.assertNotIn("document.createElement('style')", self.dossier)
        self.assertNotIn('style.textContent', self.dossier)
        self.assertIn('.market-detail-actions{', self.dossier_css)
        self.assertIn('position:fixed!important', self.dossier_css)
        self.assertIn('gap:8px!important', self.dossier_css)
        self.assertIn('> .market-watch--detail{', self.dossier_css)
        self.assertIn('.market-detail-actions .market-close{', self.dossier_css)
        self.assertIn('width:44px!important', self.dossier_css)
        self.assertIn('height:44px!important', self.dossier_css)
        self.assertIn('> .market-close-persistent{', self.dossier_css)
        self.assertIn('display:grid!important', self.dossier_css)
        self.assertIn('visibility:visible!important', self.dossier_css)
        self.assertIn('pointer-events:auto!important', self.dossier_css)
        self.assertIn("version: '1.3'", self.source)
        self.assertIn("version: '1.8'", self.dossier)
        self.assertIn('right:max(calc(env(safe-area-inset-right) + 66px),66px)!important', self.dossier_css)
        self.assertIn('.market-detail-actions .market-close{\n  display:none!important', self.dossier_css)

    def test_politicians_state_is_cleared_before_normal_market_mode_switch(self):
        self.assertIn("[data-politicians-mode]", self.source)
        self.assertIn("[data-market-mode]", self.source)
        self.assertIn("classList.remove('is-active')", self.source)
        self.assertIn("document.addEventListener('click', onClickCapture, true)", self.source)

    def test_stock_themes_loader_is_bounded_and_retryable(self):
        self.assertIn('const STOCK_THEMES_LOAD_TIMEOUT_MS = 8000', self.source)
        self.assertIn('let stockThemesLoadPromise = null', self.source)
        self.assertIn("script.addEventListener('load', onLoad, { once: true })", self.source)
        self.assertIn("script.addEventListener('error', onError, { once: true })", self.source)
        self.assertIn('timeoutId = setTimeout(fail, STOCK_THEMES_LOAD_TIMEOUT_MS)', self.source)
        self.assertIn('if (script.isConnected) script.remove()', self.source)
        self.assertIn('if (attempt < 1', self.source)
        self.assertIn('setTimeout(() => ensureStockThemesTools(attempt + 1), 1000)', self.source)
        self.assertIn('stockThemesLoadPromise = null', self.source)
        self.assertNotIn("if (window.VestraMarketStockThemesTools || document.querySelector('script[data-vestra-stock-themes-tools]')) return;", self.source)

    def test_no_market_data_or_financial_semantics_changed(self):
        self.assertNotIn('fetch(', self.source)
        self.assertNotIn('score', self.source.lower())
        self.assertNotIn('risk_gate', self.source.lower())
        self.assertNotIn('localStorage', self.source)
        self.assertNotIn('indexedDB', self.source)

    def test_companions_are_reachable_from_loader(self):
        self.assertIn('ensureMarketUiPolish', self.loader)
        self.assertIn('market-ui-polish.js?v=1.3', self.loader)
        self.assertIn('ensureAnalysisToolsRuntime', self.loader)
        self.assertIn('market-analysis-tools-runtime.js?v=1.3', self.loader)
        self.assertIn("version: '1.12'", self.loader)

    def test_analysis_tools_have_searchable_compare_and_news_and_lazy_scanner(self):
        self.assertIn('marketCompareSearch', self.analysis_tools)
        self.assertIn('compareCandidates', self.analysis_tools)
        self.assertIn('marketNewsSearch', self.analysis_tools)
        self.assertIn('newsCandidates', self.analysis_tools)
        self.assertIn('VestraMarketScannerData', self.analysis_tools)
        self.assertIn('data-tool-scanner-strategy', self.analysis_tools)
        self.assertIn('window.VestraNavigation', self.analysis_tools)
        self.assertIn("nav.openCompany(ticker, { origin: 'market' })", self.analysis_tools)
        self.assertNotIn('VestraMarket?.openTicker', self.analysis_tools)
        self.assertIn("market-analysis-tools-runtime.css?v=1.0", self.analysis_tools)
        self.assertNotIn("document.createElement('style')", self.analysis_tools)
        self.assertNotIn('style.textContent', self.analysis_tools)
        self.assertIn('overflow-y:auto', self.analysis_tools_css)
        self.assertIn('.market-tool-runtime__search', self.analysis_tools_css)
        self.assertIn('.market-tool-runtime__chips', self.analysis_tools_css)
        self.assertIn("version:'1.3'", self.analysis_tools)


if __name__ == '__main__':
    unittest.main(verbosity=2)
