from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ServiceWorkerCacheGenerationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = (ROOT / "sw.js").read_text(encoding="utf-8")

    def test_bounded_precache_install_uses_a_fresh_cache_generation(self):
        self.assertIn('const CACHE_NAME = "vestra-cache-v195";', self.source)
        self.assertNotIn('const CACHE_NAME = "vestra-cache-v178";', self.source)
        self.assertIn('const cache = await caches.open(CACHE_NAME);', self.source)
        self.assertIn('"./data/portfolio-sectors.json"', self.source)
        self.assertIn('APP_SHELL.map(asset => precacheAsset(cache, asset))', self.source)
        self.assertIn('"./app-xlsx-loader.js"', self.source)
        self.assertIn('"app-xlsx-loader.js"', self.source)
        self.assertIn('"./market-runtime-loader.js"', self.source)
        self.assertIn('"market-runtime-loader.js"', self.source)
        self.assertIn('"./market.js"', self.source)
        self.assertIn('"./app-broker-import-loader.js"', self.source)
        self.assertIn('"app-broker-import-loader.js"', self.source)
        self.assertIn('"./app-broker-workbook.js"', self.source)
        self.assertIn('"./app-broker-parsers.js"', self.source)
        self.assertIn('"./market-company-brief.js"', self.source)
        self.assertIn('"./market-metric-cleanup.js"', self.source)

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


    def test_styles_are_network_first_before_generic_static_asset_cache(self):
        fetch_start = self.source.index('self.addEventListener("fetch"')
        fetch_block = self.source[fetch_start:]
        style_branch = 'if (request.destination === "style")'
        generic_branch = 'if (["script", "worker", "manifest"].includes(request.destination))'
        self.assertIn(style_branch, fetch_block)
        self.assertIn('event.respondWith(networkFirst(request)); return;', fetch_block)
        self.assertLess(fetch_block.index(style_branch), fetch_block.index(generic_branch))
        self.assertNotIn('["script", "style", "worker", "manifest"]', fetch_block)


    def test_versioned_runtime_urls_try_network_before_ignore_search_fallback(self):
        start = self.source.index("async function staleWhileRevalidate")
        end = self.source.index('self.addEventListener("fetch"', start)
        block = self.source[start:end]
        self.assertIn('const exact = await cache.match(request);', block)
        self.assertIn('const hasVersionQuery =', block)
        self.assertIn('if (hasVersionQuery) {', block)
        self.assertIn('const fresh = await refresh;', block)
        self.assertIn('const fallback = await cache.match(request, { ignoreSearch: true });', block)
        self.assertLess(block.index('if (hasVersionQuery) {'), block.index('const cached = await matchCached(cache, request);'))


if __name__ == "__main__":
    unittest.main(verbosity=2)
