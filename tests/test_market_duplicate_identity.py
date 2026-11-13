"""Canonical shard selection must not turn a known ETF into an unknown equity."""
import unittest

from scripts.build_market_shards import choose_duplicate_ticker_row


class DuplicateIdentityTests(unittest.TestCase):
    def test_unresolved_duplicate_cannot_erase_known_etf(self):
        etf = {"ticker": "ISAG.L", "name": "ISHARES V PUBLIC LIMITED COMPAN",
               "quote_type": "ETF", "region": "Global"}
        unknown = {"ticker": "ISAG.L", "name": "ISAG.L",
                   "quote_type": None, "region": "United Kingdom"}
        self.assertIs(choose_duplicate_ticker_row(etf, unknown), etf)

    def test_later_explicit_identity_can_improve_unknown_record(self):
        old = {"ticker": "ABC", "quote_type": None}
        new = {"ticker": "ABC", "quote_type": "EQUITY"}
        self.assertIs(choose_duplicate_ticker_row(old, new), new)

    def test_later_typed_record_preserves_enrichment_precedence(self):
        old = {"ticker": "ABC", "quote_type": "EQUITY", "score": 40}
        new = {"ticker": "ABC", "quote_type": "EQUITY", "score": 65}
        self.assertIs(choose_duplicate_ticker_row(old, new), new)


if __name__ == "__main__":
    unittest.main()
