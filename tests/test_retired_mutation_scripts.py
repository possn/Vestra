from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class RetiredMutationScriptsTests(unittest.TestCase):
    RETIRED = (
        "scripts/activate_canonical_opportunities.py",
        "scripts/activate_portfolio_hierarchy.py",
        "scripts/add_dividend_reconciliation_ui.py",
        "scripts/add_worker_health.py",
        "scripts/apply_quote_engine_v2_hotfix.py",
        "scripts/cleanup_market_index_consumers.py",
        "scripts/cleanup_v452_opportunities.py",
    )

    def test_one_shot_mutation_scripts_stay_retired(self):
        for relative in self.RETIRED:
            self.assertFalse((ROOT / relative).exists(), relative)

    def test_temporary_patch_workflows_are_not_part_of_main(self):
        workflows = ROOT / ".github" / "workflows"
        offenders = [p.name for p in workflows.glob("*.yml") if p.name.startswith(("tmp-", "_apply-", "patch-"))]
        self.assertEqual(offenders, [])

    def test_canonical_replacements_remain_present(self):
        for relative in (
            "market-opportunities.js",
            "vestra-portfolio-hierarchy.js",
            "app-market-client.js",
            "app-broker-normalization.js",
            "worker.js",
        ):
            self.assertTrue((ROOT / relative).exists(), relative)

    def test_retired_compatibility_targets_remain_absent(self):
        for relative in (
            "market-hotfix.js",
            "market-enhancements.js",
            "vestra-ux-v452.js",
        ):
            self.assertFalse((ROOT / relative).exists(), relative)


if __name__ == "__main__":
    unittest.main(verbosity=2)
