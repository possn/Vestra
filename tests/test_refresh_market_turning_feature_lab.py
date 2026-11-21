import math
import sys
import unittest
from datetime import datetime, date, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from refresh_market_turning_feature_lab import collect, normalize_yahoo


class Frame:
    empty = False
    columns = ("Close", "High", "Low", "Volume")

    def __init__(self, values):
        self.values = values

    def iterrows(self):
        return iter(self.values)


class HistoricalTurningRefreshTests(unittest.TestCase):
    def days(self, amount=800):
        day = date(2020, 1, 1)
        result = []
        while len(result) < amount:
            if day.weekday() < 5:
                i = len(result)
                p = 100 + i * 0.015 + math.sin(i / 10)
                result.append((datetime.combine(day, datetime.min.time()),
                               {"Close": p, "High": p + 1, "Low": p - 1,
                                "Volume": 100000 + i}))
            day += timedelta(days=1)
        return result

    def test_maturity_filter_and_optional_symbol_failure(self):
        rows = self.days()
        day = rows[-2][0].date()
        frame = Frame(rows)
        eligible = normalize_yahoo(frame, day)
        self.assertEqual(eligible[-1]["date"], rows[-3][0].date().isoformat())
        self.assertTrue(all(row["high"] >= row["close"] >= row["low"]
                            for row in eligible))

        def downloader(ticker, **kwargs):
            if ticker == "^COR1M":
                return None
            return frame

        result = collect(downloader, now=datetime(2026, 11, 21,
                                                 tzinfo=timezone.utc))
        self.assertGreater(result["sample"]["rows"], 500)
        self.assertFalse(result["probability_calibrated"])
        self.assertEqual(result["feature_coverage"]["cor1m_percentile_126"]["observed"], 0)
        self.assertEqual(result["source_provenance"]["optional_symbol_failures"]["^COR1M"],
                         "missing_or_invalid_completed_bars")
        self.assertFalse(result["source_provenance"]["point_in_time_original_vintage_verified"])
        self.assertTrue(result["source_provenance"]["never_promote_report_to_live_probability_or_risk_gate"])

    def test_missing_spy_is_not_a_zero_probability(self):
        with self.assertRaises(ValueError):
            collect(lambda ticker, **kwargs: None,
                    now=datetime(2026, 11, 21, tzinfo=timezone.utc))

    def test_duplicate_or_invalid_completed_history_is_discarded(self):
        rows = self.days(20)
        repeated = Frame([rows[0], rows[0]] + rows[1:])
        self.assertEqual(normalize_yahoo(repeated, date(2026, 11, 21)), [])


if __name__ == "__main__":
    unittest.main()
