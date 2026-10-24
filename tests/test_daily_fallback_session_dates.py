import datetime
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
with patch.dict(sys.modules, {"yfinance": Mock(), "requests": Mock(), "ticker_successors": Mock(retrieval_symbol=lambda ticker: ticker)}):
    from insider_prices import _download_direct_daily_returns

class DatedDirectDailyFallbackTests(unittest.TestCase):
    def _response(self, days, tz="America/New_York", omit_timestamps=False):
        stamps = [int(datetime.datetime(2026, 9, 1, 16, tzinfo=datetime.timezone.utc).timestamp()) + 86400 * i for i in range(days)]
        result = {"indicators": {"quote": [{"close": [100.0 + i for i in range(days)]}]}, "meta": {"exchangeTimezoneName": tz}}
        if not omit_timestamps:
            result["timestamp"] = stamps
        return Mock(status_code=200, json=lambda: {"chart": {"result": [result]}})

    @patch.object(_download_direct_daily_returns.__globals__["requests"], "get")
    def test_preserves_verified_21_session_dates(self, get):
        get.return_value = self._response(21)
        metrics = _download_direct_daily_returns("XLK")
        self.assertEqual(len(metrics["market_return_20d_dates"]), 21)
        self.assertEqual(metrics["market_return_asof_date"], metrics["market_return_20d_dates"][-1])
        self.assertIn("market_return_20d_pct", metrics)

    @patch.object(_download_direct_daily_returns.__globals__["requests"], "get")
    def test_no_dates_without_source_timestamps(self, get):
        get.return_value = self._response(21, omit_timestamps=True)
        metrics = _download_direct_daily_returns("XLK")
        self.assertNotIn("market_return_20d_dates", metrics)
        self.assertIn("market_return_20d_pct", metrics)

    @patch.object(_download_direct_daily_returns.__globals__["requests"], "get")
    def test_invalid_exchange_timezone_does_not_invent_sessions(self, get):
        get.return_value = self._response(21, tz="Nonexistent/Exchange")
        self.assertNotIn("market_return_20d_dates", _download_direct_daily_returns("XLK"))

if __name__ == "__main__":
    unittest.main()
