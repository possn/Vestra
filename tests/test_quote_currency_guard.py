from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
def read(p): return (ROOT/p).read_text(encoding="utf-8")

class QuoteCurrencyGuardTests(unittest.TestCase):
    def test_broker_base_currency_is_not_treated_as_native_quote_currency(self):
        app=read("app.js")
        self.assertIn("asset.generatedFromBroker",app)
        self.assertIn('? ""\n    : (storedPriceCcy || storedAssetCcy)',app)
        self.assertIn("if (asset.generatedFromBroker && ccy) asset.priceCurrency = ccy",app)
        self.assertIn("Cotação suspeita: moeda ${quoteCcy} não coincide com ${assetCcy}",app)

    def test_manual_assets_keep_explicit_currency_guard(self):
        app=read("app.js")
        self.assertIn(": (storedPriceCcy || storedAssetCcy)",app)

    def test_poisoned_history_can_be_recovered_only_for_exact_broker_aliases(self):
        app=read("app.js")
        core=read("app-broker-parsing-core.js")
        self.assertIn('"FLR.US": Object.freeze({ ticker: "FLR"', app)
        self.assertIn('"SHA.DE": Object.freeze({ ticker: "SHA0.DE"', app)
        self.assertIn("brokerQuoteRecoveryMatches(asset, q, nextIdentity)", app)
        self.assertIn('"|FLR.US": "FLR"', core)
        self.assertIn('"|SHA.DE": "SHA0.DE"', core)

    def test_fresh_bundle_is_published(self):
        index=read("index.html")
        self.assertIn("app.js?v=20260930v2",index)
        sw=read("sw.js")
        self.assertIn('const CACHE_NAME = "vestra-cache-',sw)
        self.assertIn("staleWhileRevalidate",sw)
        self.assertIn('./market-live-overlay.js',sw)

if __name__=='__main__': unittest.main(verbosity=2)
