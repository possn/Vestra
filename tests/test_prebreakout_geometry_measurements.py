"""Verify diagnostic VCP widths reflect actual bars and never qualify a signal."""
import math
import unittest
from datetime import date, timedelta
from scripts.refresh_prebreakout_scanner import scan_bars


class ContinuousGeometryTests(unittest.TestCase):
    def test_shadow_widths_are_measured_from_observed_price_ranges(self):
        last = date(2026, 11, 14)
        bars = []
        for i in range(230):
            close = 10 + i * 0.01
            bars.append({"date": (last - timedelta(days=229-i)).isoformat(),
                         "open": close, "close": close,
                         "high": close * 1.02, "low": close * 0.98,
                         "volume": 1_000_000})
        audit = {}
        scan_bars("FIXTURE", bars, date(2026, 11, 15),
                  strict_quality=True, liquidity_floor=1_000_000, audit=audit)
        geom = audit["geometry_shadow"]
        windows = {"prior_width_pct": bars[-100:-60],
                   "base_width_pct": bars[-40:],
                   "w1_pct": bars[-60:-40],
                   "w2_pct": bars[-40:-20],
                   "w3_pct": bars[-20:]}
        for field, window in windows.items():
            observed = (max(b["high"] for b in window) /
                        min(b["low"] for b in window) - 1) * 100
            with self.subTest(field=field):
                self.assertTrue(math.isfinite(geom[field]))
                self.assertAlmostEqual(geom[field], observed, delta=.00051)
        base_pass = geom["base_width_pct"] <= 22 and (
            geom["base_width_pct"] < geom["prior_width_pct"] * .8)
        self.assertEqual(geom["base_width_pass"], base_pass)
        self.assertEqual(geom["both_pass"],
                         geom["base_width_pass"] and geom["contractions_pass"])
        self.assertTrue(geom["research_only_not_eligibility"])
        lineage = audit["research_prebreakout_lineage"]
        self.assertTrue(lineage["research_only_no_eligibility_or_score_effect"])
        self.assertEqual(lineage["prior_confirmed_breakouts_in_base"], 0)
        self.assertIsInstance(lineage["unbroken_prebreakout_position"], bool)

    def test_already_exceeded_pivot_is_not_research_watch_even_on_ma_failure(self):
        last = date(2026, 11, 14)
        bars = []
        for i in range(230):
            close = 10 + i * .001
            bars.append({"date": (last - timedelta(days=229-i)).isoformat(),
                         "close": close, "high": close * 1.01,
                         "low": close * .99, "volume": 1_000_000})
        bars[-1]["high"] = 12.0  # Intraday excursion beyond prior 39-session high.
        audit = {}
        scan_bars("LATE", bars, date(2026, 11, 15), audit=audit)
        self.assertFalse(audit["research_prebreakout_lineage"]["unbroken_prebreakout_position"])


if __name__ == "__main__":
    unittest.main()
