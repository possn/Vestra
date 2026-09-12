from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
UI = (ROOT / 'app-ui-core.js').read_text(encoding='utf-8')
BASE = (ROOT / 'styles.css').read_text(encoding='utf-8')
SW = (ROOT / 'sw.js').read_text(encoding='utf-8')


class SplashBootstrapTests(unittest.TestCase):
    def test_ui_core_owns_effective_splash_lifecycle_before_app_monolith(self):
        self.assertIn('installPremiumSplashWatchdog', UI)
        self.assertIn('vestra:app-ready', UI)
        self.assertIn('setTimeout(() => releaseSplash', UI)
        self.assertNotIn('new MutationObserver(', UI)
        self.assertNotIn('appTriedToHide', UI)

    def test_splash_background_is_fully_opaque(self):
        self.assertIn('background:#eef0ec!important', UI)
        self.assertIn('backdrop-filter:none!important', UI)
        self.assertIn('-webkit-backdrop-filter:none!important', UI)

    def test_premium_visibility_rules_contain_legacy_inline_writes(self):
        self.assertIn('display:flex!important;opacity:1!important', UI)
        self.assertIn('pointer-events:auto!important;transition:none!important', UI)
        self.assertIn('.vestra-splash.vestra-splash--premium.vestra-splash--leaving', UI)
        self.assertIn('display:flex!important;opacity:0!important;pointer-events:none!important', UI)
        self.assertIn('beat any stale inline opacity/display writes', UI)

    def test_base_styles_own_single_entrance_animation(self):
        self.assertIn('Vestra UI core v2.0', UI)
        self.assertIn('animation:vestraMarkIn .72s', BASE)
        self.assertIn('animation:vestraCopyIn .55s .14s', BASE)
        self.assertIn('animation:vestraCopyIn .55s .22s', BASE)
        self.assertIn('animation:vestraGlow 1.7s', BASE)
        self.assertNotIn('vestraPremiumMarkIn', UI)
        self.assertNotIn('vestraPremiumBrandIn', UI)
        self.assertNotIn('vestraPremiumTaglineIn', UI)
        self.assertNotIn('vestraPremiumGlow', UI)
        self.assertIn('must not replace the\n   animation-name after parse', UI)
        self.assertIn('Do not swap animation names here', UI)

    def test_release_keeps_single_fade_owner_and_existing_hold_contract(self):
        self.assertIn('copyReadyMs = 2000', UI)
        self.assertIn('minimumVisibleMs = 4000', UI)
        self.assertIn('failsafeMs = 6200', UI)
        self.assertIn('transition:opacity .68s cubic-bezier(.4,0,.2,1)!important', UI)
        self.assertIn("splash.classList.add('vestra-splash--leaving')", UI)
        self.assertIn('}, 720);', UI)

    def test_bootstrap_scripts_are_network_first(self):
        self.assertIn('BOOTSTRAP_NETWORK_FIRST', SW)
        for asset in ('app-utils.js', 'app-storage.js', 'app-ui-core.js', 'app.js', 'market-static-universe.js', 'dashboard-weekly-events.js', 'market-dossier-controls.js', 'market-ui-polish.js'):
            self.assertIn(asset, SW)
        self.assertIn('event.respondWith(networkFirst(request))', SW)
        self.assertRegex(SW, r"vestra-cache-v\d+")


if __name__ == '__main__':
    unittest.main(verbosity=2)
