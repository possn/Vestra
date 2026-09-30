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
        cls.dossier_styles = (ROOT / 'market-dossier-controls.css').read_text(encoding='utf-8')

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
            'function toggleSidebar()',
            'function wireSidebar()',
            'toggle.addEventListener("click", toggleSidebar)',
            'if (!desktopSidebarMode()) closeSidebar()',
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

    def test_mobile_close_controls_have_single_stylesheet_owner(self):
        self.assertIn('Persistent close controls', self.styles)
        self.assertIn('.modal__head{', self.styles)
        self.assertIn('position:sticky', self.styles)
        self.assertNotIn('#marketSheet:not([hidden])>.market-close-persistent{', self.styles)
        self.assertIn('> .market-close-persistent{', self.dossier_styles)
        self.assertIn('position:fixed!important', self.dossier_styles)
        self.assertIn('top:max(calc(env(safe-area-inset-top,0px) + 62px),72px)!important', self.dossier_styles)

    def test_iphone_fixed_navigation_avoids_backdrop_recomposition(self):
        self.assertIn('iPhone interaction fast path', self.styles)
        self.assertIn('.topbar,.bottomnav{', self.styles)
        self.assertIn('-webkit-backdrop-filter:none!important', self.styles)
        self.assertIn('backdrop-filter:none!important', self.styles)
        self.assertIn('touch-action:manipulation', self.styles)

    def test_view_switch_defers_forced_scroll_out_of_tap_handler(self):
        marker = 'Keep forced layout/scroll work out of the tap handler'
        self.assertIn(marker, self.app)
        section = self.app[self.app.index(marker):self.app.index(marker) + 320]
        self.assertIn('requestAnimationFrame(() => {', section)
        self.assertIn('window.scrollTo(0, 0)', section)

    def test_companion_is_reachable_from_static_loader(self):
        self.assertIn('ensureMobileUiRefresh', self.loader)
        self.assertIn('mobile-ui-refresh.js?v=1.5', self.loader)
        self.assertIn("version: '1.30'", self.loader)
        self.assertIn("version:'1.5'", self.source)


if __name__ == '__main__':
    unittest.main(verbosity=2)
