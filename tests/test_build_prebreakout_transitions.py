import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("transitions",ROOT/"scripts/build_prebreakout_transitions.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class ObservedTransitionsTests(unittest.TestCase):
    def test_real_stage_changes_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);folder=root/"2026"/"slots";folder.mkdir(parents=True)
            def write(slot,instant,signals):
                name=f"2026-10-15-slot{slot}.json"
                (folder/name).write_text(json.dumps({"schema":"vestra_prebreakout_v1",
                    "generated_at":instant,"scan_slot_utc":slot,"signals":signals}))
            def signal(ticker,stage):
                return {"ticker":ticker,"stage":stage,"source":"yahoo:daily_ohlcv",
                    "score":72,"date":"2026-10-15"}
            write(1,"2026-10-15T08:10:00Z",[signal("AAA","compressão"),signal("BBB","pré-breakout")])
            write(2,"2026-10-15T14:10:00Z",[signal("AAA","pré-breakout")])
            write(3,"2026-10-15T20:10:00Z",[signal("AAA","pré-breakout"),signal("BBB","confirmado")])
            ledger=mod.build(root)
            self.assertEqual(ledger["scans_considered"],3)
            self.assertEqual([(x["ticker"],x["event"],x["from_stage"],x["to_stage"]) for x in ledger["events"]],
                [("AAA","first_observed",None,"compressão"),("BBB","first_observed",None,"pré-breakout"),
                 ("AAA","stage_changed","compressão","pré-breakout"),
                 ("BBB","stage_changed","pré-breakout","confirmado")])
            self.assertEqual(ledger["last_observed"]["AAA"]["last_observed_at"],"2026-10-15T20:10:00+00:00")
            self.assertFalse(any(event["to_stage"]=="invalidado" for event in ledger["events"]))

    def test_carried_signal_does_not_create_observed_transition(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/"2026"/"slots";folder.mkdir(parents=True)
            for slot,stage in [(1,"compressão"),(2,"pré-breakout")]:
                row={"ticker":"AAA","stage":stage,"source":"yahoo:daily_ohlcv",
                     "score":72,"date":"2026-10-15","scanner_verified_at":"2026-10-15T08:10:00+00:00"}
                ts=f"2026-10-15T{slot*6+2:02d}:10:00+00:00"
                (folder/f"2026-10-15-slot{slot}.json").write_text(json.dumps({
                    "schema":"vestra_prebreakout_v1","generated_at":ts,"scan_slot_utc":slot,"signals":[row]}))
            ledger=mod.build(Path(tmp))
            self.assertEqual(len(ledger["events"]),1)
            self.assertEqual(ledger["events"][0]["to_stage"],"compressão")
            self.assertEqual(ledger["events"][0]["scan_slot_utc"],1)

    def test_invalid_archive_is_ignored(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);folder=root/"2026"/"slots";folder.mkdir(parents=True)
            (folder/"2026-10-15-slot2.json").write_text('{"schema":"vestra_prebreakout_v1","generated_at":"2026-10-15T08:10:00Z","scan_slot_utc":2,"signals":[]}')
            self.assertEqual(mod.build(root)["scans_considered"],0)

if __name__=="__main__":
    unittest.main()
