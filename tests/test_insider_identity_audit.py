"""Regression tests for Form 4 persisted-cache provenance diagnostics."""
import unittest
from scripts.insider_identity_audit import analyze


def filing(cik="320193", accession="0001-26-000001", tx=None):
    if tx is None:
        tx=[{"issuer_cik":"0000320193","ticker":"AAPL","type":"buy","value":100}]
    return {"cik":cik,"issuer_cik":"0000320193","accession":accession,
            "raw_nonderivative_transactions":len(tx),"transactions":tx}


class InsiderIdentityAuditTests(unittest.TestCase):
    def test_valid_multiple_transactions_are_one_filing_and_two_operations(self):
        x=filing(tx=[{"issuer_cik":"320193"},{"issuer_cik":"0000320193"}])
        result=analyze({"filings":{"320193:0001-26-000001":x}})
        self.assertEqual(result["validated_rows"],1)
        self.assertEqual(result["validated_transactions"],2)
        self.assertEqual(result["multiple_transactions_in_one_filing_rows"],1)

    def test_unproven_legacy_is_unavailable_not_zero_buy(self):
        x=filing()
        x.pop("issuer_cik")
        result=analyze({"filings":{"320193:0001-26-000001":x}})
        self.assertEqual(result["legacy_or_missing_identity_rows"],1)
        self.assertEqual(result["validated_rows"],0)
        self.assertNotIn("confirmed_no_transactions",result)

    def test_mismatch_and_corrupt_key_are_counted_without_promotion(self):
        x=filing()
        x["issuer_cik"]="42"
        y=filing(accession="0001-26-000002")
        report=analyze({"filings":{"320193:0001-26-000001":x,
                                   "42:0001-26-000002":y}})
        self.assertEqual(report["issuer_or_cache_key_mismatch_rows"],2)
        self.assertEqual(report["validated_rows"],0)

    def test_missing_transaction_issuer_rejected_from_verified_counts(self):
        x=filing(tx=[{"ticker":"AAPL","value":100}])
        report=analyze({"filings":{"320193:0001-26-000001":x}})
        self.assertEqual(report["missing_or_mismatched_transaction_issuer_rows"],1)
        self.assertEqual(report["validated_transactions"],0)

    def test_invalid_document_state_is_explicitly_unavailable(self):
        self.assertEqual(analyze({})["state"],"unavailable")


if __name__=="__main__":
    unittest.main()
