"""Regression: Yahoo can publish EPS on earnings_dates before earnings_history."""
import sys
import unittest
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
yf = ModuleType("yfinance")
yf.Ticker = lambda ticker: None
with patch.dict(sys.modules, {"yfinance": yf}):
    import analyst


class Dates:
    empty = False
    def iterrows(self):
        from datetime import datetime, timezone
        yield datetime(2026, 10, 13, 12, tzinfo=timezone.utc), {
            "Reported EPS": 2.5,
            "EPS Estimate": 2.0,
            "Surprise(%)": 25.0,
        }


class EarningsFallbackTests(unittest.TestCase):
    def test_confirmed_report_recovers_eps_when_history_missing(self):
        ticker = SimpleNamespace(
            get_earnings_estimate=lambda: None,
            get_revenue_estimate=lambda: None,
            get_eps_trend=lambda: None,
            get_eps_revisions=lambda: None,
            get_earnings_history=lambda: None,
            get_earnings_dates=lambda limit: Dates(),
            get_recommendations=lambda: None,
            get_analyst_price_targets=lambda: None,
        )
        with patch.object(analyst.yf, "Ticker", return_value=ticker):
            result = analyst.fetch_one("JPM")
        self.assertEqual(result.latest_earnings_date, "2026-10-13")
        self.assertEqual(result.latest_eps_actual, 2.5)
        self.assertEqual(result.latest_eps_estimate, 2.0)
        self.assertAlmostEqual(result.latest_eps_surprise_pct, 0.25)
        self.assertEqual(result.earnings_history_4q[0]["actual"], 2.5)

    def test_multiple_reports_pick_latest_confirmed_date(self):
        class MultipleReports(Dates):
            def iterrows(self):
                from datetime import datetime, timezone
                yield datetime(2026, 7, 14, tzinfo=timezone.utc), {
                    "Reported EPS": 1.5, "EPS Estimate": 1.4,
                }
                yield datetime(2026, 10, 13, tzinfo=timezone.utc), {
                    "Reported EPS": 2.5, "EPS Estimate": 2.0,
                }
        ticker = SimpleNamespace(
            get_earnings_estimate=lambda: None,
            get_revenue_estimate=lambda: None,
            get_eps_trend=lambda: None,
            get_eps_revisions=lambda: None,
            get_earnings_history=lambda: None,
            get_earnings_dates=lambda limit: MultipleReports(),
            get_recommendations=lambda: None,
            get_analyst_price_targets=lambda: None,
        )
        with patch.object(analyst.yf, "Ticker", return_value=ticker):
            result = analyst.fetch_one("GS")
        self.assertEqual(result.latest_earnings_date, "2026-10-13")
        self.assertEqual(result.latest_eps_actual, 2.5)
        self.assertAlmostEqual(result.latest_eps_surprise_pct, 0.25)

    def test_missing_reported_eps_does_not_fabricate_result(self):
        class EmptyReport(Dates):
            def iterrows(self):
                from datetime import datetime, timezone
                yield datetime(2026, 10, 13, tzinfo=timezone.utc), {
                    "Reported EPS": None, "EPS Estimate": 2.0,
                }
        ticker = SimpleNamespace(
            get_earnings_estimate=lambda: None,
            get_revenue_estimate=lambda: None,
            get_eps_trend=lambda: None,
            get_eps_revisions=lambda: None,
            get_earnings_history=lambda: None,
            get_earnings_dates=lambda limit: EmptyReport(),
            get_recommendations=lambda: None,
            get_analyst_price_targets=lambda: None,
        )
        with patch.object(analyst.yf, "Ticker", return_value=ticker):
            result = analyst.fetch_one("JNJ")
        self.assertIsNone(result.latest_eps_actual)
        self.assertIsNone(result.latest_eps_surprise_pct)


if __name__ == "__main__":
    unittest.main()
