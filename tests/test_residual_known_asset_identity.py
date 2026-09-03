import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from known_asset_identity import exact_identity_override


class ResidualKnownAssetIdentityTests(unittest.TestCase):
    def test_agig_is_exact_equity_identity(self):
        row = exact_identity_override("AGIG")
        self.assertIsNotNone(row)
        self.assertEqual(row["quote_type"], "EQUITY")
        self.assertEqual(row["name"], "Abundia Global Impact Group Inc.")

    def test_qdve_and_qdvh_are_exact_etf_identities(self):
        qdve = exact_identity_override("QDVE.DE")
        qdvh = exact_identity_override("QDVH.DE")
        self.assertEqual(qdve["quote_type"], "ETF")
        self.assertEqual(qdve["isin"], "IE00B3WJKG14")
        self.assertEqual(qdvh["quote_type"], "ETF")
        self.assertEqual(qdvh["isin"], "IE00B4JNQZ49")

    def test_similar_symbols_are_not_guessed(self):
        for ticker in ("AGI", "AGIG.DE", "QDVE", "QDVH", "QDVE.L", "QDVH.L"):
            self.assertIsNone(exact_identity_override(ticker), ticker)


if __name__ == "__main__":
    unittest.main(verbosity=2)
