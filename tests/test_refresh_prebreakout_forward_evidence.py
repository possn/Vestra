import json
import sys
import tempfile
import unittest
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from refresh_prebreakout_forward_evidence import gather, completed_bars, completed_ohlcv

class ForwardPriceRefreshTests(unittest.TestCase):
    def archive(self,root):
        folder=root/"2026"/"slots"
        folder.mkdir(parents=True)
        slot={"schema":"vestra_prebreakout_v1","scan_slot_utc":2,
            "generated_at":"2026-10-15T14:10:00Z",
            "signals":[{"ticker":"AAA","stage":"compressão",
                        "source":"yahoo:daily_ohlcv","date":"2026-10-15"}]}
        (folder/"2026-10-15-slot2.json").write_text(json.dumps(slot))

    def frame(self):
        class Frame:
            empty=False
            columns=("Close",)
            def __init__(self):
                self.rows=[(datetime(2026,10,day),{"Close":float(value)})
                           for day,value in [(14,100),(15,101),(16,102),(17,105)]]
            def iterrows(self):
                return iter(self.rows)
        return Frame()

    def test_completed_only_and_adjusted_contract(self):
        rows=completed_bars(self.frame(),datetime(2026,10,17,tzinfo=timezone.utc).date())
        self.assertEqual(len(rows),3)
        self.assertEqual(rows[-1]["date"],"2026-10-16")

    def test_collects_real_archive_without_current_day_lookahead(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive=Path(tmp);self.archive(archive)
            requests=[]
            def download(ticker,**kwargs):
                requests.append((ticker,kwargs))
                return self.frame()
            result=gather(archive,download,datetime(2026,10,17,tzinfo=timezone.utc))
            self.assertEqual(result["cohort_count"],1)
            self.assertEqual(sorted(t for t,_ in requests),["AAA","SPY"])
            self.assertTrue(all(k["auto_adjust"] is True for _,k in requests))
            self.assertTrue(all(k["start"] <= "2026-07-20" for _,k in requests))  # enough prior bars for volume baseline
            self.assertTrue(all(k["multi_level_index"] is False for _,k in requests))
            self.assertEqual(result["outcomes"][0]["entry"],"2026-10-16")
            self.assertIsNone(result["outcomes"][0]["results"][5])
            self.assertEqual(result["price_metadata"]["completed_before_utc_date"],"2026-10-17")

    def test_optional_event_history_fails_closed_when_ohlcv_missing(self):
        self.assertIsNone(completed_ohlcv(self.frame(),datetime(2026,10,17,tzinfo=timezone.utc).date()))
        with tempfile.TemporaryDirectory() as tmp:
            archive=Path(tmp);self.archive(archive)
            result=gather(archive,lambda ticker,**kwargs:self.frame(),
                          datetime(2026,10,17,tzinfo=timezone.utc))
            self.assertEqual(result["price_metadata"]["complete_ohlcv"],0)
            events=result["breakout_event_evidence"]["events"]
            self.assertEqual(len(events),3)
            self.assertTrue(all(e["status"]=="missing_ohlcv" for e in events))
            self.assertTrue(all(e["event_date"] is None for e in events))
            h=result["breakout_event_evidence"]["coverage_by_horizon"]["5"]
            self.assertEqual(h["cohorts"],1)
            self.assertEqual(h["evaluable"],0)
            self.assertIsNone(h["breakout_rate"])
            self.assertEqual(h["by_status"]["missing_ohlcv"],1)
            self.assertEqual({key:h["post_confirmation_durability"]["3"][key] for key in ("observed","held_pivot","lost_pivot")},{"observed":0,"held_pivot":0,"lost_pivot":0})
            self.assertEqual(h["post_confirmation_durability"]["3"]["return_observations"],0)
            self.assertIsNone(h["post_confirmation_durability"]["3"]["mean_net_return_scenario"])
            self.assertEqual(h["post_confirmation_durability"]["10"]["observed"],0)

    def test_transient_download_failure_retries_once_without_backfill(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive=Path(tmp);self.archive(archive)
            calls={}
            def downloader(ticker,**kwargs):
                calls[ticker]=calls.get(ticker,0)+1
                self.assertTrue(kwargs["auto_adjust"])
                if ticker=="AAA" and calls[ticker]==1:
                    raise ConnectionError("transient")
                return self.frame()
            result=gather(archive,downloader,datetime(2026,10,17,tzinfo=timezone.utc))
            self.assertEqual(calls["AAA"],2)
            self.assertEqual(calls["SPY"],1)
            self.assertEqual(result["price_metadata"]["recovered_after_single_retry"],["AAA"])
            self.assertNotIn("AAA",result["price_metadata"]["failed"])

    def test_permanent_download_failure_never_synthesizes_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive=Path(tmp);self.archive(archive)
            calls={}
            def downloader(ticker,**kwargs):
                calls[ticker]=calls.get(ticker,0)+1
                if ticker=="AAA":raise ConnectionError("unavailable")
                return self.frame()
            result=gather(archive,downloader,datetime(2026,10,17,tzinfo=timezone.utc))
            self.assertEqual(calls["AAA"],2)
            self.assertEqual(result["price_metadata"]["failed"]["AAA"],"ConnectionError")
            self.assertEqual(result["price_metadata"]["recovered_after_single_retry"],[])
            self.assertEqual(result["breakout_event_evidence"]["coverage_by_horizon"]["5"]["evaluable"],0)

    def test_missing_spy_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive=Path(tmp);self.archive(archive)
            def downloader(ticker,**kwargs):
                if ticker=="SPY":raise ConnectionError("unavailable")
                return self.frame()
            with self.assertRaisesRegex(ValueError,"SPY"):gather(
                archive,downloader,datetime(2026,10,17,tzinfo=timezone.utc))

    def test_v2_scoped_same_provider_recovery_does_not_rewrite_legacy_ohlcv(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive=Path(tmp)
            self.archive(archive)
            folder=archive/"2026"/"slots"
            observed={
                "ticker":"AAA","evaluable":True,"last_session":"2026-11-23",
                "geometry_shadow":{"base_width_pass":False,"contractions_pass":False},
                "research_prebreakout_lineage":{"unbroken_prebreakout_position":True},
                "technical_evidence_shadow":{"status":"measured",
                    "atr14_pct":2.0,"volume9_to_prior40":1.1},
                "ma_structure_shadow":{"status":"measured","all_pass":True,
                    "price_order_pass":True,"three_slopes_rising":True,
                    "research_only_no_eligibility_or_score_effect":True},
                "asof_base_price_anchor":{
                    "schema":"vestra_prebreakout_asof_base_anchor_v1",
                    "session":"2026-11-23","adjusted_close":100.0,
                    "adjusted_pivot_high":110.0,"window_bars":40,
                    "reference_bars":39,
                    "historical_adjustment_factor_verified":False,
                    "research_only_no_eligibility_or_score_effect":True}
            }
            slot={"schema":"vestra_prebreakout_v1","scan_slot_utc":0,
                  "generated_at":"2026-11-24T02:26:00Z",
                  "research_observations":{
                      "point_in_time_capture_not_historical_reconstruction":True,
                      "rows":[observed]}}
            (folder/"2026-11-24-slot0.json").write_text(json.dumps(slot))
            class Frame:
                empty=False
                columns=("Close","High","Low","Volume")
                def __init__(self,rows):self.rows=rows
                def iterrows(self):return iter(self.rows)
            base=datetime(2026,9,15)
            history=[]
            for offset in range(70):
                dt=base+timedelta(days=offset)
                if dt.weekday()<5:
                    history.append((dt,{"Close":100.0,"High":102.0,
                                         "Low":98.0,
                                         "Volume":0.0 if offset==0 else 100.0}))
            calls=[]
            def downloader(ticker,**kwargs):
                calls.append((ticker,kwargs["start"]))
                rows=[x for x in history if x[0].date().isoformat()>=kwargs["start"]]
                return Frame(rows if ticker=="AAA" else [
                    (dt,dict(values,Volume=100.0)) for dt,values in rows])
            result=gather(archive,downloader,datetime(2026,11,24,tzinfo=timezone.utc))
            meta=result["price_metadata"]
            self.assertEqual(meta["v2_scoped_same_provider_probe_attempted"],["AAA"])
            self.assertEqual(meta["v2_scoped_complete_ohlcv_recovered"],["AAA"])
            self.assertEqual(meta["v2_scoped_not_recovered"],{})
            self.assertEqual([x for x in calls if x[0]=="AAA"],
                             [("AAA","2026-07-17"),("AAA","2026-09-24")])
            old=result["independent_ma_geometry_forward"]["groups"]["geometry_fail_ma_pass"]
            new=result["independent_ma_geometry_at_risk_forward"]["groups"]["geometry_fail_ma_pass"]
            self.assertEqual(old["by_horizon"]["5"]["unknown_reasons"],
                             {"independent_ohlcv_unavailable":1})
            self.assertEqual(new["by_horizon"]["5"]["unknown_reasons"],{"pending":1})
            self.assertEqual(new["by_horizon"]["5"]["matured_evaluable"],0)
            self.assertEqual(new["selected_tickers"],1)

    def test_invalid_prices_rejected(self):
        frame=self.frame()
        frame.rows[1][1]["Close"]=float("nan")
        with self.assertRaises(ValueError):
            completed_bars(frame,datetime(2026,10,17,tzinfo=timezone.utc).date())

if __name__=="__main__":unittest.main()
