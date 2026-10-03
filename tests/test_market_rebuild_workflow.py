from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "update-market-data.yml"


class MarketRebuildWorkflowTests(unittest.TestCase):
    def test_market_publishers_are_serialized_and_canonical_runs_supersede_obsolete_work(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        startup = (ROOT / ".github" / "workflows" / "rebuild-market-startup.yml").read_text(encoding="utf-8")
        self.assertIn("group: market-data-publish", source)
        self.assertIn("group: market-data-publish", startup)
        self.assertIn("cancel-in-progress: true", source)
        self.assertIn("cancel-in-progress: false", startup)

    def test_canonical_rebuild_is_bounded(self):
        source = WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("timeout-minutes: 45", source)
        expected = {
            'FINSCANNER_FUNDAMENTALS_PORTFOLIO_REFRESH: "140"',
            'FINSCANNER_FUNDAMENTALS_NONPRIORITY_REFRESH: "180"',
            'FINSCANNER_ESEF_NONPRIORITY_REFRESH: "60"',
            'FINSCANNER_GAP_REFRESH: "80"',
            'FINSCANNER_QUARTERLY_GAP_REFRESH: "80"',
            'FINSCANNER_ANALYST_PRIORITY_REFRESH: "100"',
            'FINSCANNER_ANALYST_NONPRIORITY_REFRESH: "80"',
            'FINSCANNER_CAPITAL_RISK_PRIORITY_REFRESH: "80"',
            'FINSCANNER_CAPITAL_RISK_NONPRIORITY_REFRESH: "30"',
        }
        for item in expected:
            self.assertIn(item, source)

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
