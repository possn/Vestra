"""Regression contract for independent small-cap publication recovery."""
from pathlib import Path
import unittest


class SmallcapRecoveryFallbackTests(unittest.TestCase):
    def test_recovery_has_independent_schedule_and_age_guard(self):
        workflow = (Path(__file__).resolve().parents[1] / ".github/workflows/recover-smallcap-publication.yml").read_text()
        self.assertIn("cron: '10 3,9,15,21 * * *'", workflow)
        self.assertIn("scripts/check_smallcap_publication.py --max-age-hours 8", workflow)
        self.assertIn("steps.freshness.outputs.stale == 'true'", workflow)
        self.assertIn("github.event.workflow_run.conclusion == 'failure'", workflow)

    def test_recovery_remains_bounded_and_deduplicated(self):
        workflow = (Path(__file__).resolve().parents[1] / ".github/workflows/recover-smallcap-publication.yml").read_text()
        self.assertIn('status=="queued"', workflow)
        self.assertIn('status=="in_progress"', workflow)
        self.assertIn('if [ "$active" -gt 0 ]; then', workflow)
        self.assertIn("budget=30", workflow)
        self.assertIn("cancel-in-progress: false", workflow)


if __name__ == "__main__":
    unittest.main()
