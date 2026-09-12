from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class MobileUiRefreshContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / 'mobile-ui-refresh.js').read_text(encoding='utf-8')
        cls.styles = (ROOT / 'mobile-ui-refresh.css').read_text(encoding='utf-8')
        cls.loader = (ROOT / 'market-static-universe.js').read_text(encoding='utf-8')
        cls.app = (ROOT / 'app.js').read_text(encoding='utf-8')

    def test_mobile_topbar_keeps_sidebar_access_and_removes_only_settings(self):
        self.assertIn('@media(max-width:720px)', self.styles)
        self.assertIn('.topbar #btnSidebarToggle{display:grid!important', self.styles)
        self.assertIn('.topbar #btnSettingsNav{display:none!important}', self.styles)
        self.assertIn('#btnSearchToggle', self.styles)
        self.assertIn('.topbar .fab', self.styles)

    def test_mobile_static_styles_live_outside_runtime_javascript(self):
        self.assertIn("link.rel = 'stylesheet'", self.source)
        self.assertIn("mobile-ui-refresh.css?v=1.0", self.source)
        self.assertNotIn('style.textContent = `', self.source)
        self.assertIn('.more-shortcuts', self.styles)
        self.assertIn('#sidebar.sidebar--open', self.styles)

    def test_mobile_drawer_uses_canonical_app_runtime_owner(self):
        for marker in (
            'function openSidebar()',
            'function closeSidebar()',
            'function wireSidebar()',
            'toggle.addEventListener("click", openSidebar)',
            'backdrop.addEventListener("click", closeSidebar)',
        ):
            self.assertIn(marker, self.app)
        self.assertNotIn('function setSidebarOpen(open)', self.source)
        self.assertNotIn('function ensureSidebarRuntime()', self.source)
        self.assertNotIn('vestraMobileDrawer', self.source)

    def test_more_hub_restores_direct_access_to_hidden_sidebar_destinations(self):
        for label in ('Dividendos', 'Análise', 'Importar', 'Backup'):
            self.assertIn(label, self.source)
        self.assertIn("callView('dividends')", self.source)
        self.assertIn("callView('analysis')", self.source)
        self.assertIn("btnGoImport", self.source)
        self.assertIn("btnExportJSON", self.source)

    def test_no_financial_state_or_remote_data_mutation(self):
        self.assertNotIn('state.', self.source)
        self.assertNotIn('fetch(', self.source)
        self.assertNotIn('localStorage', self.source)
        self.assertNotIn('indexedDB', self.source)

    def test_companion_is_reachable_from_static_loader(self):
        self.assertIn('ensureMobileUiRefresh', self.loader)
        self.assertIn('mobile-ui-refresh.js?v=1.4', self.loader)
        self.assertIn("version: '1.9'", self.loader)
        self.assertIn("version:'1.4'", self.source)


if __name__ == '__main__':
    unittest.main(verbosity=2)
