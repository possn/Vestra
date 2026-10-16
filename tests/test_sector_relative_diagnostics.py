import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from sector_relative_diagnostics import exclusion_summary

def row(ticker, sector="Technology", quote_type="EQUITY"):
    return SimpleNamespace(ticker=ticker, sector=sector, quote_type=quote_type)

class SectorRelativeExclusionTests(unittest.TestCase):
    def test_missing_and_mismatched_sessions_reported_without_fabrication(self):
        days = [f"2026-09-{d:02d}" for d in range(1,22)]
        etf = {"market_return_20d_pct": 3, "market_return_asof_date": days[-1], "market_return_20d_dates": days}
        a = {"market_return_20d_pct": 5, "market_return_asof_date": days[-1], "market_return_20d_dates": days}
        b = {**a, "market_return_20d_dates": days[:-2] + ["2026-09-20", days[-1]]}
        result = exclusion_summary([row("A"), row("B"), row("C"), row("XLK", quote_type="ETF")],
                                   {"XLK": etf, "A": a, "B": b, "C": {}})
        self.assertEqual(result["total"], 3)
        self.assertEqual(result["reasons"]["verified"], 1)
        self.assertEqual(result["reasons"]["session_calendar_mismatch"], 1)
        self.assertEqual(result["reasons"]["stock_sessions_missing"], 1)

if __name__ == "__main__":
    unittest.main()
