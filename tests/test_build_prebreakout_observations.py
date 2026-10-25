import importlib.util
import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

SCRIPT=Path(__file__).resolve().parents[1]/"scripts/build_prebreakout_observations.py"
spec=importlib.util.spec_from_file_location("prebreakout_observations",SCRIPT)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class HistoricalObservationTests(unittest.TestCase):
 def test_slots_are_history_not_live_signals(self):
  with tempfile.TemporaryDirectory() as temp:
   root=Path(temp)
   folder=root/"2026"/"slots";folder.mkdir(parents=True)
   def write(slot,ticker,score):
    timestamp=f"2026-10-15T{slot*6+1:02d}:10:00Z"
    data={"schema":"vestra_prebreakout_v1","generated_at":timestamp,
          "scan_slot_utc":slot,"signals":[{"ticker":ticker,"score":score,"date":"2026-10-14",
            "stage":"compressão","source":"yahoo:daily_ohlcv"}]}
    (folder/f"2026-10-15-slot{slot}.json").write_text(json.dumps(data))
   write(0,"AAA",55);write(1,"AAA",61);write(2,"BBB",70)
   result=mod.build(root,datetime(2026,10,15,15,tzinfo=timezone.utc))
   self.assertTrue(result["historical_only"])
   self.assertEqual(result["slots_considered"],3)
   self.assertEqual(len(result["observations"]),2)
   self.assertTrue(all(x["current"] is False for x in result["observations"]))
   aaa=next(x for x in result["observations"] if x["ticker"]=="AAA")
   self.assertEqual(aaa["score"],61)
   self.assertEqual(aaa["scan_slot_utc"],1)
 def test_future_or_mismatched_snapshot_ignored(self):
  with tempfile.TemporaryDirectory() as temp:
   folder=Path(temp)/"2026"/"slots";folder.mkdir(parents=True)
   payload={"schema":"vestra_prebreakout_v1","generated_at":"2026-10-15T13:10:00Z",
            "scan_slot_utc":1,"signals":[{"ticker":"FAKE","score":90,"stage":"confirmado",
                                         "source":"yahoo:daily_ohlcv"}]}
   (folder/"2026-10-15-slot1.json").write_text(json.dumps(payload))
   result=mod.build(Path(temp),datetime(2026,10,15,14,tzinfo=timezone.utc))
   self.assertEqual(result["observations"],[])
 def test_carried_rows_do_not_renew_historical_observation(self):
  with tempfile.TemporaryDirectory() as temp:
   folder=Path(temp)/"2026"/"slots";folder.mkdir(parents=True)
   row={"ticker":"AAA","score":70,"date":"2026-10-15","stage":"pré-breakout",
        "source":"yahoo:daily_ohlcv","scanner_verified_at":"2026-10-15T08:10:00+00:00"}
   for slot,ts in [(1,"2026-10-15T08:10:00+00:00"),(2,"2026-10-15T14:10:00+00:00")]:
    (folder/f"2026-10-15-slot{slot}.json").write_text(json.dumps({"schema":"vestra_prebreakout_v1",
      "generated_at":ts,"scan_slot_utc":slot,"signals":[row]}))
   result=mod.build(Path(temp),datetime(2026,10,15,15,tzinfo=timezone.utc))
   self.assertEqual(result["observations"][0]["observed_at"],"2026-10-15T08:10:00+00:00")
   self.assertEqual(result["observations"][0]["scan_slot_utc"],1)
 def test_missing_archive_never_fabricates_signals(self):
  with tempfile.TemporaryDirectory() as temp:
   result=mod.build(Path(temp),datetime(2026,10,15,tzinfo=timezone.utc))
   self.assertEqual(result["slots_considered"],0)
   self.assertEqual(result["observations"],[])

if __name__=="__main__":unittest.main()
