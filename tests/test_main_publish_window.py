from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
GUARD = ROOT / "scripts" / "defer_main_publish_if_code_pr.py"

WRITERS = {
    "rebuild-market-startup.yml",
    "refresh-weekly-earnings.yml",
    "sec-fund-identity.yml",
    "update-aaii-sentiment.yml",
    "update-dashboard-feeds.yml",
    "update-executives.yml",
    "update-macro-events.yml",
    "update-market-data.yml",
    "update-metals-news.yml",
    "update-politicians.yml",
}


class MainPublishWindowTests(unittest.TestCase):
    def test_guard_treats_data_and_trigger_only_changes_as_safe(self):
        source = GUARD.read_text(encoding="utf-8")
        self.assertIn('SAFE_PREFIXES = ("data/",)', source)
        self.assertIn('".github/triggers/market-data-rebuild.txt"', source)
        self.assertIn('".github/triggers/market-startup-rebuild.txt"', source)
        self.assertIn("any(path and not _is_safe_path(path) for path in changed)", source)
        self.assertIn('compare/main...{head_sha}', source)
        self.assertIn('if int(compare.get("behind_by") or 0) > 0:', source)

    def test_every_main_writer_uses_same_publish_window_guard(self):
        for name in WRITERS:
            source = (WORKFLOWS / name).read_text(encoding="utf-8")
            with self.subTest(workflow=name):
                self.assertIn("pull-requests: read", source)
                self.assertIn("id: publish_window", source)
                self.assertIn("python scripts/defer_main_publish_if_code_pr.py", source)
                self.assertIn("steps.publish_window.outputs.defer != 'true'", source)

    def test_no_unprotected_main_writer_remains(self):
        discovered = set()
        for path in WORKFLOWS.glob("*.yml"):
            source = path.read_text(encoding="utf-8")
            if "publish_with_retry.sh" in source or "git push" in source or "git commit -m" in source:
                discovered.add(path.name)
        self.assertEqual(discovered, WRITERS)


if __name__ == "__main__":
    unittest.main(verbosity=2)
