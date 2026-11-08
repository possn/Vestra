"""Forward publisher checks previous genuine evaluation, not newly generated output."""
import datetime
import unittest
from pathlib import Path

from scripts.defer_main_publish_if_code_pr import forward_publication_overdue

ROOT = Path(__file__).resolve().parents[1]
UTC = datetime.timezone.utc


class ForwardPublishFreshnessTests(unittest.TestCase):
    def old_report(self, date):
        return {
            "schema": "vestra_prebreakout_forward_cohorts_v1",
            "price_metadata": {"completed_before_utc_date": date},
        }

    def test_report_fresh_enough_to_respect_open_code_pr(self):
        self.assertFalse(forward_publication_overdue(
            self.old_report("2026-11-07"),
            datetime.datetime(2026, 11, 8, 11, tzinfo=UTC), 48))

    def test_overdue_real_report_unblocks_validated_forward_publication(self):
        self.assertTrue(forward_publication_overdue(
            self.old_report("2026-11-07"),
            datetime.datetime(2026, 11, 9, 1, tzinfo=UTC), 48))

    def test_missing_invalid_future_provenance_does_not_suppress_publication(self):
        now = datetime.datetime(2026, 11, 8, 11, tzinfo=UTC)
        for report in ({}, {"schema": "wrong"},
                       self.old_report("not-a-date"),
                       self.old_report("2026-11-10")):
            with self.subTest(report=report):
                self.assertTrue(forward_publication_overdue(report, now, 48))

    def test_invalid_parameters(self):
        with self.assertRaises(ValueError):
            forward_publication_overdue({}, datetime.datetime(2026, 11, 8), 48)
        with self.assertRaises(ValueError):
            forward_publication_overdue({}, datetime.datetime(2026, 11, 8, tzinfo=UTC), 0)

    def test_workflow_snapshots_previous_file_before_evaluation_and_guards_publication(self):
        workflow = (ROOT / ".github/workflows/refresh-prebreakout-forward-evidence.yml").read_text()
        self.assertLess(workflow.index("git show HEAD:data/prebreakout-forward-evidence.json"),
                        workflow.index("python scripts/refresh_prebreakout_forward_evidence.py"))
        self.assertIn("VESTRA_FORWARD_PREVIOUS: /tmp/vestra-prebreakout-forward-previous.json", workflow)
        self.assertIn("--forward-max-staleness-hours 48", workflow)
        self.assertIn("steps.publish_window.outputs.defer != 'true'", workflow)


if __name__ == "__main__":
    unittest.main()
