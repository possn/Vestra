import importlib.util,json,tempfile,unittest
from datetime import datetime,timezone
from pathlib import Path
p=Path(__file__).resolve().parents[1]/"scripts/check_prebreakout_publication.py"
spec=importlib.util.spec_from_file_location("publication",p)
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
class Contract(unittest.TestCase):
 def setup_files(self,root):
  d=root/"data";d.mkdir()
  ts="2026-10-15T14:15:00+00:00"
  signal={"ticker":"TEST","date":"2026-10-14","stage":"compressão"}
  feed={"schema":"vestra_prebreakout_v1","generated_at":ts,"scan_slot_utc":2,"signals":[signal]}
  index={"schema":"vestra_prebreakout_observations_v1","historical_only":True,"slots_considered":1,
         "observations":[{"ticker":"TEST","observed_at":ts,"signal_date":signal["date"],
                          "stage":signal["stage"],"current":False}]}
  slot=d/"prebreakout-history"/"2026"/"slots";slot.mkdir(parents=True)
  (slot/"2026-10-15-slot2.json").write_text(json.dumps(feed))
  (d/"prebreakout-signals.json").write_text(json.dumps(feed))
  (d/"prebreakout-observations.json").write_text(json.dumps(index))
  return d
 def test_valid_publication(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);self.setup_files(root)
   self.assertEqual(mod.verify(root)["verified_slot"],2)
 def test_rejected_when_slot_missing_or_different(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);d=self.setup_files(root)
   (d/"prebreakout-history"/"2026"/"slots"/"2026-10-15-slot2.json").unlink()
   with self.assertRaises(FileNotFoundError):mod.verify(root)
 def test_rejected_when_history_promoted_or_dated_incorrectly(self):
  with tempfile.TemporaryDirectory() as folder:
   root=Path(folder);d=self.setup_files(root)
   file=d/"prebreakout-observations.json"
   data=json.loads(file.read_text());data["observations"][0]["current"]=True
   file.write_text(json.dumps(data))
   with self.assertRaises(ValueError):mod.verify(root)
if __name__=="__main__":unittest.main()
