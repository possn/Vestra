"""Congress holdings must not collapse BRK.A and BRK.B identities."""
import unittest
from unittest.mock import patch

from scripts import congress


class CongressShareClassTests(unittest.TestCase):
    def test_us_market_suffix_is_removed_without_losing_share_class(self):
        self.assertEqual(congress._us_ticker_identity("brk.b.us"), "BRK.B")
        self.assertEqual(congress._us_ticker_identity("brk-b"), "BRK.B")
        self.assertEqual(congress._us_ticker_identity("brk.a"), "BRK.A")
        self.assertEqual(congress._us_ticker_identity("msft.us"), "MSFT")

    def test_share_classes_never_cross_assign_disclosures(self):
        trades = [
            {"ticker": "BRK.A", "member": "A", "transaction_date": "2026-11-02", "type": "Purchase"},
            {"ticker": "BRK.B", "member": "B", "transaction_date": "2026-11-02", "type": "Sale"},
            {"ticker": "MSFT", "member": "C", "transaction_date": "2026-11-03", "type": "Purchase"},
        ]
        with patch.object(congress, "_load_snapshot", return_value={"trades": trades, "source": "fixture"}):
            result = congress.fetch_congress_for_universe(["BRK.A", "MSFT.US"])
        self.assertEqual(set(result), {"BRK.A", "MSFT"})
        self.assertEqual(result["BRK.A"][0]["member"], "A")
        self.assertEqual(result["MSFT"][0]["member"], "C")
        with patch.object(congress, "_load_snapshot", return_value={"trades": trades}):
            result_b = congress.fetch_congress_for_universe(["BRK.B.US"])
        self.assertEqual(set(result_b), {"BRK.B"})
        self.assertEqual(result_b["BRK.B"][0]["member"], "B")


if __name__ == "__main__":
    unittest.main()
