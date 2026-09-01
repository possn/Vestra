import unittest

from scripts.coverage_audit import identity_state, retrieval_lane


class CoverageAuditSchemaTests(unittest.TestCase):
    def test_known_fund_types_are_not_equity_identity(self):
        for quote_type in ("ETF", "FUND", "MUTUALFUND", "CRYPTO"):
            with self.subTest(quote_type=quote_type):
                self.assertEqual(identity_state({"quote_type": quote_type}), "non_equity")

    def test_unknown_identity_never_routes_to_official_fundamentals(self):
        row = {
            "ticker": "UNKNOWN",
            "region": "United States",
            "quote_type": "",
            "roe": None,
            "data_sources": [],
        }
        self.assertEqual(retrieval_lane(row), "identity_unresolved")


if __name__ == "__main__":
    unittest.main()
