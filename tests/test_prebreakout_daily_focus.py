import sys
import unittest
from datetime import date
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from refresh_prebreakout_scanner import daily_focus

class DailyFocusTests(unittest.TestCase):
    def sample(self,ticker="AAA",score=80):
        return {"ticker":ticker,"date":"2026-10-23","stage":"pré-breakout",
                "source":"yahoo:daily_ohlcv","vcpConfirmed":True,
                "volumeDry":True,"volumeConfirmed":False,"score":score,"distancePct":2}
    def test_no_candidate_abstains(self):
        result=daily_focus([],date(2026,10,24))
        self.assertEqual(result["status"],"no_qualified_setup")
        self.assertIsNone(result["success_probability"])
    def test_chooses_single_best_and_does_not_invent_probability(self):
        result=daily_focus([self.sample("A",66),self.sample("B",90)],date(2026,10,24))
        self.assertEqual(result["ticker"],"B")
        self.assertEqual(result["status"],"research_candidate")
        self.assertIsNone(result["success_probability"])
    def test_rejects_stale_and_unconfirmed_evidence(self):
        old=self.sample();old["date"]="2026-10-10"
        loose=self.sample();loose["volumeDry"]=False
        self.assertIsNone(daily_focus([old,loose],date(2026,10,24))["ticker"])
if __name__=="__main__":
    unittest.main()
