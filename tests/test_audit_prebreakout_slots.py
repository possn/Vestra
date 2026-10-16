import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from audit_prebreakout_slots import missing_closed_slots

class MissedSlotAuditTests(unittest.TestCase):
    def test_never_marks_open_or_future_slots_missing(self):
        with tempfile.TemporaryDirectory() as td:
            now = datetime(2026, 10, 16, 4, 0, tzinfo=timezone.utc)
            found = missing_closed_slots(now, Path(td), 0)
            self.assertEqual(found, [])

    def test_detects_closed_missing_slot_and_respects_archive(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            now = datetime(2026, 10, 16, 6, 0, tzinfo=timezone.utc)
            self.assertEqual([(x["date"], x["slot"]) for x in missing_closed_slots(now, root, 0)],
                             [("2026-10-16", 0)])
            slot = root / "2026" / "slots" / "2026-10-16-slot0.json"
            slot.parent.mkdir(parents=True)
            slot.write_text("{}")
            self.assertEqual(missing_closed_slots(now, root, 0), [])

    def test_weekend_skipped_and_timezone_required(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.assertEqual(missing_closed_slots(datetime(2026, 10, 18, 23, 0, tzinfo=timezone.utc), root, 0), [])
            with self.assertRaises(ValueError):
                missing_closed_slots(datetime(2026, 10, 16, 6, 0), root)
if __name__ == "__main__":
    unittest.main()
