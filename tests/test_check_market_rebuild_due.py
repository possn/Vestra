import sys
import unittest
from datetime import date
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from check_market_rebuild_due import due

class CanonicalRecoveryTests(unittest.TestCase):
    def test_fresh_published_snapshot_does_not_rebuild(self):
        self.assertFalse(due({"generated_at": "2026-10-16T06:33:00Z"}, date(2026, 10, 16)))
    def test_missing_or_prior_day_publication_requests_rebuild(self):
        self.assertTrue(due({"generated_at": "2026-10-15T23:58:00Z"}, date(2026, 10, 16)))
        self.assertTrue(due({"generated_at": "invalid"}, date(2026, 10, 16)))
        self.assertTrue(due({}, date(2026, 10, 16)))
    def test_future_dated_market_snapshot_cannot_suppress_recovery(self):
        self.assertTrue(due(
            {"generated_at": "2026-10-17T03:00:00Z"},
            date(2026, 10, 16)))
        self.assertTrue(due(
            {"generated_at": "2026-10-18T00:01:00+00:00"},
            date(2026, 10, 16)))

    def test_recovery_has_independent_macro_schedule_fallback(self):
        workflow = (Path(__file__).resolve().parents[1] /
                    ".github/workflows/recover-market-data.yml").read_text()
        self.assertIn('workflows: ["Update macro events"]', workflow)
        self.assertIn("github.event.workflow_run.event == 'schedule'", workflow)
        self.assertIn("UPSTREAM_SCHEDULED_AT:", workflow)
        self.assertIn("10<=stamp.astimezone(datetime.timezone.utc).hour<=14", workflow)
        self.assertIn("steps.independent_window.outputs.ready == 'true'", workflow)
        self.assertIn("python scripts/check_market_rebuild_due.py", workflow)
        self.assertIn("gh workflow run update-market-data.yml --ref main", workflow)

    def test_timestamp_needs_timezone(self):
        self.assertTrue(due({"generated_at": "2026-10-16T06:33:00"}, date(2026, 10, 16)))
if __name__ == "__main__":
    unittest.main()
