from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
IDENTITY = ROOT / "app-asset-identity.js"
INDEX = ROOT / "index.html"
TEST = ROOT / "tests" / "test_eu_quote_identity.py"
CACHE_TOKEN = "app-asset-identity.js?v=20260829v2"

MAPPINGS = {
    "DE000SHL1006": "SHL.DE",   # Siemens Healthineers AG, Xetra
    "DE000ENER6Y0": "ENR.DE",   # Siemens Energy AG, Xetra
    "FR0000125486": "DG.PA",    # VINCI SA, Euronext Paris
}


def upsert_isin_mapping(text: str, isin: str, yahoo: str) -> str:
    # Replace any stale/bare mapping wherever it already exists.
    pattern = re.compile(rf'"{re.escape(isin)}"\s*:\s*"[^"]+"')
    if pattern.search(text):
        return pattern.sub(f'"{isin}":"{yahoo}"', text)

    # Otherwise add to the curated exchange-aware section before the auto-added block.
    marker = "  // === AUTO-ADDED: T212 ISIN→ticker mappings (all 460 unique ISINs) ==="
    if marker not in text:
        raise SystemExit("asset identity marker not found")
    return text.replace(marker, f'  "{isin}":"{yahoo}",\n\n{marker}', 1)


identity = IDENTITY.read_text(encoding="utf-8")
for isin, yahoo in MAPPINGS.items():
    identity = upsert_isin_mapping(identity, isin, yahoo)

# Explicitly document why these venue-qualified mappings are mandatory.
comment_anchor = "const ISIN_YAHOO_MAP = {\n"
comment = (
    "const ISIN_YAHOO_MAP = {\n"
    "  // Exchange identity is authoritative for broker-imported instruments.\n"
    "  // Never allow a bare symbol to override an exact ISIN mapping: SHL/DG/ENR\n"
    "  // can resolve to unrelated instruments on other venues/providers.\n"
)
if "Exchange identity is authoritative for broker-imported instruments." not in identity:
    if comment_anchor not in identity:
        raise SystemExit("ISIN map anchor not found")
    identity = identity.replace(comment_anchor, comment, 1)

IDENTITY.write_text(identity, encoding="utf-8")

# Force iOS/PWA clients to request the repaired identity bundle without touching app.js.
index = INDEX.read_text(encoding="utf-8")
pattern = re.compile(r'app-asset-identity\.js(?:\?v=[^"\']+)?')
if not pattern.search(index):
    raise SystemExit("app-asset-identity loader not found in index.html")
index = pattern.sub(CACHE_TOKEN, index)
INDEX.write_text(index, encoding="utf-8")

# Keep existing bundle-generation regression tests aligned with the intentional cache bump.
for path in (ROOT / "tests").glob("test_*.py"):
    text = path.read_text(encoding="utf-8")
    text = re.sub(r'app-asset-identity\.js\?v=[0-9A-Za-z._-]+', CACHE_TOKEN, text)
    path.write_text(text, encoding="utf-8")

TEST.write_text(
    '''from pathlib import Path\nimport re\nimport unittest\n\nROOT = Path(__file__).resolve().parents[1]\n\nclass EuQuoteIdentityTests(unittest.TestCase):\n    def test_critical_european_isins_are_exchange_qualified(self):\n        identity = (ROOT / "app-asset-identity.js").read_text(encoding="utf-8")\n        expected = {\n            "DE000SHL1006": "SHL.DE",\n            "DE000ENER6Y0": "ENR.DE",\n            "FR0000125486": "DG.PA",\n        }\n        for isin, ticker in expected.items():\n            self.assertRegex(identity, rf'"{isin}"\\s*:\\s*"{re.escape(ticker)}"')\n\n    def test_no_bare_symbol_regression_for_these_isins(self):\n        identity = (ROOT / "app-asset-identity.js").read_text(encoding="utf-8")\n        for isin, bare in (("DE000SHL1006", "SHL"), ("DE000ENER6Y0", "ENR"), ("FR0000125486", "DG")):\n            self.assertNotRegex(identity, rf'"{isin}"\\s*:\\s*"{bare}"\\s*[,}}]')\n\n    def test_identity_bundle_cachebuster_is_fresh(self):\n        index = (ROOT / "index.html").read_text(encoding="utf-8")\n        self.assertIn("app-asset-identity.js?v=20260829v2", index)\n\nif __name__ == "__main__":\n    unittest.main(verbosity=2)\n''',
    encoding="utf-8",
)

print("EU quote identity repair applied")
