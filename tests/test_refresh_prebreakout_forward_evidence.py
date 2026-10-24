import json
import sys
import tempfile
import unittest
from datetime import datetime,timezone
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

    def test_missing_spy_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            archive=Path(tmp);self.archive(archive)
            def downloader(ticker,**kwargs):
                if ticker=="SPY":raise ConnectionError("unavailable")
                return self.frame()
            with self.assertRaisesRegex(ValueError,"SPY"):gather(
                archive,downloader,datetime(2026,10,17,tzinfo=timezone.utc))

    def test_invalid_prices_rejected(self):
        frame=self.frame()
        frame.rows[1][1]["Close"]=float("nan")
        with self.assertRaises(ValueError):
            completed_bars(frame,datetime(2026,10,17,tzinfo=timezone.utc).date())

if __name__=="__main__":unittest.main()
