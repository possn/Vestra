import sys
import datetime
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from sector_relative_context import evidence

class SectorRelativeEvidenceTests(unittest.TestCase):
    def test_same_date_observations_are_verified(self):
        dates=[(datetime.date(2026,10,15)-datetime.timedelta(days=d)).isoformat() for d in range(20,-1,-1)]
        prices={"MSFT":{"market_return_20d_pct":8,"market_return_asof_date":"2026-10-15","market_return_20d_dates":dates},
                "XLK":{"market_return_20d_pct":3,"market_return_asof_date":"2026-10-15","market_return_20d_dates":dates[:]}}
        result=evidence("MSFT","Technology",prices)
        self.assertTrue(result["opportunity_sector_benchmark_verified"])
        self.assertEqual(result["opportunity_stock_return_20d_pct"],8)
        self.assertEqual(result["opportunity_sector_benchmark_ticker"],"XLK")
        prices["XLK"]["market_return_20d_dates"][0]="2026-09-30"
        self.assertEqual(evidence("MSFT","Technology",prices),{})
        prices["XLK"]["market_return_20d_dates"]=dates[:]
        prices["XLK"]["market_return_asof_date"]="2026-10-14"
        self.assertEqual(evidence("MSFT","Technology",prices),{})
    def test_missing_date_or_unknown_sector_fails_closed(self):
        prices={"MSFT":{"market_return_20d_pct":8},
                "XLK":{"market_return_20d_pct":3,"market_return_asof_date":"2026-10-15"}}
        self.assertEqual(evidence("MSFT","Technology",prices),{})
        self.assertEqual(evidence("MSFT","unknown",prices),{})
        self.assertEqual(evidence("MSFT.L","Technology",prices),{})
    def test_nonfinite_return_rejected(self):
        prices={"MSFT":{"market_return_20d_pct":float("inf"),"market_return_asof_date":"2026-10-15"},
                "XLK":{"market_return_20d_pct":3,"market_return_asof_date":"2026-10-15"}}
        self.assertEqual(evidence("MSFT","Technology",prices),{})
if __name__=="__main__":unittest.main()
