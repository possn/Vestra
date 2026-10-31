from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
WORKFLOW=(ROOT/'.github/workflows/vestra-guarded-pr-integration.yml').read_text()

class GuardedIntegrationTests(unittest.TestCase):
    def test_explicit_opt_in_and_same_sha_four_gates(self):
        for term in ("vestra-auto-merge", "head_sha:head", "webkit-iphone (1)", "webkit-iphone (2)", "architecture-invariants.yml", "runtime-js-syntax.yml", "browser-e2e.yml"):
            self.assertIn(term,WORKFLOW)
    def test_merge_protection(self):
        for term in ("fresh.head.sha!==head","fresh.base.sha!==currentMain",
                     "latestCompare.behind_by!==0","fresh.mergeable!==true",
                     "sha:head","merge_method:'squash'","break;"):
            self.assertIn(term,WORKFLOW)
    def test_workflow_run_uses_trusted_main_without_untrusted_checkout(self):
        self.assertIn("workflow_run:",WORKFLOW)
        self.assertNotIn("actions/checkout",WORKFLOW)
        self.assertIn("requestedLabel",WORKFLOW)
        self.assertIn("secrets.VESTRA_INTEGRATION_TOKEN",WORKFLOW)
        self.assertNotIn("secrets.GITHUB_TOKEN",WORKFLOW)

if __name__=="__main__": unittest.main()
