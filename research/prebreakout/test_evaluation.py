import unittest
from evaluation import summarize_net_trades, paired_baseline_delta

def trade(i, gross, cost=0.5):
    return {"issuer_id":"ISS"+str(i),"episode_id":"E"+str(i),
            "signal_date":"2025-01-15","gross_return_pct":gross,"total_cost_pct":cost}

class EvaluationTests(unittest.TestCase):
    def test_net_returns_and_factor(self):
        r=summarize_net_trades([trade(1,5,1),trade(2,-2,1)])
        self.assertEqual(r["mean_net_pct"],0.5)
        self.assertAlmostEqual(r["profit_factor"],4/3,places=6)
    def test_no_trades_abstains(self):
        self.assertIsNone(summarize_net_trades([])["mean_net_pct"])
    def test_repeated_episode_rejected(self):
        with self.assertRaises(ValueError):
            summarize_net_trades([trade(1,2),trade(1,3)])
    def test_missing_cost_rejected(self):
        t=trade(1,2);del t["total_cost_pct"]
        with self.assertRaises(KeyError):
            summarize_net_trades([t])
    def test_paired_comparison(self):
        r=paired_baseline_delta([trade(1,5)],[trade(1,3)])
        self.assertEqual(r["mean_delta_net_pct"],2)
    def test_nonmatched_baseline_fails(self):
        with self.assertRaises(ValueError):
            paired_baseline_delta([trade(1,5)],[trade(2,5)])

if __name__=="__main__":
    unittest.main()
