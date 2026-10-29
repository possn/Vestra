import importlib.util
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("study",ROOT/"research/prebreakout/prebase_impulse_audit.py")
study=importlib.util.module_from_spec(spec)
spec.loader.exec_module(study)

class MorphologyResearchTests(unittest.TestCase):
    def row(self,episode,label,ret,verified=True):
        return {"episode_id":episode,"horizon_sessions":10,"outcome":label,
                "outcome_matured":True,"features_point_in_time_verified":verified,
                "features":{"preBaseReturn40Pct":ret,"preBaseRange40Pct":abs(ret)+4,
                            "contractionWidths20Pct":[10.0,5.0,2.0]}}
    def test_duplicate_pending_and_unverified_not_counted(self):
        records=[self.row("A","confirmed",30),self.row("A","confirmed",99),
                 self.row("B","not_confirmed",2),self.row("C","confirmed",50,False),
                 {**self.row("D","not_confirmed",10),"outcome_matured":False}]
        result=study.audit(records,min_per_group=1)["by_horizon"]["10"]
        self.assertEqual(result["distinct_verified_episodes"],2)
        self.assertEqual(result["excluded"],{"unknown_outcome":1,"unverified_asof":1,"missing_features":0,"duplicate_episode":1})
        f=result["features"]["preBaseReturn40Pct"]
        self.assertEqual((f["confirmed_median"],f["not_confirmed_median"]),(30,2))
        self.assertTrue(f["minimum_descriptive_evidence_met"])
    def test_missing_feature_record_does_not_reserve_episode_id(self):
        incomplete=self.row("A","confirmed",30)
        incomplete["features"]=None
        complete=self.row("A","confirmed",12)
        opposite=self.row("B","not_confirmed",2)
        result=study.audit([incomplete,complete,opposite],min_per_group=1)["by_horizon"]["10"]
        self.assertEqual(result["distinct_verified_episodes"],2)
        self.assertEqual(result["excluded"]["missing_features"],1)
        self.assertEqual(result["excluded"]["duplicate_episode"],0)
        feature=result["features"]["preBaseReturn40Pct"]
        self.assertEqual(feature["confirmed_median"],12)
        self.assertEqual(feature["not_confirmed_median"],2)
        self.assertFalse(study.audit([incomplete,complete,opposite],min_per_group=1)["predictive_validity_established"])

    def test_without_grounded_episodes_no_claim(self):
        result=study.audit([self.row("A","confirmed",40,False)])
        self.assertFalse(result["predictive_validity_established"])
        self.assertFalse(result["live_gate_approved"])
        self.assertIsNone(result["by_horizon"]["10"]["features"]["preBaseReturn40Pct"]["median_difference"])
    def test_missing_impulse_evidence_stays_missing(self):
        x=self.row("A","confirmed",30)
        x["features"]["contractionWidths20Pct"]=[10,None,2]
        y=self.row("B","not_confirmed",3)
        f=study.audit([x,y],1)["by_horizon"]["10"]["features"]["contractionWidths20Pct"]
        self.assertEqual(f["confirmed_n"],0)
        self.assertIsNone(f["median_difference"])

    def test_only_strictly_decreasing_widths_are_descriptive_contractions(self):
        good=self.row("A","confirmed",30)
        bad=self.row("B","not_confirmed",3)
        bad["features"]["contractionWidths20Pct"]=[10.0,12.0,2.0]
        flat=self.row("C","not_confirmed",5)
        flat["features"]["contractionWidths20Pct"]=[10.0,10.0,2.0]
        result=study.audit([good,bad,flat],min_per_group=1)["by_horizon"]["10"]
        feature=result["features"]["contractionWidths20Pct"]
        self.assertEqual(feature["confirmed_n"],1)
        self.assertEqual(feature["not_confirmed_n"],0)
        self.assertIsNone(feature["median_difference"])
        self.assertFalse(feature["minimum_descriptive_evidence_met"])
        # Valid impulse features remain available without declaring edge.
        self.assertEqual(result["features"]["preBaseReturn40Pct"]["not_confirmed_n"],2)


if __name__=="__main__":
    unittest.main()
