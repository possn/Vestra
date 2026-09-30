from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1]
def read(p): return (ROOT/p).read_text(encoding="utf-8")
class RemainingQuoteIdentityTests(unittest.TestCase):
    def test_current_identity_repairs_are_narrow(self):
        a=read("app.js")
        for token in ('"ENS": "ENS"','"MPW": "MPT"','"EDV": "EDV.TO"','"AMS": "AMS.SW"'):
            self.assertIn(token,a)
        generic=a[a.index('function toYahooTicker'):a.index('function toYahooTicker')+1200]
        self.assertNotIn('cryptoToYahoo(t)',generic)
    def test_split_guard_keeps_extremes_blocked(self):
        a=read("app.js")
        self.assertIn('const splitFactors = [2, 3, 4, 5, 10, 20]',a)
        self.assertIn('explicitIdentity && splitLike',a)
        self.assertIn('Cotação suspeita rejeitada',a)
    def test_crypto_candidates_use_crypto_identity_not_equity_identity(self):
        a=read("app.js")
        block=a[a.index("function isQuoteCandidateAcceptable"):a.index("async function fetchQuoteWithFallback")]
        self.assertIn('clsNorm === "cripto" || clsNorm === "crypto"', block)
        self.assertIn("cryptoToYahoo(rawCrypto)", block)
        self.assertIn("return !!cryptoExpected && cand === cryptoExpected", block)
        for ticker in ("STX", "ATOM", "NEAR", "POL"):
            self.assertIn(f'"{ticker}"', read("app-asset-identity.js"))

    def test_ib1t_native_quote_currency_is_repaired_narrowly(self):
        a=read("app.js")
        self.assertIn('"IB1T.DE": "EUR"', a)
        self.assertIn("QUOTE_NATIVE_CURRENCY_OVERRIDES[normalizedRawTicker]", a)
        self.assertIn("QUOTE_NATIVE_CURRENCY_OVERRIDES[resolvedQuoteTicker]", a)

    def test_fresh_bundle(self):
        self.assertIn('app.js?v=20260930v3',read('index.html'))
        sw=read('sw.js')
        self.assertIn('const CACHE_NAME = "vestra-cache-',sw)
        self.assertIn('staleWhileRevalidate',sw)
        self.assertIn('./market-live-overlay.js',sw)
if __name__=='__main__': unittest.main(verbosity=2)
