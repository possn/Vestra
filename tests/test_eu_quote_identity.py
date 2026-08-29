from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]

class EuQuoteIdentityTests(unittest.TestCase):
    def test_critical_european_isins_are_exchange_qualified(self):
        identity = (ROOT / "app-asset-identity.js").read_text(encoding="utf-8")
        expected = {
            "DE000SHL1006": "SHL.DE",
            "DE000ENER6Y0": "ENR.DE",
            "FR0000125486": "DG.PA",
        }
        for isin, ticker in expected.items():
            self.assertRegex(identity, rf'"{isin}"\s*:\s*"{re.escape(ticker)}"')

    def test_no_bare_symbol_regression_for_these_isins(self):
        identity = (ROOT / "app-asset-identity.js").read_text(encoding="utf-8")
        for isin, bare in (("DE000SHL1006", "SHL"), ("DE000ENER6Y0", "ENR"), ("FR0000125486", "DG")):
            self.assertNotRegex(identity, rf'"{isin}"\s*:\s*"{bare}"\s*[,}}]')

    def test_identity_bundle_cachebuster_is_fresh(self):
        index = (ROOT / "index.html").read_text(encoding="utf-8")
        self.assertIn("app-asset-identity.js?v=20260829v2", index)

if __name__ == "__main__":
    unittest.main(verbosity=2)
