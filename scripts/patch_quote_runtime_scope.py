from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
app = ROOT / 'app.js'
text = app.read_text(encoding='utf-8')

anchor = '''function quoteSanityCheck(asset, q, priceEur, rawTicker, previousYahooTicker = "") {\n'''
helper = '''function getRawTickerForAssetSafe(asset) {\n  // Top-level, scope-safe mirror of the refresh-local raw ticker resolver.\n  // quoteSanityCheck runs outside refreshLiveQuotesCore and must never depend\n  // on helpers declared inside that function.\n  const tk = String((asset && asset.ticker) || "").trim();\n  if (tk && /^[A-Z0-9.\\-]{1,16}$/i.test(tk)) return tk.toUpperCase();\n\n  const notes = String((asset && asset.notes) || "");\n  const tagged = notes.match(/\\b(?:Ticker|Yahoo)=([A-Z0-9.\\-=^]{1,24})\\b/i);\n  if (tagged) return String(tagged[1] || "").trim().toUpperCase();\n\n  const nm = String((asset && asset.name) || "").trim();\n  if (nm && /^[A-Z0-9.\\-]{1,16}$/i.test(nm)) return nm.toUpperCase();\n  const bracketed = nm.match(/[\\[(]([A-Z0-9.-]{1,16}(?:\\.[A-Z]{1,4}|-[A-Z]{3})?)[\\])]/i);\n  if (bracketed) return String(bracketed[1] || "").trim().toUpperCase();\n  const venue = nm.match(/^([A-Z0-9.-]{1,16}\\.(?:US|DE|FR|PT|LS|MC|PA|AS|L|SW|TO|IR|CO|ST|OL|HE|AX|F|UK))(?:\\b|\\s|—|-)/i);\n  if (venue) return String(venue[1] || "").trim().toUpperCase();\n  return "";\n}\n\n'''
if 'function getRawTickerForAssetSafe(asset)' not in text:
    if anchor not in text:
        raise SystemExit('quoteSanityCheck anchor missing')
    text = text.replace(anchor, helper + anchor, 1)

old = 'const localIdentity = String(getRawTickerForAsset(asset) || "").trim().toUpperCase();'
new = 'const localIdentity = String(getRawTickerForAssetSafe(asset) || "").trim().toUpperCase();'
if old not in text:
    raise SystemExit('unsafe quoteSanityCheck reference missing')
text = text.replace(old, new, 1)
app.write_text(text, encoding='utf-8')

# Add a regression test that protects lexical scope, not just syntax.
test = ROOT / 'tests' / 'test_quote_runtime_scope.py'
test.write_text('''from pathlib import Path\nimport subprocess\nimport unittest\n\nROOT = Path(__file__).resolve().parents[1]\nAPP = ROOT / "app.js"\n\nclass QuoteRuntimeScopeTests(unittest.TestCase):\n    def test_app_syntax(self):\n        subprocess.run(["node", "--check", str(APP)], check=True, cwd=ROOT)\n\n    def test_quote_sanity_uses_top_level_scope_safe_ticker_resolver(self):\n        text = APP.read_text(encoding="utf-8")\n        helper = text.index("function getRawTickerForAssetSafe(asset)")\n        sanity = text.index("function quoteSanityCheck(asset")\n        refresh = text.index("async function refreshLiveQuotesCore(options = {})")\n        self.assertLess(helper, sanity)\n        self.assertLess(sanity, refresh)\n        block = text[sanity:refresh]\n        self.assertIn("getRawTickerForAssetSafe(asset)", block)\n        self.assertNotIn("getRawTickerForAsset(asset)", block)\n\n    def test_scope_safe_resolver_keeps_identity_rules(self):\n        text = APP.read_text(encoding="utf-8")\n        start = text.index("function getRawTickerForAssetSafe(asset)")\n        end = text.index("function quoteSanityCheck(asset", start)\n        block = text[start:end]\n        self.assertIn("Ticker|Yahoo", block)\n        self.assertIn("asset && asset.ticker", block)\n        self.assertIn("const bracketed", block)\n        self.assertIn("const venue", block)\n        self.assertIn('return ""', block)\n\nif __name__ == "__main__":\n    unittest.main(verbosity=2)\n''', encoding='utf-8')
