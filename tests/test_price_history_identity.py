from pathlib import Path
import sys
import types
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

if "yfinance" not in sys.modules:
    yf_stub = types.ModuleType("yfinance")
    yf_stub.download = lambda *args, **kwargs: None
    sys.modules["yfinance"] = yf_stub

if "requests" not in sys.modules:
    requests_stub = types.ModuleType("requests")
    requests_stub.get = lambda *args, **kwargs: None
    sys.modules["requests"] = requests_stub

import insider_prices


class PriceHistoryIdentityTests(unittest.TestCase):
    def test_crypto_internal_symbol_maps_to_yahoo_usd_pair(self):
        self.assertEqual(insider_prices._history_symbol("BTC.CC"), "BTC-USD")
        self.assertEqual(insider_prices._history_symbol("ETH.CC"), "ETH-USD")

    def test_official_successor_is_used_only_for_retrieval(self):
        self.assertEqual(insider_prices._history_symbol("BITF"), "KEEL")
        self.assertEqual(insider_prices._history_symbol("IINN"), "QTEX")
        self.assertEqual(insider_prices._history_symbol("MSFT"), "MSFT")

    def test_batch_results_are_mapped_back_to_canonical_ticker(self):
        original_batch = insider_prices._download_batch
        original_direct = insider_prices._download_direct
        calls = []
        try:
            def fake_batch(batch):
                calls.extend(batch)
                return {symbol: [{"date": "2026-09-01", "close": 1.0}, {"date": "2026-09-02", "close": 2.0}] for symbol in batch}

            insider_prices._download_batch = fake_batch
            insider_prices._download_direct = lambda ticker: []
            result = insider_prices.fetch_many(["BTC.CC", "BITF", "MSFT"], workers=1, batch_size=10)
        finally:
            insider_prices._download_batch = original_batch
            insider_prices._download_direct = original_direct

        self.assertEqual(set(calls), {"BTC-USD", "KEEL", "MSFT"})
        self.assertEqual(set(result), {"BTC.CC", "BITF", "MSFT"})
        self.assertEqual(result["BTC.CC"][-1]["close"], 2.0)
        self.assertEqual(result["BITF"][-1]["close"], 2.0)

    def test_direct_fallback_uses_retrieval_symbol_but_canonical_output_key(self):
        original_batch = insider_prices._download_batch
        original_direct = insider_prices._download_direct
        direct_calls = []
        try:
            insider_prices._download_batch = lambda batch: {symbol: [] for symbol in batch}

            def fake_direct(symbol):
                direct_calls.append(symbol)
                return [{"date": "2026-09-01", "close": 3.0}, {"date": "2026-09-02", "close": 4.0}]

            insider_prices._download_direct = fake_direct
            result = insider_prices.fetch_many(["ETH.CC"], workers=1, batch_size=10)
        finally:
            insider_prices._download_batch = original_batch
            insider_prices._download_direct = original_direct

        self.assertEqual(direct_calls, ["ETH-USD"])
        self.assertIn("ETH.CC", result)
        self.assertEqual(result["ETH.CC"][-1]["close"], 4.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
