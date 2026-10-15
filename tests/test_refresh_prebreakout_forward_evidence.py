import json
import sys
import tempfile
import unittest
from datetime import datetime,timezone
from pathlib import Path
import pandas as pd

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from refresh_prebreakout_forward_evidence import gather, completed_bars

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
        return pd.DataFrame({"Close":[100.0,101.0,102.0,105.0]},
              index=pd.to_datetime(["2026-10-14","2026-10-15","2026-10-16","2026-10-17"]))

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
            self.assertEqual(result["outcomes"][0]["entry"],"2026-10-16")
            self.assertIsNone(result["outcomes"][0]["results"][5])
            self.assertEqual(result["price_metadata"]["completed_before_utc_date"],"2026-10-17")

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
        frame.loc[frame.index[1],"Close"]=float("nan")
        with self.assertRaises(ValueError):
            completed_bars(frame,datetime(2026,10,17,tzinfo=timezone.utc).date())

if __name__=="__main__":unittest.main()
