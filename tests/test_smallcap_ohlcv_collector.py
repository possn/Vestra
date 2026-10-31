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

    def test_rejects_invalid_limits(self):
        for slot,budget in ((-1,1),(0,0),(0,31)):
            with self.assertRaises(ValueError):mod.collect([],Provider(),slot,budget)
if __name__=="__main__":unittest.main()
