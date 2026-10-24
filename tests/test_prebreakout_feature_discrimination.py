import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from prebreakout_feature_discrimination import compare_features

class DescriptiveComparisonTests(unittest.TestCase):
    def test_pending_records_do_not_become_failures(self):
        rows=[{"horizon_sessions":5,"outcome":"confirmed","features":{"atr14_pct":2.0}},
              {"horizon_sessions":5,"outcome":"not_confirmed","features":{"atr14_pct":4.0}},
              {"horizon_sessions":5,"outcome":"pending_or_unverified","features":{"atr14_pct":100.0}}]
        result=compare_features(rows,min_per_group=1)
        h=result["by_horizon"]["5"]
        self.assertEqual(h["excluded_pending_or_unverified"],1)
        self.assertEqual(h["features"]["atr14_pct"]["median_difference"],-2.0)
        self.assertFalse(h["features"]["atr14_pct"]["significance_tested"])
        self.assertFalse(result["predictive_validity_established"])

    def test_missing_values_do_not_inflate_denominators(self):
        rows=[{"horizon_sessions":10,"outcome":"confirmed","features":{"atr14_pct":float("nan")}},
              {"horizon_sessions":10,"outcome":"not_confirmed","features":{}}]
        value=compare_features(rows)["by_horizon"]["10"]["features"]["atr14_pct"]
        self.assertEqual(value["confirmed_n"],0)
        self.assertIsNone(value["median_difference"])
        self.assertFalse(value["minimum_descriptive_evidence_met"])

if __name__=="__main__":
    unittest.main()
