"""Production WebKit smoke must run on a supported, reproducible image."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = (ROOT / ".github/workflows/production-smoke.yml").read_text(encoding="utf-8")


class ProductionSmokeRunnerTests(unittest.TestCase):
    def test_webkit_runner_uses_pinned_supported_container(self):
        self.assertIn("mcr.microsoft.com/playwright:v1.55.0-noble", WORKFLOW)
        self.assertIn("shell: bash", WORKFLOW)
        self.assertIn("test -d /ms-playwright", WORKFLOW)
        self.assertNotIn("playwright install --with-deps webkit", WORKFLOW)

    def test_published_website_and_score_contract_still_checked(self):
        self.assertIn("Wait for published Vestra", WORKFLOW)
        self.assertIn("Validate published score report contract", WORKFLOW)
        self.assertIn("npm run test:e2e:production", WORKFLOW)


if __name__ == "__main__":
    unittest.main()
