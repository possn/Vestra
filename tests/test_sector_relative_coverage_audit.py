import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from audit_sector_relative_coverage import report

class SectorCoverageAuditTests(unittest.TestCase):
    def test_counts_verified_incomplete_and_missing_without_guessing(self):
        rows = [
            {"ticker": "MSFT", "sector": "Technology",
             "opportunity_stock_return_20d_pct": 4,
             "opportunity_sector_return_20d_pct": 2,
             "opportunity_sector_benchmark_ticker": "XLK",
             "opportunity_sector_benchmark_asof_date": "2026-10-15",
             "opportunity_sector_benchmark_verified": True},
            {"ticker": "AAPL", "sector": "Technology"},
            {"ticker": "NVDA", "sector": "Technology",
             "opportunity_sector_benchmark_verified": True},
            {"ticker": "XLK", "quote_type": "ETF", "sector": "Technology"},
            {"ticker": "VOD.L", "sector": "Communication Services"},
        ]
        value = report({"stocks": rows, "generated_at": "2026-10-16T02:00:00Z"})
        self.assertEqual(value["total"]["eligible"], 3)
        self.assertEqual(value["total"]["verified"], 1)
        self.assertEqual(value["total"]["incomplete"], 1)
        self.assertEqual(value["total"]["unavailable"], 1)
        self.assertEqual(value["total"]["coverage_pct"], 33.33)
        self.assertEqual(value["source_generated_at"], "2026-10-16T02:00:00Z")

    def test_invalid_shape_and_zero_denominator(self):
        with self.assertRaises(ValueError):
            report({"stocks": {}})
        self.assertIsNone(report({"stocks": []})["total"]["coverage_pct"])

if __name__ == "__main__":
    unittest.main()
