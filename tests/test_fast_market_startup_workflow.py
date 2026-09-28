from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "rebuild-market-startup.yml"


class FastMarketStartupWorkflowTests(unittest.TestCase):
    def test_fast_path_does_not_run_heavy_enrichment(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("python build_market_shards.py", source)
        self.assertIn("timeout-minutes: 15", source)
        for forbidden in (
            "run_market_pipeline.py",
            "sec_endpoint_probe.py",
            "normalize_market_provenance.py",
            "postprocess_market.py",
            "score_audit.py",
        ):
            self.assertNotIn(forbidden, source)
        self.assertNotIn("python coverage_audit.py", source)

    def test_fast_path_validates_budget_before_publication(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("tests/test_market_index_budget.py", source)
        self.assertIn("tests/test_weekly_rotation_relative_destinations.py", source)
        self.assertLess(
            source.index("Validate generated payload budgets and rotation contracts"),
            source.index("Publish startup payloads"),
        )

    def test_fast_path_rebuilds_when_builder_or_rotation_contracts_change(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        for path in (
            "scripts/build_market_shards.py",
            "tests/test_market_index_budget.py",
            "tests/test_weekly_rotation_relative_destinations.py",
        ):
            self.assertIn(path, source)

    def test_fast_path_publishes_only_generated_startup_artifacts(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        self.assertNotIn("git add data/", source)
        publish = source.split("Publish startup payloads", 1)[1]
        self.assertNotIn("data/stocks.json", publish)
        for path in (
            "data/stocks-index.json",
            "data/stocks-startup.json",
            "data/portfolio-sectors.json",
            "data/dossiers-manifest.json",
            "data/dossiers/",
        ):
            self.assertIn(path, source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
