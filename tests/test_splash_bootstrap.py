from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
UI = (ROOT / 'app-ui-core.js').read_text(encoding='utf-8')
SW = (ROOT / 'sw.js').read_text(encoding='utf-8')


class SplashBootstrapTests(unittest.TestCase):
    def test_splash_has_independent_watchdog_before_app_monolith(self):
        self.assertIn('installPremiumSplashWatchdog', UI)
        self.assertIn('MutationObserver', UI)
        self.assertIn('vestra:app-ready', UI)
        self.assertIn('setTimeout(() => releaseSplash', UI)

    def test_premium_sequence_is_mark_then_brand_then_tagline(self):
        self.assertIn('vestraPremiumMarkIn', UI)
        self.assertIn('vestraPremiumBrandIn', UI)
        self.assertIn('vestraPremiumTaglineIn', UI)
        self.assertIn('1.05s', UI)
        self.assertIn('1.65s', UI)
        self.assertIn('minimumVisibleMs = 2700', UI)

    def test_legacy_early_fade_is_neutralised_until_copy_finishes(self):
        self.assertIn('keepSplashVisible', UI)
        self.assertIn("splash.style.opacity = '1'", UI)
        self.assertIn("splash.style.display = 'flex'", UI)
        self.assertIn('appTriedToHide', UI)
        self.assertIn('elapsed < minimumVisibleMs', UI)

    def test_bootstrap_scripts_are_network_first(self):
        self.assertIn('BOOTSTRAP_NETWORK_FIRST', SW)
        for asset in ('app-utils.js', 'app-storage.js', 'app-ui-core.js', 'app.js', 'market-static-universe.js', 'dashboard-weekly-events.js'):
            self.assertIn(asset, SW)
        self.assertIn('event.respondWith(networkFirst(request))', SW)
        self.assertIn('vestra-cache-v128', SW)


if __name__ == '__main__':
    unittest.main(verbosity=2)
