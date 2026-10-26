import unittest
from market_period_uncertainty import market_period_bootstrap

def item(i,month,value):
    return {"issuer_id":f"I{i}","episode_id":f"E{i}","signal_date":f"2024-{month:02d}-05",
            "period_id":f"2024-{month:02d}","delta_net_pct":value}

class MarketPeriodTests(unittest.TestCase):
    def test_monthly_common_shock_kept_together(self):
        rows=[item(i,m,4 if m%2 else -2) for m in range(1,13) for i in range(m*10,m*10+3)]
        a=market_period_bootstrap(rows,repetitions=250)
        b=market_period_bootstrap(rows,repetitions=250)
        self.assertEqual(a,b)
        self.assertEqual(a["periods"],12)
        self.assertEqual(a["issuers"],36)
        self.assertEqual(a["mean_delta_net_pct"],1)
    def test_underpowered_abstains(self):
        r=market_period_bootstrap([item(1,1,5)])
        self.assertEqual(r["status"],"insufficient_periods_or_issuers")
        self.assertIsNone(r["ci95_lower_pct"])
    def test_mismatched_period_rejected(self):
        r=item(1,1,1);r["period_id"]="2024-02"
        with self.assertRaises(ValueError):
            market_period_bootstrap([r])
    def test_duplicate_episode_rejected(self):
        r=item(1,1,1)
        with self.assertRaises(ValueError):
            market_period_bootstrap([r,r])
    def test_nonfinite_rejected(self):
        r=item(1,1,float("nan"))
        with self.assertRaises(ValueError):
            market_period_bootstrap([r])
if __name__=="__main__":
    unittest.main()
