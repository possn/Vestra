import re
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUBLISHER = ROOT / "scripts" / "publish_with_retry.sh"
MARKET_WORKFLOW = ROOT / ".github" / "workflows" / "update-market-data.yml"
WRITER_WORKFLOWS = [
    MARKET_WORKFLOW,
    ROOT / ".github" / "workflows" / "update-executives.yml",
    ROOT / ".github" / "workflows" / "update-politicians.yml",
    ROOT / ".github" / "workflows" / "update-metals-news.yml",
]


class DataPublishingContractTests(unittest.TestCase):
    def test_shared_publisher_has_valid_shell_syntax(self):
        self.assertTrue(PUBLISHER.exists(), "shared publisher is missing")
        subprocess.run(["bash", "-n", str(PUBLISHER)], check=True)

    def test_all_data_writers_use_resilient_publisher(self):
        for workflow in WRITER_WORKFLOWS:
            with self.subTest(workflow=workflow.name):
                source = workflow.read_text()
                self.assertIn(
                    "bash scripts/publish_with_retry.sh origin main",
                    source,
                    f"{workflow.name} bypasses the shared resilient publisher",
                )
                self.assertNotIn(
                    "git pull --rebase origin main",
                    source,
                    f"{workflow.name} restored the single-shot publication race",
                )

    def test_blocked_market_build_cleans_tracked_and_untracked_payloads_before_publish(self):
        source = MARKET_WORKFLOW.read_text()
        blocked = source.split("- name: Persist blocked-build diagnostics", 1)[1]
        blocked = blocked.split("- name: Fail build after diagnostics are persisted", 1)[0]

        # Core generated payloads are known tracked files and must be restored
        # before any diagnostics are staged.
        core_checkout = "git checkout -- data/stocks.json data/stocks-index.json data/dossiers-manifest.json data/dossiers"
        self.assertIn(core_checkout, blocked)

        # During the compact-payload rollout these two paths may be tracked on a
        # later run or still untracked on the first run. The workflow must handle
        # both states independently instead of letting one bad pathspec skip all cleanup.
        self.assertIn("for path in data/stocks-startup.json data/stocks-scanner.json; do", blocked)
        self.assertIn('git ls-files --error-unmatch "$path"', blocked)
        self.assertIn('git checkout -- "$path"', blocked)
        self.assertIn('rm -f -- "$path"', blocked)

        for path in (
            "data/stocks.json",
            "data/stocks-index.json",
            "data/stocks-startup.json",
            "data/stocks-scanner.json",
            "data/dossiers-manifest.json",
            "data/dossiers",
        ):
            with self.subTest(path=path):
                self.assertIn(path, blocked)

        selective_stage = "git add data/coverage_audit.json"
        self.assertIn(selective_stage, blocked)
        self.assertLess(blocked.index(core_checkout), blocked.index(selective_stage))
        self.assertLess(blocked.index("git clean -fd data/dossiers"), blocked.index(selective_stage))

        # Fail closed if any rejected payload remains modified/untracked. This
        # guard must run before the selective diagnostic staging/publish path.
        dirty_guard = "git status --porcelain -- data/stocks.json data/stocks-index.json data/stocks-startup.json data/stocks-scanner.json data/dossiers-manifest.json data/dossiers"
        self.assertIn(dirty_guard, blocked)
        self.assertIn("refusing diagnostic publication", blocked)
        self.assertLess(blocked.index(dirty_guard), blocked.index(selective_stage))

        self.assertIsNone(
            re.search(r"(?m)^\s*git add data/\s*$", blocked),
            "blocked build must never stage the whole rejected data directory",
        )

    def test_publisher_retries_remote_advance_without_force_push(self):
        source = PUBLISHER.read_text()
        self.assertIn('git fetch "$remote" "$branch"', source)
        self.assertIn('git rebase "$remote/$branch"', source)
        self.assertIn('git push "$remote" "HEAD:${branch}"', source)
        self.assertIn("for ((attempt=1; attempt<=attempts; attempt++))", source)
        self.assertNotIn("--force", source)
        self.assertNotIn("--force-with-lease", source)


if __name__ == "__main__":
    unittest.main()
