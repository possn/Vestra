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
if __name__=="__main__":unittest.main()
