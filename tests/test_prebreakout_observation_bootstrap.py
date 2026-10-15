"""Verify published historical observations against all immutable eligible scan slots."""
import json
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
INDEX=ROOT/"data/prebreakout-observations.json"
ARCHIVE=ROOT/"data/prebreakout-history"

class PublishedObservationProvenance(unittest.TestCase):
    def test_index_matches_immutable_slots(self):
        index=json.loads(INDEX.read_text(encoding="utf-8"))
        self.assertEqual(index["schema"],"vestra_prebreakout_observations_v1")
        self.assertIs(index["historical_only"],True)
        now=datetime.fromisoformat(index["generated_at"].replace("Z","+00:00")).astimezone(timezone.utc)
        expected={}
        slots=0
        for path in sorted(ARCHIVE.glob("*/slots/*-slot*.json")):
            source=json.loads(path.read_text(encoding="utf-8"))
            stamp=datetime.fromisoformat(source["generated_at"].replace("Z","+00:00")).astimezone(timezone.utc)
            if not 0<=(now-stamp).total_seconds()/86400<=7 or source.get("schema")!="vestra_prebreakout_v1":
                continue
            slot=source.get("scan_slot_utc")
            if type(slot) is not int or slot!=stamp.hour//6 or path.name!=f"{stamp.date().isoformat()}-slot{slot}.json":
                continue
            self.assertIsInstance(source.get("signals"),list)
            slots+=1
            for signal in source["signals"]:
                if not isinstance(signal,dict):continue
                ticker=str(signal.get("ticker") or "").strip().upper()
                if not ticker or signal.get("stage") not in ("compressão","pré-breakout","confirmado") or signal.get("source")!="yahoo:daily_ohlcv":
                    continue
                try:score=float(signal["score"])
                except (KeyError,TypeError,ValueError):continue
                if not 0<=score<=100:continue
                observation={"ticker":ticker,"stage":signal["stage"],"score":score,
                    "signal_date":signal.get("date"),"observed_at":stamp.isoformat(),
                    "scan_slot_utc":slot,"current":False}
                if ticker not in expected or observation["observed_at"]>expected[ticker]["observed_at"]:
                    expected[ticker]=observation
        self.assertGreater(slots,0,"no eligible immutable scanner publication")
        self.assertEqual(index["slots_considered"],slots)
        ranked=sorted(expected.values(),key=lambda row:(-row["score"],row["ticker"]))[:100]
        self.assertEqual(index["observations"],ranked)

if __name__=="__main__":
    unittest.main()
