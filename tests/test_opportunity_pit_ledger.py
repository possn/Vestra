"""PIT capture must include failed observations without fabricating outcomes."""
import tempfile
import unittest
import importlib.util
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location("pit_ledger",ROOT/"scripts/build_opportunity_pit_ledger.py")
MODULE=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
build,archive=MODULE.build,MODULE.archive


class OpportunityPitLedgerTests(unittest.TestCase):
    def setUp(self):
        self.now="2026-11-17T15:00:00+00:00"
        self.index={"generated_at":"2026-11-17T13:00:00+00:00","stocks":[
            {"ticker":"AAA","quote_type":"EQUITY","low52_status":"watch",
             "current_price":12.0,"low52_price_basis":"observed_weekly_closes_approximately_52weeks",
             "low52_observed_last_session":"2026-11-16","low52_above_low_pct":1.2,
             "risk_gate":"watch"},
            {"ticker":"ETF","quote_type":"ETF","low52_status":"watch"}]}
        self.pre={"schema":"vestra_prebreakout_v1","generated_at":"2026-11-17T14:30:00+00:00",
                  "research_observations":{"rows":[{"ticker":"BBB","evaluable":True,
                      "last_session":"2026-11-16","adjusted_close":15.0,
                      "first_rejection":"sequential_vcp_contractions"}]}}
        self.small={"schema":"vestra_breakout_lab_smallcap_ohlcv_research_v1",
                    "generated_at":"2026-11-17T14:00:00+00:00",
                    "observations":[{"ticker":"CCC","status":"evaluable_ohlcv",
                        "last_session":"2026-11-16","last_adjusted_close":8.0,
                        "technical_first_rejection":"base_width"}]}

    def test_rejected_and_watch_rows_retained_with_source_provenance(self):
        out=build(self.index,self.pre,self.small,self.now)
        self.assertEqual([r["ticker"] for r in out["low52"]["rows"]],["AAA"])
        self.assertFalse(out["low52"]["rows"][0]["current_price_timestamp_verified"])
        self.assertEqual(out["prebreakout"]["rows"][0]["first_rejection"],
                         "sequential_vcp_contractions")
        self.assertEqual(out["smallcap"]["rows"][0]["adjusted_close"],8.0)
        self.assertTrue(out["not_backtest_or_predictive_validation"])

    def test_future_source_rejected(self):
        self.small["generated_at"]="2026-11-18T00:00:00+00:00"
        with self.assertRaises(ValueError):build(self.index,self.pre,self.small,self.now)

    def test_archive_is_immutable(self):
        with tempfile.TemporaryDirectory() as folder:
            out=build(self.index,self.pre,self.small,self.now)
            first=archive(out,Path(folder))
            original=first.read_bytes()
            changed={**out,"low52":{"rows":[]}}
            self.assertEqual(archive(changed,Path(folder)),first)
            self.assertEqual(first.read_bytes(),original)


if __name__=="__main__":unittest.main()
