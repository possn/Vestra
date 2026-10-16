import datetime
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from defer_main_publish_if_code_pr import scan_grace_expired

UTC = datetime.timezone.utc

class ScannerPublishGraceTests(unittest.TestCase):
    def at(self, hour, minute, day=16):
        return datetime.datetime(2026, 10, day, hour, minute, tzinfo=UTC)

    def test_original_scheduled_run_is_guarded(self):
        for hour in (2, 8, 14, 20):
            self.assertFalse(scan_grace_expired(self.at(hour, 10), 85))
            self.assertFalse(scan_grace_expired(self.at(hour + 1, 34), 85))

    def test_fresh_retry_after_grace_can_publish(self):
        for hour in (2, 8, 14, 20):
            self.assertTrue(scan_grace_expired(self.at(hour + 1, 35), 85))

    def test_never_exempts_before_a_due_slot_or_on_weekend(self):
        self.assertFalse(scan_grace_expired(self.at(1, 59), 85))
        self.assertFalse(scan_grace_expired(self.at(7, 59), 85))
        self.assertFalse(scan_grace_expired(self.at(3, 35, day=17), 85))
        with self.assertRaises(ValueError):
            scan_grace_expired(datetime.datetime(2026, 10, 16, 3, 35), 85)

if __name__ == "__main__":
    unittest.main()
