from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ServiceWorkerCacheGenerationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / "sw.js").read_text(encoding="utf-8")

    def test_bounded_precache_install_uses_a_fresh_cache_generation(self):
        self.assertIn('const CACHE_NAME = "vestra-cache-v161";', self.source)
        self.assertNotIn('const CACHE_NAME = "vestra-cache-v160";', self.source)
        self.assertIn('const cache = await caches.open(CACHE_NAME);', self.source)
        self.assertIn('APP_SHELL.map(asset => precacheAsset(cache, asset))', self.source)

    def test_install_fails_closed_if_any_shell_asset_fails(self):
        install_start = self.source.index('self.addEventListener("install"')
        activate_start = self.source.index('self.addEventListener("activate"')
        install_block = self.source[install_start:activate_start]
        self.assertIn('await Promise.all(APP_SHELL.map(asset => precacheAsset(cache, asset)))', install_block)
        self.assertNotIn('Promise.allSettled', install_block)

    def test_previous_generation_survives_until_activate_cleanup(self):
        install_start = self.source.index('self.addEventListener("install"')
        activate_start = self.source.index('self.addEventListener("activate"')
        install_block = self.source[install_start:activate_start]
        activate_block = self.source[activate_start:self.source.index('async function matchCached', activate_start)]
        self.assertNotIn('caches.delete(', install_block)
        self.assertIn('key === CACHE_NAME ? Promise.resolve() : caches.delete(key)', activate_block)
        self.assertIn('await self.clients.claim()', activate_block)


if __name__ == "__main__":
    unittest.main(verbosity=2)
