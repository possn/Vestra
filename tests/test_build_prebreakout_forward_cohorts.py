import json
import sys
import tempfile
import unittest
from datetime import date,timedelta
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from build_prebreakout_forward_cohorts import cohorts,build

class ImmutableCohortTests(unittest.TestCase):
    def fixture(self,folder):
        path=folder/"2026"/"slots"
        path.mkdir(parents=True)
        def slot(number,day,time,stage):
            (path/f"{day}-slot{number}.json").write_text(json.dumps({
                "schema":"vestra_prebreakout_v1","generated_at":f"{day}T{time}:00Z",
                "scan_slot_utc":number,"signals":[{
                    "ticker":"AAA","date":day,"stage":stage,"score":65,
                    "source":"yahoo:daily_ohlcv"}]}))
        slot(1,"2026-10-15","08:10","compressão")
        slot(2,"2026-10-15","14:10","compressão")
        slot(3,"2026-10-15","20:10","pré-breakout")

    def bars(self):
        start=date(2026,10,15)
        return [{"date":(start+timedelta(days=i)).isoformat(),"close":100+i} for i in range(13)]

    def test_repeated_stage_does_not_expand_cohort(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp);self.fixture(path)
            cases=cohorts(path)
            self.assertEqual(len(cases),2)
            self.assertEqual([x["stage"] for x in cases],["compressão","pré-breakout"])
            self.assertEqual(cases[0]["published_at"],"2026-10-15T08:10:00+00:00")
            self.assertEqual(cases[1]["published_at"],"2026-10-15T20:10:00+00:00")

    def test_new_anchored_base_is_distinct_but_repeated_slots_do_not_duplicate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);folder=root/"2026"/"slots";folder.mkdir(parents=True)
            for day,slot,anchor in [("2026-10-15",1,"2026-09-01"),
                                    ("2026-10-15",2,"2026-09-01"),
                                    ("2026-10-20",1,"2026-10-01")]:
                (folder/f"{day}-slot{slot}.json").write_text(json.dumps({
                    "schema":"vestra_prebreakout_v1",
                    "generated_at":f"{day}T{slot*6+1:02d}:00:00Z",
                    "scan_slot_utc":slot,
                    "signals":[{"ticker":"AAA","date":day,"stage":"compressão",
                                "baseStartDate":anchor,"source":"yahoo:daily_ohlcv"}]}))
            cases=cohorts(root)
            self.assertEqual(len(cases),2)
            self.assertEqual([r["base_start_date"] for r in cases],["2026-09-01","2026-10-01"])
            summary=build(root,{},self.bars())
            self.assertEqual(summary["base_identity_coverage"],{"anchored":2,"legacy_unanchored":0})
            self.assertEqual(summary["breakout_event_evidence"]["coverage_by_horizon"]["5"]["cohorts"],2)

    def test_bad_or_future_base_anchor_cannot_create_cohort(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);folder=root/"2026"/"slots";folder.mkdir(parents=True)
            (folder/"2026-10-15-slot1.json").write_text(json.dumps({
                "schema":"vestra_prebreakout_v1","generated_at":"2026-10-15T07:00:00Z",
                "scan_slot_utc":1,"signals":[
                    {"ticker":"AAA","date":"2026-10-15","stage":"compressão",
                     "baseStartDate":"2026-10-16","source":"yahoo:daily_ohlcv"}]}))
            self.assertEqual(cohorts(root),[])

    def test_missing_prices_are_missing_not_zero_performance(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp);self.fixture(path)
            result=build(path,{},self.bars())
            self.assertEqual(result["cohort_count"],2)
            self.assertTrue(all(not case["results"] for case in result["outcomes"]))
            self.assertEqual(result["stage_evidence"]["stages"]["compressão"]["5"]["n"],0)

    def test_future_only_post_publication_adjusted_closes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp);self.fixture(path)
            bars=self.bars()
            result=build(path,{"AAA":bars},[{"date":r["date"],"close":100} for r in bars])
            self.assertEqual(result["cohort_count"],2)
            self.assertEqual(result["outcomes"][0]["entry"],"2026-10-16")
            self.assertEqual(result["stage_evidence"]["stages"]["compressão"]["5"]["n"],1)
            self.assertNotIn("hit_rate",result["stage_evidence"]["stages"]["compressão"]["5"])

    def test_wrong_slot_never_creates_cohort(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);f=root/"2026"/"slots";f.mkdir(parents=True)
            (f/"2026-10-15-slot2.json").write_text(json.dumps({"schema":"vestra_prebreakout_v1",
                "generated_at":"2026-10-15T08:10:00Z","scan_slot_utc":2,
                "signals":[{"ticker":"FAKE","date":"2026-10-15","stage":"confirmado","source":"yahoo:daily_ohlcv"}]}))
            self.assertEqual(cohorts(root),[])

if __name__=="__main__":
    unittest.main()
