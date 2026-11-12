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


    def test_future_and_malformed_trade_dates_never_enter_dossiers(self):
        from datetime import datetime, timedelta, timezone
        today = datetime.now(timezone.utc).date()
        valid = (today - timedelta(days=2)).isoformat()
        future = (today + timedelta(days=1)).isoformat()
        trades = [
            {"ticker": "MSFT", "member": "Valid", "transaction_date": valid,
             "disclosure_date": valid, "type": "buy"},
            {"ticker": "MSFT", "member": "Future trade", "transaction_date": future,
             "disclosure_date": valid, "type": "buy"},
            {"ticker": "MSFT", "member": "Future disclosure", "transaction_date": valid,
             "disclosure_date": future, "type": "buy"},
            {"ticker": "MSFT", "member": "Invalid trade", "transaction_date": "2026-02-30",
             "type": "buy"},
            {"ticker": "MSFT", "member": "Week-date not canonical",
             "transaction_date": "2026-W45-1", "type": "buy"},
            {"ticker": "MSFT", "member": "Invalid disclosure", "transaction_date": valid,
             "disclosure_date": "not-a-date", "type": "buy"},
        ]
        with patch.object(congress, "_load_snapshot", return_value={"trades": trades}):
            mapped = congress.fetch_congress_for_universe(["MSFT"])
        self.assertEqual([trade["member"] for trade in mapped["MSFT"]], ["Valid"])

    def test_disclosure_preceding_transaction_is_not_smart_money_evidence(self):
        from datetime import date, timedelta
        tx=(date.today()-timedelta(days=3)).isoformat()
        premature=(date.today()-timedelta(days=4)).isoformat()
        trades=[
            {"ticker":"DIS","member":"Invalid chronology","transaction_date":tx,
             "disclosure_date":premature,"type":"Purchase"},
            {"ticker":"DIS","member":"Valid chronology","transaction_date":tx,
             "disclosure_date":tx,"type":"Purchase"},
        ]
        with patch.object(congress,"_load_snapshot",return_value={"trades":trades}):
            result=congress.fetch_congress_for_universe(["DIS"])
        self.assertEqual([x["member"] for x in result["DIS"]],["Valid chronology"])

    def test_only_official_disclosure_links_are_exposed(self):
        official = "https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/2026/20035788.pdf"
        cases = [
            (official, official),
            ("  " + official + "  ", official),
            ("https://efdsearch.senate.gov/search/view/ptr/abc/", 
             "https://efdsearch.senate.gov/search/view/ptr/abc/"),
            ("http://disclosures-clerk.house.gov/public_disc/ptr-pdfs/2026/20035788.pdf", ""),
            ("https://disclosures-clerk.house.gov.evil.com/public_disc/ptr-pdfs/2026/20035788.pdf", ""),
            ("https://evil.example/stock-act/filing.pdf", ""),
            ("https://disclosures-clerk.house.gov/public_disc/ptr-pdfs/2026/20035788.pdf?redirect=https://evil.example", ""),
            ("https://disclosures-clerk.house.gov@evil.example/public_disc/ptr-pdfs/2026/20035788.pdf", ""),
            ("javascript:alert(1)", ""),
            (None, ""),
        ]
        for supplied,expected in cases:
            with self.subTest(url=supplied):
                self.assertEqual(congress._trusted_filing_url(supplied), expected)

    def test_untrusted_document_link_is_hidden_without_fabricating_trade(self):
        from datetime import date, timedelta
        d = (date.today()-timedelta(days=2)).isoformat()
        rows=[
            {"ticker":"MSFT", "member":"Member", "transaction_date":d,
             "disclosure_date":d, "type":"buy",
             "filing_url":"https://evil.example/stock-act.pdf"},
        ]
        with patch.object(congress, "_load_snapshot", return_value={"trades":rows}):
            mapped = congress.fetch_congress_for_universe(["MSFT"])
        self.assertEqual(len(mapped["MSFT"]),1)
        self.assertEqual(mapped["MSFT"][0]["filing_portal"], "")

    def test_explicit_data_not_current_prevents_dossier_evidence(self):
        from datetime import date
        today = date.today().isoformat()
        payload = {"schema_version": 2, "data_current": False,
                   "newest_disclosure": today, "trades": []}
        self.assertFalse(congress._is_fresh(payload))
        payload["data_current"] = True
        self.assertTrue(congress._is_fresh(payload))


if __name__ == "__main__":
    unittest.main()
