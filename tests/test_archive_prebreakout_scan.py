import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
module=Path(__file__).resolve().parents[1]/"scripts/archive_prebreakout_scan.py"
spec=importlib.util.spec_from_file_location("archive_prebreakout",module)
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)

class ArchiveTests(unittest.TestCase):
 def payload(self):
  return {"schema":"vestra_prebreakout_v1","generated_at":"2026-10-14T13:39:26+00:00","signals":[]}
 def test_first_snapshot_is_immutable(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder); first=self.payload();p=mod.archive(first,root)
   second=self.payload();second["signals"]=[{"ticker":"TEST"}]
   self.assertEqual(mod.archive(second,root),p)
   self.assertEqual(json.loads(p.read_text())["signals"],[])
 def test_invalid_scan_cannot_be_published(self):
  with tempfile.TemporaryDirectory() as folder:
   with self.assertRaises(ValueError):mod.archive({"generated_at":"2026-10-14T13:39:26Z","signals":[]},Path(folder))
 def test_date_uses_utc(self):
  with tempfile.TemporaryDirectory() as folder:
   p=self.payload();p["generated_at"]="2026-10-15T00:30:00+02:00"
   self.assertEqual(mod.archive(p,Path(folder)).name,"2026-10-14.json")
 def test_naive_timestamp_rejected(self):
  with tempfile.TemporaryDirectory() as folder:
   p=self.payload();p["generated_at"]="2026-10-14T13:39:26"
   with self.assertRaises(ValueError):mod.archive(p,Path(folder))
 def test_slots_are_distinct_and_immutable(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder)
   first=self.payload();first["generated_at"]="2026-10-14T02:10:00Z";first["scan_slot_utc"]=0
   later=self.payload();later["generated_at"]="2026-10-14T08:10:00Z";later["scan_slot_utc"]=1
   p0=mod.archive_slot(first,root)
   p1=mod.archive_slot(later,root)
   self.assertNotEqual(p0,p1)
   self.assertEqual(json.loads(p0.read_text())["scan_slot_utc"],0)
   self.assertEqual(json.loads(p1.read_text())["scan_slot_utc"],1)
   rerun=dict(first);rerun["signals"]=[{"ticker":"FAKE"}]
   self.assertEqual(mod.archive_slot(rerun,root),p0)
   self.assertEqual(json.loads(p0.read_text())["signals"],[])
 def test_slot_timestamp_must_match_publication_window(self):
  with tempfile.TemporaryDirectory() as folder:
   payload=self.payload();payload["scan_slot_utc"]=0
   with self.assertRaises(ValueError):mod.archive_slot(payload,Path(folder))
   payload["scan_slot_utc"]=2
   self.assertEqual(mod.archive_slot(payload,Path(folder)).name,"2026-10-14-slot2.json")
   payload["generated_at"]="2026-10-14T13:39:26"
   with self.assertRaises(ValueError):mod.archive_slot(payload,Path(folder))
if __name__=="__main__":unittest.main()
