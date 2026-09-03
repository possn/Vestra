import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "publish_with_retry.sh"
MARKET_PREFIX = "Actualização automática de dados de mercado ("


def git(cwd, *args, check=True):
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )


class PublishWithRetryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="vestra-publish-test-"))
        self.remote = self.tmp / "remote.git"
        self.seed = self.tmp / "seed"
        git(self.tmp, "init", "--bare", str(self.remote))
        git(self.tmp, "clone", str(self.remote), str(self.seed))
        git(self.seed, "config", "user.name", "Test Bot")
        git(self.seed, "config", "user.email", "test@example.com")
        (self.seed / "base.txt").write_text("base\n", encoding="utf-8")
        git(self.seed, "add", "base.txt")
        git(self.seed, "commit", "-m", "base")
        git(self.seed, "branch", "-M", "main")
        git(self.seed, "push", "-u", "origin", "main")
        git(self.remote, "symbolic-ref", "HEAD", "refs/heads/main")
        self.base = git(self.seed, "rev-parse", "HEAD").stdout.strip()

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def clone(self, name):
        path = self.tmp / name
        git(self.tmp, "clone", str(self.remote), str(path))
        git(path, "config", "user.name", "Test Bot")
        git(path, "config", "user.email", "test@example.com")
        return path

    def commit_file(self, repo, filename, content, message):
        (repo / filename).write_text(content, encoding="utf-8")
        git(repo, "add", filename)
        git(repo, "commit", "-m", message)
        return git(repo, "rev-parse", "HEAD").stdout.strip()

    def run_publisher(self, repo):
        env = os.environ.copy()
        env["PUBLISH_PUSH_ATTEMPTS"] = "1"
        env["PUBLISH_PUSH_DELAY_SECONDS"] = "0"
        return subprocess.run(
            ["bash", str(SCRIPT), "origin", "main"],
            cwd=repo,
            env=env,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

    def test_independent_remote_feed_still_rebases_and_publishes(self):
        local = self.clone("local-independent")
        remote_writer = self.clone("remote-independent")

        self.commit_file(
            local,
            "market.json",
            "local snapshot\n",
            "Actualização automática de dados de mercado (2026-09-03 12:00 UTC)",
        )
        independent_sha = self.commit_file(
            remote_writer,
            "executives.json",
            "independent feed\n",
            "Actualização disclosures Executivo (2026-09-03 12:01 UTC)",
        )
        git(remote_writer, "push", "origin", "main")

        result = self.run_publisher(local)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("Published successfully", result.stdout)
        self.assertNotIn("Publication superseded", result.stdout)

        verify = self.clone("verify-independent")
        self.assertEqual((verify / "market.json").read_text(), "local snapshot\n")
        self.assertEqual((verify / "executives.json").read_text(), "independent feed\n")
        self.assertTrue(git(verify, "merge-base", "--is-ancestor", independent_sha, "HEAD", check=False).returncode == 0)

    def test_newer_remote_market_snapshot_supersedes_local_snapshot(self):
        local = self.clone("local-superseded")
        remote_writer = self.clone("remote-superseded")

        local_sha = self.commit_file(
            local,
            "market.json",
            "queued snapshot\n",
            "Actualização automática de dados de mercado (2026-09-03 12:00 UTC)",
        )
        remote_market_sha = self.commit_file(
            remote_writer,
            "market.json",
            "already published snapshot\n",
            "Actualização automática de dados de mercado (2026-09-03 12:01 UTC)",
        )
        git(remote_writer, "push", "origin", "main")

        result = self.run_publisher(local)
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertIn("Publication superseded", result.stdout)
        self.assertIn("refusing snapshot-on-snapshot rebase", result.stdout)

        verify = self.clone("verify-superseded")
        remote_head = git(verify, "rev-parse", "HEAD").stdout.strip()
        self.assertEqual(remote_head, remote_market_sha)
        self.assertNotEqual(remote_head, local_sha)
        self.assertEqual((verify / "market.json").read_text(), "already published snapshot\n")

    def test_non_market_commit_keeps_conflict_fail_closed_behavior(self):
        local = self.clone("local-nonmarket")
        remote_writer = self.clone("remote-nonmarket")

        self.commit_file(local, "shared.json", "local\n", "diagnostics: local market guard")
        self.commit_file(remote_writer, "shared.json", "remote\n", "other writer")
        git(remote_writer, "push", "origin", "main")

        result = self.run_publisher(local)
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertIn("Rebase conflict while publishing", result.stdout)
        self.assertNotIn("Publication superseded", result.stdout)


if __name__ == "__main__":
    unittest.main()
