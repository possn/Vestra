from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "update-market-data.yml"


class MarketRebuildWorkflowTests(unittest.TestCase):
    def test_market_publishers_are_serialized(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("group: market-data-publish", source)
        self.assertIn("cancel-in-progress: false", source)

    def test_production_preflight_compiles_current_runtime_layers(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        required = (
            "scripts/run_market_pipeline.py",
            "scripts/yahoo_rate_limit.py",
            "scripts/yahoo_retry_hygiene.py",
            "scripts/sec_archives_enrich.py",
            "scripts/sec_archives_runtime.py",
            "scripts/sec_worker_fallback.py",
            "scripts/insider_prices.py",
        )
        for path in required:
            self.assertIn(path, source, path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
