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
    def test_fresh_bundle(self):
        self.assertIn('app.js?v=20260827v20',read('index.html'))
        sw=read('sw.js')
        self.assertIn('Vestra Service Worker v10.9',sw)
        self.assertIn('vestra-cache-v123',sw)
if __name__=='__main__': unittest.main(verbosity=2)
