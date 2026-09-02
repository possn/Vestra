from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import extra_ticker_hygiene as hygiene


class ExtraTickerHygieneTests(unittest.TestCase):
    def test_exact_evidence_states_are_separate(self):
        published = {"ticker": "AAPL", "quote_type": "EQUITY"}
        self.assertEqual(hygiene.classify("AAPL", published)["state"], "published_confirmed")

        successor = hygiene.classify("BITF", {})
        self.assertEqual(successor["state"], "corporate_successor")
        self.assertEqual(successor["retrieval_ticker"], "KEEL")
        self.assertEqual(successor["quote_type"], "EQUITY")

        known = hygiene.classify("SPYL.DE", {})
        self.assertEqual(known["state"], "known_identity")
        self.assertEqual(known["quote_type"], "ETF")

        unknown = hygiene.classify("ZZPST", {})
        self.assertEqual(unknown["state"], "unresolved")
        self.assertIsNone(unknown["quote_type"])

    def test_published_current_type_wins_over_historical_evidence(self):
        row = {"ticker": "BITF", "quote_type": "EQUITY"}
        result = hygiene.classify("BITF", row)
        self.assertEqual(result["state"], "published_confirmed")
        self.assertEqual(result["evidence"], "stocks_snapshot")

    def test_review_families_are_diagnostic_only(self):
        audit = hygiene.build_audit(
            {"tickers": ["BRADE", "BRADES", "VICO", "VICOR", "ZZPST"]},
            {"stocks": []},
        )
        families = {row["family_key"]: row for row in audit["review_families"]}
        self.assertEqual(families["BRAD"]["tickers"], ["BRADE", "BRADES"])
        self.assertEqual(families["VICO"]["tickers"], ["VICO", "VICOR"])
        self.assertEqual(families["BRAD"]["action"], "review_only")
        self.assertIn("no_auto_merge", audit["mutation_policy"])
        self.assertIn("no_delete", audit["mutation_policy"])

    def test_duplicate_input_does_not_duplicate_rows(self):
        audit = hygiene.build_audit({"tickers": ["BITF", "bitf", " AAPL "]}, {"stocks": []})
        self.assertEqual(audit["extra_ticker_count"], 2)
        self.assertEqual([row["ticker"] for row in audit["rows"]], ["AAPL", "BITF"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
