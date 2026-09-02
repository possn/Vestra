import unittest

from scripts.known_asset_identity import exact_identity_override


class KnownAssetIdentityQsrBtTests(unittest.TestCase):
    def test_qsr_is_exact_equity_identity(self):
        row = exact_identity_override("QSR")
        self.assertIsNotNone(row)
        self.assertEqual(row["quote_type"], "EQUITY")
        self.assertEqual(row["name"], "Restaurant Brands International Inc.")

    def test_bt_dot_a_l_is_exact_equity_identity(self):
        row = exact_identity_override("BT.A.L")
        self.assertIsNotNone(row)
        self.assertEqual(row["quote_type"], "EQUITY")
        self.assertEqual(row["isin"], "GB0030913577")

    def test_similar_symbols_are_not_guessed(self):
        self.assertIsNone(exact_identity_override("BTAL"))
        self.assertIsNone(exact_identity_override("QSRS"))


if __name__ == "__main__":
    unittest.main()
