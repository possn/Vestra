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

        sec_registered = hygiene.classify("QCOM", {}, 804328)
        self.assertEqual(sec_registered["state"], "sec_registered_identity")
        self.assertEqual(sec_registered["evidence"], "sec_ticker_map")
        self.assertEqual(sec_registered["cik"], 804328)
        self.assertIsNone(sec_registered["quote_type"])

        unknown = hygiene.classify("ZZPST", {})
        self.assertEqual(unknown["state"], "unresolved")
        self.assertIsNone(unknown["quote_type"])

    def test_stronger_type_evidence_wins_over_sec_identity(self):
        row = {"ticker": "BITF", "quote_type": "EQUITY"}
        result = hygiene.classify("BITF", row, 123456)
        self.assertEqual(result["state"], "published_confirmed")
        self.assertEqual(result["evidence"], "stocks_snapshot")

        successor = hygiene.classify("BITF", {}, 123456)
        self.assertEqual(successor["state"], "corporate_successor")
        self.assertEqual(successor["quote_type"], "EQUITY")

    def test_sec_snapshot_confirms_identity_not_asset_type(self):
        audit = hygiene.build_audit(
            {"tickers": ["Q", "QBTS", "QCOM", "ZZPST"]},
            {"stocks": []},
            {"map": {"Q": 1, "QBTS": 2, "QCOM": 3}},
        )
        rows = {row["ticker"]: row for row in audit["rows"]}
        for ticker in ("Q", "QBTS", "QCOM"):
            self.assertEqual(rows[ticker]["state"], "sec_registered_identity")
            self.assertIsNone(rows[ticker]["quote_type"])
        self.assertEqual(rows["ZZPST"]["state"], "unresolved")
        self.assertEqual(audit["unresolved_tickers"], ["ZZPST"])
        self.assertEqual(audit["schema_version"], 2)

    def test_review_families_are_diagnostic_only(self):
        audit = hygiene.build_audit(
            {"tickers": ["BRADE", "BRADES", "VICO", "VICOR", "ZZPST"]},
            {"stocks": []},
            {"map": {}},
        )
        families = {row["family_key"]: row for row in audit["review_families"]}
        self.assertEqual(families["BRAD"]["tickers"], ["BRADE", "BRADES"])
        self.assertEqual(families["VICO"]["tickers"], ["VICO", "VICOR"])
        self.assertEqual(families["BRAD"]["action"], "review_only")
        self.assertIn("no_auto_merge", audit["mutation_policy"])
        self.assertIn("no_delete", audit["mutation_policy"])

    def test_sec_identity_index_rejects_invalid_entries(self):
        index = hygiene.sec_identity_index({"map": {"QCOM": 804328, "BAD": "x", "ZERO": 0}})
        self.assertEqual(index, {"QCOM": 804328})

    def test_duplicate_input_does_not_duplicate_rows(self):
        audit = hygiene.build_audit(
            {"tickers": ["BITF", "bitf", " AAPL "]},
            {"stocks": []},
            {"map": {}},
        )
        self.assertEqual(audit["extra_ticker_count"], 2)
        self.assertEqual([row["ticker"] for row in audit["rows"]], ["AAPL", "BITF"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
