from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / '.github' / 'workflows'

ACTIVE_WORKFLOWS = {
    'bootstrap-earnings-archive.yml',
    'architecture-invariants.yml',
    'browser-e2e.yml',
    'capital-risk-regression.yml',
    'crypto-production-smoke.yml',
    'production-smoke.yml',
    'publish-vestra-mobile-icons.yml',
    'rebuild-market-startup.yml',
    'recover-market-data.yml',
    'recover-prebreakout-independent.yml',
    'refresh-weekly-earnings.yml',
    'refresh-prebreakout-scanner.yml',
    'smallcap-prebreakout-research.yml',
    'refresh-prebreakout-forward-evidence.yml',
    'refresh-cnn-fear-greed.yml',
    'runtime-js-syntax.yml',
    'sec-connectivity-probe.yml',
    'sec-fund-identity.yml',
    'sec-runtime-regression.yml',
    'update-aaii-sentiment.yml',
    'update-executives.yml',
    'update-dashboard-feeds.yml',
    'update-macro-events.yml',
    'update-market-data.yml',
    'update-metals-news.yml',
    'update-politicians.yml',
    'verify-cloudflare-worker.yml',
}


class WorkflowInventoryTests(unittest.TestCase):
    def test_only_canonical_workflows_remain(self):
        actual = {p.name for p in WORKFLOWS.glob('*.yml')}
        self.assertEqual(
            actual,
            ACTIVE_WORKFLOWS,
            'Workflow inventory changed. New workflows must be explicitly classified as canonical; '
            'completed patch/refactor workflows must not remain executable in main.',
        )

    def test_no_canonical_workflow_is_named_as_one_off_patch(self):
        forbidden = ('apply-', 'fix-', 'refactor-', 'remove-', 'repair-', 'restore-', 'patch-')
        for name in ACTIVE_WORKFLOWS:
            self.assertFalse(name.startswith(forbidden), name)


if __name__ == '__main__':
    unittest.main(verbosity=2)
