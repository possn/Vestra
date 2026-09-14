from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "market-data-health.js"
BOOT = ROOT / "market-company-brief.js"


class MarketDataHealthFetchTimeoutTests(unittest.TestCase):
    def setUp(self):
        self.runtime = RUNTIME.read_text(encoding="utf-8")
        self.boot = BOOT.read_text(encoding="utf-8")

    def test_static_health_fetches_have_a_bounded_deadline(self):
        self.assertIn("const DATA_FETCH_TIMEOUT_MS = 5000;", self.runtime)
        self.assertIn("Promise.race([request, timeout])", self.runtime)
        self.assertIn("controller?.abort()", self.runtime)
        self.assertIn("clearTimeout(timeoutId)", self.runtime)

    def test_timeout_path_degrades_to_null_without_blocking_refresh(self):
        self.assertIn("resolve(null);", self.runtime)
        self.assertIn("loadJson(DATA_URLS.guard)", self.runtime)
        self.assertIn("loadJson(DATA_URLS.learned)", self.runtime)
        self.assertIn("const [guard, learned, quote] = await Promise.all([", self.runtime)

    def test_loader_and_runtime_versions_match(self):
        self.assertIn("version: '1.3'", self.runtime)
        self.assertIn("market-data-health.js?v=1.3", self.boot)


if __name__ == "__main__":
    unittest.main(verbosity=2)
