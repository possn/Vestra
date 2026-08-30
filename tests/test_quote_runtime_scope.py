from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app.js"

class QuoteRuntimeScopeTests(unittest.TestCase):
    def test_app_syntax(self):
        subprocess.run(["node", "--check", str(APP)], check=True, cwd=ROOT)

    def test_quote_sanity_uses_top_level_scope_safe_ticker_resolver(self):
        text = APP.read_text(encoding="utf-8")
        helper = text.index("function getRawTickerForAssetSafe(asset)")
        sanity = text.index("function quoteSanityCheck(asset")
        refresh = text.index("async function refreshLiveQuotesCore(options = {})")
        self.assertLess(helper, sanity)
        self.assertLess(sanity, refresh)
        block = text[sanity:refresh]
        self.assertIn("getRawTickerForAssetSafe(asset)", block)
        self.assertNotIn("getRawTickerForAsset(asset)", block)

    def test_scope_safe_resolver_keeps_identity_rules(self):
        text = APP.read_text(encoding="utf-8")
        start = text.index("function getRawTickerForAssetSafe(asset)")
        end = text.index("function quoteSanityCheck(asset", start)
        block = text[start:end]
        self.assertIn("Ticker|Yahoo", block)
        self.assertIn("asset && asset.ticker", block)
        self.assertIn("const bracketed", block)
        self.assertIn("const venue", block)
        self.assertIn('return ""', block)

if __name__ == "__main__":
    unittest.main(verbosity=2)
