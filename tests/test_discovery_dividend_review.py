"""Source-attested dividend review never trusts Yahoo vendor data alone."""
import datetime as dt
import unittest

from scripts.discovery_dividend_review import domain_matches, prepare_review


def candidate():
    return {
        "ticker": "AAA", "ex_date": "2026-09-01",
        "amount_per_share": 0.25, "currency_hint": "USD",
        "status": "pending_issuer_verification",
        "issuer_source_url": None, "payment_date": None,
    }


def approval(**fields):
    base = {
        "ticker": "AAA", "ex_date": "2026-09-01",
        "amount_per_share": 0.25, "currency": "USD",
        "payment_date": "2026-09-15",
        "issuer_source_url": "https://investors.issuer-example.com/news/dividend",
        "reviewed_by": "Finance reviewer",
        "reviewed_at": "2026-09-16",
    }
    base.update(fields)
    return base


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.report = {
            "schema_version": 1, "status": "candidates_only_unverified",
            "candidates": [candidate()],
        }
        self.domains = {
            "schema_version": 1, "domains": {"AAA": ["issuer-example.com"]},
        }
        self.ledger = {"schema_version": 1, "events": []}
        self.today = dt.date(2026, 11, 6)

    def review(self, approvals):
        return prepare_review(approvals, self.report, self.domains,
                              self.ledger, self.today)

    def test_source_attested_review_promotes_only_exact_candidate(self):
        output = self.review([approval()])
        self.assertEqual(len(output["events"]), 1)
        event = output["events"][0]
        self.assertEqual(event["status"], "confirmed")
        self.assertEqual(event["reviewed_at"], "2026-09-16")
        self.assertEqual(event["verification_method"], "manual_issuer_document")

    def test_non_issuer_or_lookalike_domain_rejected(self):
        for url in (
            "https://finance.yahoo.com/quote/AAA",
            "https://issuer-example.com.attacker.net/news",
            "http://investors.issuer-example.com/news",
            "https://issuer-example.com@attacker.net/dividend",
            "https://issuer-example.com:8443/news",
        ):
            with self.subTest(url=url):
                self.assertFalse(domain_matches(url, ["issuer-example.com"]))
                with self.assertRaises(ValueError):
                    self.review([approval(issuer_source_url=url)])

    def test_missing_primary_domain_registry_rejected(self):
        self.domains["domains"] = {}
        with self.assertRaisesRegex(ValueError, "independently registered"):
            self.review([approval()])

    def test_vendor_only_cannot_verify_without_manual_evidence(self):
        for change in (
            {"issuer_source_url": None},
            {"reviewed_by": ""},
            {"payment_date": "2026-08-15"},
            {"payment_date": "2026-12-15"},
            {"reviewed_at": "2026-12-17"},
            {"currency": "EUR"},
            {"amount_per_share": 0.5},
        ):
            with self.subTest(change=change), self.assertRaises(ValueError):
                self.review([approval(**change)])

    def test_duplicate_review_and_duplicate_verified_event_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate review"):
            self.review([approval(), approval()])
        self.ledger = self.review([approval()])
        with self.assertRaisesRegex(ValueError, "already verified"):
            self.review([approval()])

    def test_unverified_source_report_cannot_promote(self):
        self.report["candidates"][0]["status"] = "confirmed"
        with self.assertRaisesRegex(ValueError, "non-pending"):
            self.review([approval()])


if __name__ == "__main__":
    unittest.main()
