import importlib.util
import math
import json
import tempfile
import unittest
from datetime import date, timedelta, datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("prebreakout",ROOT/"scripts/refresh_prebreakout_scanner.py")
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class PrebreakoutDataTests(unittest.TestCase):
    def bars(self,trend=True):
        today=date.today()
        rows=[]
        for i in range(260):
            base=50+(0.075*i if trend else -0.04*i)
            amp=5 if 160<=i<200 else 1.8 if 200<=i<220 else 1.0 if 220<=i<240 else .30
            wiggle=amp*math.sin(i*1.4)
            c=base+wiggle
            vol=60000 if i>=250 else 100000
            rows.append({"date":(today-timedelta(days=259-i)).isoformat(),
                         "close":c,"high":c+amp*.3,"low":c-amp*.3,"volume":vol})
        rows[-1]["volume"]=180000
        return rows

    def test_atr_and_liquidity_diagnostics_are_as_of_bar(self):
        rows=self.bars()
        candidate=mod.scan_bars("TEST",rows)
        self.assertIsNotNone(candidate)
        q=candidate["quantitativeDiagnostics"]
        self.assertGreater(q["atrPct14"],0)
        self.assertGreater(q["atrContractionRatio"],0)
        self.assertGreater(q["averageDollarVolume20"],0)
        older=mod.scan_bars("TEST",rows[:-1])
        self.assertIsNotNone(older)
        self.assertNotEqual(q["atrPct14"],older["quantitativeDiagnostics"]["atrPct14"])
        missing=self.bars()
        missing[-5]["volume"]=None
        result=mod.scan_bars("TEST",missing)
        if result is not None:
            self.assertIsNone(result["quantitativeDiagnostics"]["averageDollarVolume20"])

    def test_unfinished_utc_daily_bar_is_excluded_from_live_scan(self):
        today=date(2026,10,15)
        bars=[{"date":"2026-10-13","close":1},{"date":"2026-10-14","close":2},
              {"date":"2026-10-15","close":1000}]
        finished=mod.completed_sessions(bars,today)
        self.assertEqual([r["date"] for r in finished],["2026-10-13","2026-10-14"])
        self.assertEqual(mod.completed_sessions(bars,date(2026,10,16)),bars)

    def test_eligible_coverage_deduplicates_symbols_and_excludes_funds(self):
        stocks=[
            {"ticker":"AAA","quote_type":"EQUITY","market_cap":900_000_000},
            {"ticker":"aaa","quote_type":"EQUITY","market_cap":900_000_000},
            {"ticker":"BBB","quote_type":"ETF","market_cap":900_000_000},
            {"ticker":"CCC","quote_type":"EQUITY","market_cap":499_999_999},
            {"ticker":"DDD","quote_type":"EQUITY","market_cap":float("nan")},
            {"ticker":"EEE","quote_type":"EQUITY","market_cap":500_000_000}
        ]
        self.assertEqual(mod.eligible_universe_size(stocks),2)

    def test_scan_slots_rotate_across_a_broader_universe(self):
        stocks=[{"ticker":f"T{i:04d}","quote_type":"EQUITY","market_cap":10_000_000_000-i}
                for i in range(700)]
        scan0=mod.candidates(stocks,date(2026,10,14),0)
        scan1=mod.candidates(stocks,date(2026,10,14),1)
        scan2=mod.candidates(stocks,date(2026,10,14),2)
        self.assertEqual(len(scan0),150)
        self.assertEqual(scan0[:40],scan1[:40])
        self.assertTrue(set(scan0[40:]).isdisjoint(scan1[40:]))
        self.assertTrue(set(scan1[40:]).isdisjoint(scan2[40:]))
        with self.assertRaises(ValueError):mod.candidates(stocks,date(2026,10,14),4)

    def test_watchlist_rechecks_old_signals_without_expanding_scan_budget(self):
        stocks=[{"ticker":f"T{i:04d}","quote_type":"EQUITY","market_cap":10_000_000_000-i} for i in range(700)]
        day=date(2026,10,15)
        normal=mod.candidates(stocks,day,1)
        tracked="T0670"
        self.assertNotIn(tracked,normal)
        chosen=mod.candidates(stocks,day,1,[tracked,"T0001",tracked,"NOT-IN-UNIVERSE"])
        self.assertEqual(len(chosen),150)
        self.assertEqual(chosen[:40],normal[:40])
        self.assertEqual(chosen[40],tracked)
        self.assertEqual(len(chosen),len(set(chosen)))

    def test_published_watchlist_is_time_bounded_and_historical_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"observations.json"
            when=datetime(2026,10,15,12,tzinfo=timezone.utc)
            rows=[{"ticker":"AAA","stage":"compressão","current":False,"observed_at":"2026-10-15T07:00:00Z"},
                  {"ticker":"FAKE","stage":"confirmado","current":True,"observed_at":"2026-10-15T07:00:00Z"},
                  {"ticker":"OLD","stage":"pré-breakout","current":False,"observed_at":"2026-10-01T07:00:00Z"}]
            path.write_text(json.dumps({"schema":"vestra_prebreakout_observations_v1",
                "historical_only":True,"generated_at":"2026-10-15T11:00:00Z","observations":rows}))
            self.assertEqual(mod.watched_tickers(when,path),["AAA"])
            self.assertEqual(mod.watched_tickers(datetime(2026,10,25,tzinfo=timezone.utc),path),[])
            path.unlink()
            self.assertEqual(mod.watched_tickers(when,path),[])

    def test_requires_200_day_ma_and_rising_alignment(self):
        self.assertIsNone(mod.scan_bars("TEST",self.bars()[:190]))
        self.assertIsNone(mod.scan_bars("TEST",self.bars(trend=False)))

    def test_real_shrinking_base_can_be_scored(self):
        rows=self.bars()
        result=mod.scan_bars("TEST",rows)
        self.assertIsNotNone(result)
        self.assertEqual(result["source"],"yahoo:daily_ohlcv")
        self.assertGreater(result["sma50"],result["sma200"])
        self.assertGreater(result["priorWidthPct"],result["widthPct"])
        self.assertIn(result["stage"],("compressão","pré-breakout"))
        self.assertTrue(result["vcpConfirmed"])
        self.assertTrue(result["volumeDry"])

    def test_breakout_quality_is_observation_not_extra_alpha(self):
        rows=self.bars()
        baseline=mod.scan_bars("TEST",rows)
        self.assertIsNotNone(baseline)
        self.assertIn("breakoutCloseLocationPct",baseline)
        self.assertIn("breakoutVolumeRatio",baseline)
        self.assertIn("breakoutExtensionPct",baseline)
        self.assertIsNotNone(baseline["breakoutVolumeRatio"])
        self.assertGreater(baseline["breakoutVolumeRatio"],0)
        self.assertEqual(baseline["stage"],mod.scan_bars("TEST",rows)["stage"])

    def test_absent_today_volume_does_not_invent_breakout_volume_ratio(self):
        rows=self.bars()
        rows[-1]["volume"]=None
        observed=mod.scan_bars("TEST",rows)
        self.assertIsNotNone(observed)
        self.assertIsNone(observed["breakoutVolumeRatio"])
        self.assertFalse(observed["volumeConfirmed"])

    def test_stale_data_are_not_included(self):
        rows=self.bars()
        for row in rows:
            row["date"]=(date.fromisoformat(row["date"])-timedelta(days=60)).isoformat()
        self.assertIsNone(mod.scan_bars("TEST",rows))

    def test_out_of_order_history_rejected(self):
        rows=self.bars()
        rows[-1]["date"]=rows[-2]["date"]
        self.assertIsNone(mod.scan_bars("TEST",rows))

    def test_missing_high_or_low_does_not_fabricate_structure(self):
        rows=self.bars()
        rows[-1]["high"]=None
        self.assertIsNone(mod.scan_bars("TEST",rows))

    def test_high_volume_without_three_contractions_is_rejected(self):
        rows=self.bars()
        for i in range(240,260):
            rows[i]["high"]=rows[i]["close"]+6
            rows[i]["low"]=rows[i]["close"]-6
        self.assertIsNone(mod.scan_bars("TEST",rows))

    def test_breakout_requires_strong_close_near_session_high(self):
        self.assertTrue(mod.strong_breakout_close(102, 100, 101, 102.5, 99, True))
        self.assertFalse(mod.strong_breakout_close(102, 100, 101, 110, 99, True))
        self.assertFalse(mod.strong_breakout_close(102, 100, 101, 102.5, 99, False))
        self.assertFalse(mod.strong_breakout_close(102, 103, 101, 102.5, 99, True))
        self.assertFalse(mod.strong_breakout_close(102, 100, 101, 102, 102, True))

    def test_prebreakout_rejects_close_above_previous_resistance(self):
        rows=self.bars()
        pivot=max(r["high"] for r in rows[-40:-1])
        rows[-1]["close"]=pivot*1.01
        rows[-1]["high"]=rows[-1]["close"]*1.001
        rows[-1]["low"]=rows[-1]["close"]*.995
        self.assertIsNone(mod.scan_bars("TEST",rows),
                          "already crossed pivot must not appear as pre-breakout")

    def test_prebreakout_rejects_intraday_failed_breakout(self):
        rows=self.bars()
        pivot=max(r["high"] for r in rows[-40:-1])
        rows[-1]["high"]=max(rows[-1]["high"],pivot*1.012)
        self.assertIsNone(mod.scan_bars("TEST",rows),
                          "prior failed breakout is not an untouched VCP base")

    def test_unverified_volume_never_confirms_breakout(self):
        rows=self.bars()
        rows[-1]["volume"]=None
        result=mod.scan_bars("TEST",rows)
        self.assertIsNotNone(result)
        self.assertFalse(result["volumeConfirmed"])
        self.assertNotEqual(result["stage"],"confirmado")

if __name__=="__main__":
    unittest.main()
