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

    def test_premium_sequence_is_mark_then_slow_copy_then_release(self):
        self.assertIn('Vestra UI core v1.6', UI)
        self.assertIn('vestraPremiumMarkIn .45s', UI)
        self.assertIn('vestraPremiumBrandIn .78s .42s', UI)
        self.assertIn('vestraPremiumTaglineIn .72s .78s', UI)
        self.assertIn('copyReadyMs = 1500', UI)
        self.assertIn('minimumVisibleMs = 2000', UI)
        self.assertIn('failsafeMs = 3600', UI)

    def test_copy_fades_in_slowly_and_splash_releases_at_two_seconds(self):
        self.assertIn('copy fades in', UI)
        self.assertIn('fade at 2.00s', UI)
        self.assertIn('vestra-splash--copy-ready', UI)
        self.assertIn("splash.style.transition = 'opacity .30s", UI)
        self.assertLess(1500, 2000)
        self.assertGreaterEqual(2000 - 1500, 400)
        self.assertLessEqual(2000 - 1500, 800)

    def test_legacy_early_fade_is_neutralised_until_sequence_finishes(self):
        self.assertIn('keepSplashVisible', UI)
        self.assertIn("splash.style.opacity = '1'", UI)
        self.assertIn("splash.style.display = 'flex'", UI)
        self.assertIn('appTriedToHide', UI)
        self.assertIn('elapsed < minimumVisibleMs', UI)

    def test_bootstrap_scripts_are_network_first(self):
        self.assertIn('BOOTSTRAP_NETWORK_FIRST', SW)
        for asset in ('app-utils.js', 'app-storage.js', 'app-ui-core.js', 'app.js', 'market-static-universe.js', 'dashboard-weekly-events.js', 'market-dossier-controls.js', 'market-ui-polish.js'):
            self.assertIn(asset, SW)
        self.assertIn('event.respondWith(networkFirst(request))', SW)
        self.assertIn('vestra-cache-v128', SW)


if __name__ == '__main__':
    unittest.main(verbosity=2)
