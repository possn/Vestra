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

    def test_blocked_market_build_cleans_every_generated_payload_before_publish(self):
        source = MARKET_WORKFLOW.read_text()
        blocked = source.split("- name: Persist blocked-build diagnostics", 1)[1]
        blocked = blocked.split("- name: Fail build after diagnostics are persisted", 1)[0]
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
        self.assertLess(blocked.index("git checkout --"), blocked.index("git add data/coverage_audit.json"))
        self.assertLess(blocked.index("git clean -fd"), blocked.index("git add data/coverage_audit.json"))
        self.assertNotIn("git add data/", blocked)

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
