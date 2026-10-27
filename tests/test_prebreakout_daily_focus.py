import sys
import unittest
from datetime import date
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from refresh_prebreakout_scanner import daily_focus,quality_shadow_record

class DailyFocusTests(unittest.TestCase):
    def sample(self,ticker="AAA",score=80):
        return {"ticker":ticker,"date":"2026-10-23","stage":"pré-breakout",
                "source":"yahoo:daily_ohlcv","vcpConfirmed":True,
                "volumeDry":True,"volumeConfirmed":False,"score":score,"distancePct":2}
    def test_rejected_shadow_case_is_not_promoted_to_strict_signal(self):
        old={"ticker":"AAA","date":"2026-10-23","stage":"pré-breakout",
             "resistance":101.5,"signalClose":99.5,"baseStartDate":"2026-09-01"}
        record=quality_shadow_record(old,None)
        self.assertTrue(record["legacy_eligible"])
        self.assertFalse(record["strict_eligible"])
        self.assertEqual(record["resistance"],101.5)
        self.assertEqual(record["baseStartDate"],"2026-09-01")
        self.assertEqual(quality_shadow_record(old,old)["strict_eligible"],True)

    def test_no_candidate_abstains(self):
        result=daily_focus([],date(2026,10,24))
        self.assertEqual(result["status"],"no_qualified_setup")
        self.assertIsNone(result["success_probability"])
    def test_chooses_single_best_and_does_not_invent_probability(self):
        result=daily_focus([self.sample("A",66),self.sample("B",90)],date(2026,10,24))
        self.assertEqual(result["ticker"],"B")
        self.assertEqual(result["status"],"research_candidate")
        self.assertIsNone(result["success_probability"])
    def test_stale_rejected_but_developing_prebreakout_labeled(self):
        old=self.sample();old["date"]="2026-10-10"
        self.assertIsNone(daily_focus([old],date(2026,10,24))["ticker"])
        loose=self.sample();loose["volumeDry"]=False
        result=daily_focus([old,loose],date(2026,10,24))
        self.assertEqual(result["ticker"],"AAA")
        self.assertEqual(result["selection_tier"],"developing_setup")
        self.assertIsNone(result["success_probability"])
if __name__=="__main__":
    unittest.main()
