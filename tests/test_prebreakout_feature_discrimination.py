import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from prebreakout_feature_discrimination import compare_features

class DescriptiveComparisonTests(unittest.TestCase):
    def test_pending_records_do_not_become_failures(self):
        rows=[{"episode_id":"A","horizon_sessions":5,"outcome":"confirmed","outcome_matured":True,"features_point_in_time_verified":True,"features":{"atr14_pct":2.0}},
              {"episode_id":"B","horizon_sessions":5,"outcome":"not_confirmed","outcome_matured":True,"features_point_in_time_verified":True,"features":{"atr14_pct":4.0}},
              {"horizon_sessions":5,"outcome":"pending_or_unverified","features":{"atr14_pct":100.0}}]
        result=compare_features(rows,min_per_group=1)
        h=result["by_horizon"]["5"]
        self.assertEqual(h["excluded_pending_or_unverified"],1)
        self.assertEqual(h["features"]["atr14_pct"]["median_difference"],-2.0)
        self.assertFalse(h["features"]["atr14_pct"]["significance_tested"])
        self.assertFalse(result["predictive_validity_established"])

    def test_missing_values_do_not_inflate_denominators(self):
        rows=[{"episode_id":"C","horizon_sessions":10,"outcome":"confirmed","outcome_matured":True,"features_point_in_time_verified":True,"features":{"atr14_pct":float("nan")}},
              {"episode_id":"D","horizon_sessions":10,"outcome":"not_confirmed","outcome_matured":True,"features_point_in_time_verified":True,"features":{}}]
        value=compare_features(rows)["by_horizon"]["10"]["features"]["atr14_pct"]
        self.assertEqual(value["confirmed_n"],0)
        self.assertIsNone(value["median_difference"])
        self.assertFalse(value["minimum_descriptive_evidence_met"])

    def test_unverified_and_duplicate_episodes_cannot_fake_discrimination(self):
        def row(episode,label,value,**extras):
            return {"episode_id":episode,"horizon_sessions":10,"outcome":label,
                    "outcome_matured":True,"features_point_in_time_verified":True,
                    "features":{"atr14_pct":value},**extras}
        rows=[
            row("A","confirmed",2),
            row("A","confirmed",90),
            row("B","not_confirmed",4),
            row("C","confirmed",100,features_point_in_time_verified=False),
            row("D","not_confirmed",100,outcome_matured=False),
            {"horizon_sessions":10,"outcome":"confirmed","outcome_matured":True,
             "features_point_in_time_verified":True,"features":{"atr14_pct":20}},
        ]
        h=compare_features(rows,min_per_group=1)["by_horizon"]["10"]
        self.assertEqual(h["distinct_verified_episodes"],2)
        self.assertEqual(h["matured_labeled"],2)
        self.assertEqual(h["features"]["atr14_pct"]["median_difference"],-2)
        self.assertEqual(h["excluded_reasons"],
          {"unmatured_or_unlabeled":1,"unverified_point_in_time":1,
           "missing_episode_identity":1,"duplicate_episode":1})

    def test_no_verified_episode_no_statistical_claim(self):
        rows=[{"episode_id":"A","horizon_sessions":5,"outcome":"confirmed",
               "features":{"atr14_pct":1.0}},
              {"episode_id":"B","horizon_sessions":5,"outcome":"not_confirmed",
               "features":{"atr14_pct":3.0}}]
        h=compare_features(rows,min_per_group=1)["by_horizon"]["5"]
        self.assertEqual(h["matured_labeled"],0)
        self.assertIsNone(h["features"]["atr14_pct"]["median_difference"])
        self.assertFalse(h["features"]["atr14_pct"]["minimum_descriptive_evidence_met"])

if __name__=="__main__":
    unittest.main()
