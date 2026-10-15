import json
import sys
import tempfile
import unittest
from datetime import datetime,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from audit_prebreakout_scan_cadence import audit

class CadenceAuditTests(unittest.TestCase):
    def test_grace_and_missing_slot_are_distinct(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"2026"/"slots"
            path.mkdir(parents=True)
            feed={"schema":"vestra_prebreakout_v1","generated_at":"2026-10-15T14:59:00Z","scan_slot_utc":2,"signals":[]}
            (path/"2026-10-15-slot2.json").write_text(json.dumps(feed))
            early=audit(Path(tmp),datetime(2026,10,15,21,0,tzinfo=timezone.utc),90,1)
            self.assertNotIn("2026-10-15-slot3",early["missing_or_invalid"])
            late=audit(Path(tmp),datetime(2026,10,15,22,0,tzinfo=timezone.utc),90,1)
            self.assertIn("2026-10-15-slot2",late["present"])
            self.assertIn("2026-10-15-slot3",late["missing_or_invalid"])
            self.assertEqual(late["status"],"attention")
    def test_weekends_do_not_require_scans(self):
        with tempfile.TemporaryDirectory() as tmp:
            result=audit(Path(tmp),datetime(2026,10,17,23,0,tzinfo=timezone.utc),90,1)
            self.assertEqual(result["status"],"ok")
            self.assertEqual(result["missing_or_invalid"],[])
    def test_invalid_archive_not_counted_as_published(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"2026"/"slots";path.mkdir(parents=True)
            (path/"2026-10-15-slot2.json").write_text('{"schema":"invalid"}')
            result=audit(Path(tmp),datetime(2026,10,15,22,0,tzinfo=timezone.utc),90,1)
            self.assertIn("2026-10-15-slot2",result["missing_or_invalid"])

if __name__=="__main__":
    unittest.main()
