import importlib.util
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("collector",ROOT/"research/prebreakout/smallcap_ohlcv_collector.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class FakeFrame:
    empty=False
    def iterrows(self):
        from datetime import timedelta
        start=datetime(2025,11,1,tzinfo=timezone.utc)
        for i in range(250):
            yield start+timedelta(days=i),{"Open":10,"High":11,"Low":9,"Close":10,"Volume":600_000}

class Ticker:
    fast_info={"currency":"USD"}

class Provider:
    def __init__(self):
        self.calls=[]
    def Ticker(self,ticker):
        self.calls.append(("currency",ticker))
        return Ticker()
    def download(self,ticker,**kwargs):
        self.calls.append(("download",ticker))
        return FakeFrame()

class ResearchCollectorTests(unittest.TestCase):
    def test_cohort_excludes_live_floor_and_non_equities(self):
        rows=[{"ticker":"A","market_cap":120e6,"quote_type":"EQUITY"},
              {"ticker":"B","market_cap":499e6,"quote_type":"EQUITY"},
              {"ticker":"C","market_cap":500e6,"quote_type":"EQUITY"},
              {"ticker":"ETF","market_cap":200e6,"quote_type":"ETF"}]
        self.assertEqual(mod.cohort(rows),["A","B"])
    def test_bounded_rotation_real_ohlcv_not_signals(self):
        rows=[{"ticker":t,"market_cap":150e6,"quote_type":"EQUITY"} for t in ("A","B","C")]
        p=Provider()
        result=mod.collect(rows,p,slot=1,budget=2,
                           checked_at=datetime(2026,7,10,tzinfo=timezone.utc))
        self.assertEqual([x["ticker"] for x in result["observations"]],["C","A"])
        self.assertEqual(result["evaluable_ohlcv"],2)
        self.assertEqual(result["not_observed"],1)
        self.assertTrue(result["not_breakout_candidates"])
        self.assertTrue(all(x["liquidity_5m_usd_verified"] for x in result["observations"]))
        self.assertEqual(len([c for c in p.calls if c[0]=="download"]),2)
    def test_unobserved_current_cohort_names_are_prioritized(self):
        from datetime import timedelta
        now=datetime(2026,11,9,6,tzinfo=timezone.utc)
        names=["A","B","C","D","E"]
        old={"schema":"vestra_breakout_lab_smallcap_ohlcv_research_v1",
             "generated_at":(now-timedelta(hours=2)).isoformat(),
             "observations":[
               {"ticker":"A","observation_checked_at":(now-timedelta(hours=2)).isoformat()},
               {"ticker":"B","observation_checked_at":(now-timedelta(hours=3)).isoformat()},
               {"ticker":"E","observation_checked_at":(now-timedelta(hours=6)).isoformat()}]}
        selected=mod.pick_research_tickers(names,slot=0,budget=2,previous=old,checked_at=now)
        self.assertEqual(selected,["C","D"])
        # Second slot picks the remaining unobserved ticker, not blindly A/B.
        old["observations"].extend({"ticker":t,"observation_checked_at":now.isoformat()}
                                    for t in selected)
        self.assertEqual(mod.pick_research_tickers(names,slot=1,budget=2,
                           previous=old,checked_at=now),["E","B"])

    def test_stale_outside_cohort_and_future_dates_do_not_block_new_coverage(self):
        from datetime import timedelta
        now=datetime(2026,11,9,6,tzinfo=timezone.utc)
        old={"schema":"vestra_breakout_lab_smallcap_ohlcv_research_v1",
             "generated_at":now.isoformat(),"observations":[
                {"ticker":"A","observation_checked_at":(now-timedelta(hours=97)).isoformat()},
                {"ticker":"B","observation_checked_at":(now+timedelta(hours=1)).isoformat()},
                {"ticker":"Z","observation_checked_at":now.isoformat()}]}
        self.assertEqual(mod.pick_research_tickers(["A","B","C"],0,3,old,now),
                         ["A","B","C"])
        self.assertEqual(mod.pick_research_tickers(["A","B","C"],0,2,old,now),
                         ["A","B"])
        old["observations"]=[{"ticker":"A","observation_checked_at":now.isoformat()},
                             {"ticker":"B","observation_checked_at":
                              (now-timedelta(hours=2)).isoformat()},
                             {"ticker":"C","observation_checked_at":
                              (now-timedelta(hours=1)).isoformat()}]
        self.assertEqual(mod.pick_research_tickers(["A","B","C"],0,2,old,now),
                         ["B","C"])

    def test_collect_uses_previous_evidence_for_bounded_provider_budget(self):
        now=datetime(2026,7,10,tzinfo=timezone.utc)
        rows=[{"ticker":x,"market_cap":150e6,"quote_type":"EQUITY"}
              for x in ("A","B","C","D")]
        prior={"schema":"vestra_breakout_lab_smallcap_ohlcv_research_v1",
               "generated_at":now.isoformat(),
               "observations":[{"ticker":"A","observation_checked_at":now.isoformat()},
                               {"ticker":"B","observation_checked_at":now.isoformat()}]}
        provider=Provider()
        result=mod.collect(rows,provider,slot=0,budget=2,checked_at=now,previous=prior)
        self.assertEqual([r["ticker"] for r in result["observations"]],["C","D"])
        self.assertEqual(len([c for c in provider.calls if c[0]=="download"]),2)

    def test_recent_zero_volume_is_incomplete_research_not_an_invalid_price(self):
        from datetime import timedelta
        class NoTradeFrame:
            empty=False
            def iterrows(self):
                start=datetime(2025,11,1,tzinfo=timezone.utc)
                for i in range(250):
                    yield start+timedelta(days=i), {
                        "Open":10,"High":11,"Low":9,"Close":10,
                        "Volume":0 if i==230 else 600_000}
        from unittest.mock import patch
        with patch("scripts.refresh_prebreakout_scanner.scan_bars") as scanner:
            row=mod.inspect("ZERO",NoTradeFrame(),"USD",
                            datetime(2026,7,10,tzinfo=timezone.utc))
        self.assertEqual(row["status"],"zero_volume_interrupted_history")
        self.assertEqual(row["zero_volume_sessions"],1)
        self.assertTrue(row["setup_blocked"])
        self.assertEqual(row["bars"],19)
        scanner.assert_not_called()

    def test_ancient_zero_volume_outside_220_consecutive_sessions_does_not_invalidate_fresh_data(self):
        from datetime import timedelta
        class OldNoTradeFrame:
            empty=False
            def iterrows(self):
                start=datetime(2025,11,1,tzinfo=timezone.utc)
                for i in range(250):
                    yield start+timedelta(days=i), {
                        "Open":10,"High":11,"Low":9,"Close":10,
                        "Volume":0 if i==10 else 600_000}
        from unittest.mock import patch
        with patch("scripts.refresh_prebreakout_scanner.scan_bars",return_value=None) as scanner:
            row=mod.inspect("ZERO",OldNoTradeFrame(),"USD",
                            datetime(2026,7,10,tzinfo=timezone.utc))
        self.assertEqual(row["status"],"evaluable_ohlcv")
        self.assertEqual(row["zero_volume_sessions_before_contiguous_window"],1)
        self.assertEqual(row["bars"],239)
        bars=scanner.call_args.args[1]
        self.assertEqual(len(bars),239)
        self.assertTrue(all(b["volume"]>0 for b in bars))

    def test_currency_unknown_prevents_provider_download(self):
        class UnknownProvider(Provider):
            def Ticker(self,ticker):
                return type("T",(),{"fast_info":{"currency":None}})()
        p=UnknownProvider()
        rows=[{"ticker":"A","market_cap":200e6,"quote_type":"EQUITY"}]
        report=mod.collect(rows,p,checked_at=datetime(2026,7,10,tzinfo=timezone.utc))
        self.assertEqual(report["evaluable_ohlcv"],0)
        self.assertEqual(report["observations"][0]["status"],"currency_not_verified_usd")
        self.assertFalse(any(x[0]=="download" for x in p.calls))
    def test_verified_setup_is_only_published_after_real_ohlcv_and_usd_gate(self):
        from unittest.mock import patch
        rows=[{"ticker":"A","market_cap":180e6,"quote_type":"EQUITY"}]
        fake={"ticker":"A","stage":"pré-breakout","score":72,
              "date":"2026-07-08","distancePct":2.5,"vcpConfirmed":True}
        with patch("scripts.refresh_prebreakout_scanner.scan_bars",return_value=fake) as scanner:
            report=mod.collect(rows,Provider(),checked_at=datetime(2026,7,10,tzinfo=timezone.utc))
        self.assertEqual(len(report["signals"]),1)
        self.assertEqual(report["signals"][0]["marketCapUSD"],180e6)
        self.assertEqual(report["signals"][0]["source"],"yahoo:smallcap_daily_ohlcv")
        self.assertFalse(report["signals"][0]["spreadVerified"])
        self.assertEqual(report["signals"][0]["earningsRiskGate"],"unknown")
        self.assertEqual(scanner.call_args.kwargs["liquidity_floor"],1_000_000)

    def test_no_price_pattern_never_becomes_a_signal(self):
        rows=[{"ticker":"A","market_cap":200e6,"quote_type":"EQUITY"}]
        report=mod.collect(rows,Provider(),checked_at=datetime(2026,7,10,tzinfo=timezone.utc))
        self.assertEqual(report["signals"],[])
        self.assertEqual(report["validated_prebreakout_setups"],0)

    def test_current_day_daily_bar_is_not_treated_as_closed(self):
        from datetime import timedelta
        class SessionFrame:
            empty=False
            def iterrows(self):
                last=datetime(2026,7,10,tzinfo=timezone.utc)
                for i in range(250):
                    yield last-timedelta(days=249-i),{"Open":10,"High":11,"Low":9,"Close":10,"Volume":600_000}
        result=mod.inspect("A",SessionFrame(),"USD",datetime(2026,7,10,12,tzinfo=timezone.utc))
        self.assertEqual(result["last_session"],"2026-07-09")
        self.assertEqual(result["bars"],249)

    def test_merge_slots_retains_recent_distinct_observations(self):
        from datetime import timedelta
        now=datetime(2026,10,30,18,tzinfo=timezone.utc)
        old={"schema":"vestra_breakout_lab_smallcap_ohlcv_research_v1",
             "generated_at":(now-timedelta(hours=6)).isoformat(),
             "observations":[{"ticker":"A","status":"evaluable_ohlcv",
                              "verified_prebreakout_setup":{"ticker":"A","score":70}},
                             {"ticker":"B","status":"no_ohlcv"}]}
        current={"schema":old["schema"],"generated_at":now.isoformat(),
                 "universe_100m_500m_count":5,
                 "observations":[{"ticker":"C","status":"evaluable_ohlcv",
                                  "verified_prebreakout_setup":None}],
                 "signals":[]}
        merged=mod.merge_slots(current,old,now)
        self.assertEqual({x["ticker"] for x in merged["observations"]},{"A","B","C"})
        self.assertEqual([x["ticker"] for x in merged["signals"]],["A"])
        self.assertEqual(merged["distinct_tickers_observed"],3)
        self.assertEqual(merged["not_observed"],2)
        self.assertEqual(next(x for x in merged["observations"] if x["ticker"]=="C")["observation_checked_at"],now.isoformat())

    def test_rolling_coverage_cannot_repromote_stale_setups(self):
        from datetime import timedelta
        now=datetime(2026,11,9,12,tzinfo=timezone.utc)
        schema="vestra_breakout_lab_smallcap_ohlcv_research_v1"
        prior={"schema":schema,"generated_at":(now-timedelta(hours=24)).isoformat(),
               "observations":[
                 {"ticker":"OLD","status":"evaluable_ohlcv",
                  "observation_checked_at":(now-timedelta(hours=24)).isoformat(),
                  "verified_prebreakout_setup":{"ticker":"OLD","score":99}},
                 {"ticker":"FRESH","status":"evaluable_ohlcv",
                  "observation_checked_at":(now-timedelta(hours=6)).isoformat(),
                  "verified_prebreakout_setup":{"ticker":"FRESH","score":70}}]}
        current={"schema":schema,"generated_at":now.isoformat(),
                 "universe_100m_500m_count":3,
                 "observations":[{"ticker":"NEW","status":"evaluable_ohlcv",
                                  "verified_prebreakout_setup":None}]}
        report=mod.merge_slots(current,prior,now,eligible_tickers={"OLD","FRESH","NEW"})
        self.assertEqual({row["ticker"] for row in report["observations"]},{"OLD","FRESH","NEW"})
        self.assertEqual([item["ticker"] for item in report["signals"]],["FRESH"])
        self.assertEqual(report["historical_setups_excluded_as_stale"],1)
        self.assertEqual(report["setup_verification_window_hours"],18)
        self.assertEqual(report["evaluable_ohlcv"],3)
        self.assertEqual(report["universe_coverage_pct"],100.0)

    def test_legacy_observation_timestamp_is_not_renewed_by_republication(self):
        from datetime import timedelta
        now=datetime(2026,11,9,12,tzinfo=timezone.utc)
        schema="vestra_breakout_lab_smallcap_ohlcv_research_v1"
        older=(now-timedelta(hours=6)).isoformat()
        previous={"schema":schema,"generated_at":older,
                  "observations":[{"ticker":"OLD","status":"evaluable_ohlcv",
                                   "verified_prebreakout_setup":{"ticker":"OLD","score":80}}]}
        current={"schema":schema,"generated_at":now.isoformat(),
                 "universe_100m_500m_count":2,
                 "observations":[{"ticker":"NEW","status":"no_ohlcv"}]}
        first=mod.merge_slots(current,previous,now,eligible_tickers={"OLD","NEW"})
        observed_old=next(r for r in first["observations"] if r["ticker"]=="OLD")
        self.assertEqual(observed_old["observation_checked_at"],older)
        self.assertEqual([x["ticker"] for x in first["signals"]],["OLD"])
        later=now+timedelta(hours=20)
        next_current={"schema":schema,"generated_at":later.isoformat(),
                      "universe_100m_500m_count":2,
                      "observations":[{"ticker":"NEW","status":"no_ohlcv"}]}
        second=mod.merge_slots(next_current,first,later,eligible_tickers={"OLD","NEW"})
        self.assertEqual(second["signals"],[])
        self.assertEqual({r["ticker"] for r in second["observations"]},{"OLD","NEW"})
        self.assertEqual(second["historical_setups_excluded_as_stale"],1)

    def test_rejected_provider_recheck_cannot_retain_prior_signal(self):
        now=datetime(2026,11,9,12,tzinfo=timezone.utc)
        schema="vestra_breakout_lab_smallcap_ohlcv_research_v1"
        prior={"schema":schema,"generated_at":now.isoformat(),
               "observations":[{"ticker":"A","status":"evaluable_ohlcv",
                                "verified_prebreakout_setup":{"ticker":"A","score":85}}]}
        current={"schema":schema,"generated_at":now.isoformat(),
                 "universe_100m_500m_count":1,
                 "observations":[{"ticker":"A","status":"provider_error"}]}
        report=mod.merge_slots(current,prior,now,eligible_tickers={"A"})
        self.assertEqual(report["signals"],[])
        self.assertEqual(report["evaluable_ohlcv"],0)
        self.assertEqual(report["observations"][0]["status"],"provider_error")

    def test_merge_slots_does_not_revive_expired_observations(self):
        from datetime import timedelta
        now=datetime(2026,10,30,18,tzinfo=timezone.utc)
        previous={"schema":"vestra_breakout_lab_smallcap_ohlcv_research_v1",
                  "generated_at":(now-timedelta(hours=97)).isoformat(),
                  "observations":[{"ticker":"EXPIRED","status":"evaluable_ohlcv",
                                   "verified_prebreakout_setup":{"ticker":"EXPIRED"}}]}
        current={"schema":previous["schema"],"generated_at":now.isoformat(),
                 "universe_100m_500m_count":4,
                 "observations":[{"ticker":"NEW","status":"no_ohlcv"}]}
        merged=mod.merge_slots(current,previous,now)
        self.assertEqual(merged["signals"],[])
        self.assertEqual([x["ticker"] for x in merged["observations"]],["NEW"])

    def test_merge_slots_excludes_previous_tickers_outside_current_universe(self):
        now=datetime(2026,10,30,18,tzinfo=timezone.utc)
        schema="vestra_breakout_lab_smallcap_ohlcv_research_v1"
        previous={"schema":schema,"generated_at":now.isoformat(),
                  "observations":[{"ticker":"OLD","status":"evaluable_ohlcv",
                                   "verified_prebreakout_setup":{"ticker":"OLD"}},
                                  {"ticker":"A","status":"evaluable_ohlcv",
                                   "verified_prebreakout_setup":{"ticker":"A"}}]}
        current={"schema":schema,"generated_at":now.isoformat(),
                 "universe_100m_500m_count":2,
                 "observations":[{"ticker":"B","status":"evaluable_ohlcv",
                                  "verified_prebreakout_setup":None}]}
        merged=mod.merge_slots(current,previous,now,eligible_tickers={"A","B"})
        self.assertEqual({x["ticker"] for x in merged["observations"]},{"A","B"})
        self.assertEqual([x["ticker"] for x in merged["signals"]],["A"])
        self.assertEqual(merged["excluded_outside_current_universe"],1)
        self.assertEqual(merged["universe_coverage_pct"],100.0)
        with self.assertRaises(ValueError):
            mod.merge_slots(current,previous,now,eligible_tickers={"A"})
        bad={**current,"observations":[{"ticker":"OLD","status":"evaluable_ohlcv"}]}
        with self.assertRaises(ValueError):
            mod.merge_slots(bad,previous,now,eligible_tickers={"A","B"})

    def test_rejects_invalid_limits(self):
        for slot,budget in ((-1,1),(0,0),(0,31)):
            with self.assertRaises(ValueError):mod.collect([],Provider(),slot,budget)
if __name__=="__main__":unittest.main()
