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
    def test_rejects_invalid_limits(self):
        for slot,budget in ((-1,1),(0,0),(0,31)):
            with self.assertRaises(ValueError):mod.collect([],Provider(),slot,budget)
if __name__=="__main__":unittest.main()
