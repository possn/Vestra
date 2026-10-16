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
    def test_timestamp_needs_timezone(self):
        self.assertTrue(due({"generated_at": "2026-10-16T06:33:00"}, date(2026, 10, 16)))
if __name__ == "__main__":
    unittest.main()
