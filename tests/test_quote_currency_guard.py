from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
def read(p): return (ROOT/p).read_text(encoding="utf-8")

class QuoteCurrencyGuardTests(unittest.TestCase):
    def test_broker_base_currency_is_not_treated_as_native_quote_currency(self):
        app=read("app.js")
        self.assertIn("storedPriceCcy !== portfolioCcy",app)
        self.assertIn("asset.generatedFromBroker",app)
        self.assertIn("if (asset.generatedFromBroker && ccy) asset.priceCurrency = ccy",app)
        self.assertIn("Cotação suspeita: moeda ${quoteCcy} não coincide com ${assetCcy}",app)

    def test_manual_assets_keep_explicit_currency_guard(self):
        app=read("app.js")
        self.assertIn(": (storedPriceCcy || storedAssetCcy)",app)

    def test_fresh_bundle_is_published(self):
        index=read("index.html")
        self.assertIn("app.js?v=20260827v20",index)
        sw=read("sw.js")
        self.assertIn("Vestra Service Worker v10.9",sw)
        self.assertIn("vestra-cache-v123",sw)

if __name__=='__main__': unittest.main(verbosity=2)
