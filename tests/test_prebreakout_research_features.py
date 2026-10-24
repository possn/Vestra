import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from prebreakout_research_features import research_features

def bars(n=32):
    return [{"date":f"2026-01-{i:02d}","high":100+i+1,"low":100+i-1,
             "close":100+i,"volume":1000} for i in range(1,n)]

class PointInTimeFeaturesTests(unittest.TestCase):
    def test_future_prices_cannot_change_prepublication_features(self):
        stock=bars(27);spy=bars(27)
        base=research_features(stock,spy,"2026-01-27T15:00:00Z")
        future={"date":"2026-01-27","high":999,"low":1,"close":900,"volume":10000000}
        self.assertEqual(base,research_features(stock+[future],spy+[future],"2026-01-27T15:00:00Z"))
        self.assertIn("atr14_pct",base["features"])
        self.assertEqual(base["features"]["relative_return_20_vs_spy"],0)
        self.assertFalse(base["point_in_time_adjustments_verified"])

    def test_missing_data_does_not_fabricate_features(self):
        result=research_features(bars(10),bars(10),"2026-01-27T15:00:00Z")
        self.assertEqual(result["features"],{})
        self.assertIn("stock_minimum_21_prior_bars",result["missing"])

    def test_unaligned_benchmark_has_no_relative_strength(self):
        result=research_features(bars(27),bars(24),"2026-01-27T15:00:00Z")
        self.assertNotIn("relative_return_20_vs_spy",result["features"])
        self.assertIn("spy_21_aligned_sessions",result["missing"])

    def test_duplicate_price_day_abstains(self):
        stock=bars(27);result=research_features(stock+[stock[0]],bars(27),"2026-01-27T15:00:00Z")
        self.assertEqual(result["features"],{})

if __name__=="__main__":
    unittest.main()
