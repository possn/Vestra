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
    def test_geometry_shadow_counts_ma_rejected_without_promoting_setups(self):
        rows=[{"status":"evaluable_ohlcv","technical_first_rejection":"moving_average_structure",
               "technical_geometry_shadow":{"base_width_pass":True,"contractions_pass":True,
                                            "both_pass":True}},
              {"status":"evaluable_ohlcv","technical_first_rejection":"base_width",
               "technical_geometry_shadow":{"base_width_pass":False,"contractions_pass":True,
                                            "both_pass":False}},
              {"status":"evaluable_ohlcv","technical_first_rejection":"below_1m_usd_turnover"},
              {"status":"evaluable_ohlcv","technical_first_rejection":"not_recorded_legacy"}]
        self.assertEqual(mod.independent_geometry_audit(rows),{
            "scope":"evaluable_liquid_series_including_ma_rejections",
            "liquid_evaluable_rows":3,"geometry_diagnosed_rows":2,
            "base_width_pass":1,"contractions_pass":2,"both_pass":1,
            "not_eligibility_or_success_probability":True})

    def test_collector_never_turns_shadow_geometry_into_signal(self):
        rows=[{"ticker":"A","market_cap":150e6,"quote_type":"EQUITY"}]
        report=mod.collect(rows,Provider(),slot=0,budget=1,
                           checked_at=datetime(2026,7,10,tzinfo=timezone.utc))
        self.assertEqual(report["validated_prebreakout_setups"],0)
        self.assertEqual(report["independent_geometry_audit"]["geometry_diagnosed_rows"],1)
        self.assertEqual(report["independent_geometry_audit"]["both_pass"],0)
        self.assertIsInstance(report["observations"][0]["technical_geometry_shadow"],dict)

    def test_overlapping_ma_rejections_remain_nonexclusive(self):
        sample=[{"status":"evaluable_ohlcv","technical_first_rejection":"moving_average_structure",
                 "technical_failed_ma_checks":["price_above_ma50","ma50_rising_10"]},
                {"status":"evaluable_ohlcv","technical_first_rejection":"moving_average_structure",
                 "technical_failed_ma_checks":["ma50_rising_10"]},
                {"status":"evaluable_ohlcv","technical_first_rejection":"base_width"}]
        self.assertEqual(mod.technical_structure_audit(sample),{
            "ma_rejected_rows":2,"diagnosed_ma_rejected_rows":2,
            "nonexclusive_failed_check_counts":{"ma50_rising_10":2,"price_above_ma50":1},
            "not_independent_pass_rates":True})

    def test_technical_rejections_reconcile_with_evaluable_observations(self):
        rows=[{"ticker":"A","market_cap":150e6,"quote_type":"EQUITY"},
              {"ticker":"B","market_cap":200e6,"quote_type":"EQUITY"}]
        report=mod.collect(rows,Provider(),slot=0,budget=2,
                           checked_at=datetime(2026,7,10,tzinfo=timezone.utc))
        self.assertEqual(sum(report["technical_first_rejection_counts"].values()),
                         report["evaluable_ohlcv"])
        self.assertTrue(all("technical_first_rejection" in row
                            for row in report["observations"]
                            if row["status"]=="evaluable_ohlcv"))

    def test_workflow_default_budget_matches_bounded_collector_capacity(self):
        workflow=(ROOT/".github/workflows/smallcap-prebreakout-research.yml").read_text(encoding="utf-8")
        self.assertEqual(mod.MAX_PER_RUN,30)
        self.assertIn("default: '30'",workflow)
        self.assertIn("github.event.inputs.budget || '30'",workflow)

    def test_weekend_slots_preserve_bounded_budget_and_rolling_coverage(self):
        # A Friday-close daily history remains observable on the weekend;
        # all collection slots continue through the existing 30-name budget.
        workflow=(ROOT/".github/workflows/smallcap-prebreakout-research.yml").read_text(encoding="utf-8")
        self.assertIn("cron: '23 0,6,12,18 * * *'",workflow)
        self.assertIn('MAX_PER_RUN=30', (ROOT/"research/prebreakout/smallcap_ohlcv_collector.py").read_text())
        self.assertIn("--budget \"$BUDGET\"",workflow)

    def test_cohort_excludes_live_floor_and_non_equities(self):
        rows=[{"ticker":"A","market_cap":120e6,"quote_type":"EQUITY"},
              {"ticker":"B","market_cap":499e6,"quote_type":"EQUITY"},
              {"ticker":"C","market_cap":500e6,"quote_type":"EQUITY"},
              {"ticker":"ETF","market_cap":200e6,"quote_type":"ETF"}]
        self.assertEqual(mod.cohort(rows),["A","B"])
    def test_duplicate_symbol_is_excluded_regardless_of_row_order(self):
        # A ticker alone is not issuer identity across multiple index rows.
        eligible={"ticker":"DUPE", "market_cap":150e6, "quote_type":"EQUITY"}
        outside={"ticker":"dupe", "market_cap":800e6, "quote_type":"EQUITY"}
        other_type={"ticker":"dupe", "market_cap":200e6, "quote_type":"ETF"}
        safe={"ticker":"SAFE", "market_cap":180e6, "quote_type":"EQUITY"}
        for collision in (outside, other_type, eligible):
            for items in ([eligible,collision,safe],
                          [safe,collision,eligible]):
                with self.subTest(collision=collision["quote_type"],
                                  reversed=items[0] is safe):
                    self.assertEqual(mod.cohort(items), ["SAFE"])
                    provider=Provider()
                    report=mod.collect(items, provider, slot=0, budget=3,
                                       checked_at=datetime(2026,7,10,tzinfo=timezone.utc))
                    self.assertEqual(report["universe_100m_500m_count"],1)
                    self.assertEqual([x["ticker"] for x in report["observations"]],["SAFE"])
                    self.assertNotIn("DUPE", [t for _,t in provider.calls])

    def test_three_way_duplicate_symbol_remains_excluded(self):
        rows=[{"ticker":"DUP3","market_cap":150e6,"quote_type":"EQUITY"}
              for _ in range(3)]
        rows.append({"ticker":"SAFE","market_cap":180e6,
                     "quote_type":"EQUITY"})
        self.assertEqual(mod.cohort(rows),["SAFE"])

    def test_universe_fingerprint_is_stable_and_changes_with_eligible_members(self):
        import hashlib
        def row(t, cap=150e6):
            return {"ticker": t, "market_cap": cap, "quote_type": "EQUITY"}
        now = datetime(2026, 7, 10, tzinfo=timezone.utc)
        first = mod.collect([row("B"), row("A")], Provider(), slot=0, budget=1, checked_at=now)
        reordered = mod.collect([row("A"), row("B")], Provider(), slot=0, budget=1, checked_at=now)
        changed = mod.collect([row("A"), row("C")], Provider(), slot=0, budget=1, checked_at=now)
        self.assertEqual(first["universe_tickers_sha256"],
                         hashlib.sha256(bytes([65, 10, 66])).hexdigest())
        self.assertEqual(first["universe_tickers_sha256"], reordered["universe_tickers_sha256"])
        self.assertNotEqual(first["universe_tickers_sha256"], changed["universe_tickers_sha256"])
        self.assertNotIn("universe_source_index_sha256", first)

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
    def test_fresh_provider_attempt_outcomes_are_reported_separately_from_rolling_coverage(self):
        class MixedProvider(Provider):
            def Ticker(self, ticker):
                if ticker == "B":
                    raise TimeoutError("simulated transient provider outage")
                if ticker == "C":
                    return type("T", (), {"fast_info": {"currency": None}})()
                return super().Ticker(ticker)
        rows = [{"ticker": x, "market_cap": 150e6, "quote_type": "EQUITY"}
                for x in ("A", "B", "C")]
        report = mod.collect(rows, MixedProvider(), slot=0, budget=3,
                             checked_at=datetime(2026, 7, 10, tzinfo=timezone.utc))
        self.assertEqual(report["provider_tickers_attempted"], 3)
        self.assertEqual(report["provider_attempt_status_counts"], {
            "currency_not_verified_usd": 1, "evaluable_ohlcv": 1, "provider_error": 1})
        self.assertEqual(report["provider_error_type_counts"], {"TimeoutError": 1})
        self.assertEqual(sum(report["provider_attempt_status_counts"].values()), 3)
        self.assertNotIn("simulated transient provider outage", str(report))

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

    def test_failed_provider_observations_retry_after_unseen_before_valid_refresh(self):
        from datetime import timedelta
        now=datetime(2026,11,9,12,tzinfo=timezone.utc)
        def record(ticker,status,age_hours):
            return {"ticker":ticker,"status":status,
                    "observation_checked_at":(now-timedelta(hours=age_hours)).isoformat()}
        previous={"schema":"vestra_breakout_lab_smallcap_ohlcv_research_v1",
                  "generated_at":now.isoformat(),
                  "observations":[
                      record("A","evaluable_ohlcv",10),
                      record("B","provider_error",2),
                      record("C","insufficient_ohlcv",3),
                      record("D","evaluable_ohlcv",20)]}
        names=["A","B","C","D","E","F"]
        self.assertEqual(mod.pick_research_tickers(names,0,2,previous,now),["E","F"])
        self.assertEqual(mod.pick_research_tickers(names,0,4,previous,now),["E","F","C","B"])
        self.assertEqual(mod.pick_research_tickers(names,0,6,previous,now),
                         ["E","F","C","B","D","A"])
        # A legacy record without status retains the old observed priority.
        previous["observations"].append({"ticker":"F",
            "observation_checked_at":now.isoformat()})
        self.assertEqual(mod.pick_research_tickers(names,0,2,previous,now),["E","C"])

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

    def test_future_dated_ohlcv_never_inflates_rolling_coverage(self):
        from datetime import timedelta
        now=datetime(2026,11,9,18,tzinfo=timezone.utc)
        schema="vestra_breakout_lab_smallcap_ohlcv_research_v1"
        previous={"schema":schema,"generated_at":now.isoformat(),
                  "observations":[
                      {"ticker":"FUTURE","status":"evaluable_ohlcv",
                       "observation_checked_at":(now+timedelta(minutes=30)).isoformat(),
                       "verified_prebreakout_setup":{"ticker":"FUTURE","score":99}},
                      {"ticker":"VALID","status":"evaluable_ohlcv",
                       "observation_checked_at":(now-timedelta(hours=4)).isoformat(),
                       "verified_prebreakout_setup":None}]}
        current={"schema":schema,"generated_at":now.isoformat(),
                 "universe_100m_500m_count":3,
                 "observations":[{"ticker":"CURRENT","status":"no_ohlcv"}]}
        report=mod.merge_slots(current,previous,now,
                               eligible_tickers={"FUTURE","VALID","CURRENT"})
        self.assertEqual({x["ticker"] for x in report["observations"]},
                         {"VALID","CURRENT"})
        self.assertEqual(report["evaluable_ohlcv"],1)
        self.assertEqual(report["not_observed"],1)
        self.assertEqual(report["distinct_tickers_observed"],2)
        self.assertEqual(report["signals"],[])
        self.assertEqual(report["universe_coverage_pct"],33.33)

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
