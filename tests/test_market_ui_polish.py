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

    def test_dossier_geometry_has_one_owner_and_one_fixed_action_group(self):
        self.assertNotIn('right:max(calc(env(safe-area-inset-right) + 68px),68px)!important', self.source)
        self.assertNotIn('#marketSheet .market-close-persistent,', self.source)
        self.assertNotIn('market-detail-actions', self.source)
        self.assertNotIn("document.createElement('style')", self.source)
        self.assertNotIn('style.textContent', self.source)
        self.assertIn("market-dossier-controls.css?v=1.0", self.dossier)
        self.assertNotIn("document.createElement('style')", self.dossier)
        self.assertNotIn('style.textContent', self.dossier)
        self.assertIn('.market-detail-actions{', self.dossier_css)
        self.assertIn('position:fixed!important', self.dossier_css)
        self.assertIn('gap:8px!important', self.dossier_css)
        self.assertIn('.market-watch--detail,', self.dossier_css)
        self.assertIn('.market-close{', self.dossier_css)
        self.assertIn('width:46px!important', self.dossier_css)
        self.assertIn('height:46px!important', self.dossier_css)
        self.assertIn('> .market-close-persistent', self.dossier_css)
        self.assertIn('display:none!important', self.dossier_css)
        self.assertIn("version: '1.3'", self.source)
        self.assertIn("version: '1.4'", self.dossier)
        self.assertIn('right:max(calc(env(safe-area-inset-right) - 20px),-20px)!important', self.dossier_css)

    def test_politicians_state_is_cleared_before_normal_market_mode_switch(self):
        self.assertIn("[data-politicians-mode]", self.source)
        self.assertIn("[data-market-mode]", self.source)
        self.assertIn("classList.remove('is-active')", self.source)
        self.assertIn("document.addEventListener('click', onClickCapture, true)", self.source)

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
        self.assertIn('market-analysis-tools-runtime.js?v=1.1', self.loader)
        self.assertIn("version: '1.9'", self.loader)

    def test_analysis_tools_have_searchable_compare_and_news_and_lazy_scanner(self):
        self.assertIn('marketCompareSearch', self.analysis_tools)
        self.assertIn('compareCandidates', self.analysis_tools)
        self.assertIn('marketNewsSearch', self.analysis_tools)
        self.assertIn('newsCandidates', self.analysis_tools)
        self.assertIn('VestraMarketScannerData', self.analysis_tools)
        self.assertIn('data-tool-scanner-strategy', self.analysis_tools)
        self.assertIn('overflow-y:auto', self.analysis_tools)
        self.assertIn('window.VestraNavigation', self.analysis_tools)
        self.assertIn("nav.openCompany(ticker, { origin: 'market' })", self.analysis_tools)
        self.assertNotIn('VestraMarket?.openTicker', self.analysis_tools)
        self.assertIn("version:'1.1'", self.analysis_tools)


if __name__ == '__main__':
    unittest.main(verbosity=2)
