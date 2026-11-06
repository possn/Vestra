"""Production evidence contract: first issuer-verified dividend batch is reproducible."""
import datetime as dt
import json
import unittest
from pathlib import Path

from scripts.discovery_dividend_evidence import validated_events
from scripts.discovery_dividend_review import prepare_review, domain_matches

ROOT = Path(__file__).resolve().parents[1]


class FirstVerifiedDividendBatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.candidates = json.loads(
            (ROOT / "data" / "dividend_event_candidates.json").read_text(encoding="utf-8")
        )
        cls.issuers = json.loads(
            (ROOT / "data" / "dividend_issuer_domains.json").read_text(encoding="utf-8")
        )
        cls.verified = json.loads(
            (ROOT / "data" / "verified_dividend_events.json").read_text(encoding="utf-8")
        )

    def test_verified_events_match_real_candidates_and_primary_source(self):
        events = validated_events(self.verified)
        self.assertEqual(len(events), 3)
        self.assertEqual({event["ticker"] for event in events}, {"BAC"})
        self.assertEqual(
            [(e["ex_date"].isoformat(), e["payment_date"].isoformat(), e["amount_per_share"])
             for e in events],
            [
                ("2026-03-06", "2026-03-27", 0.28),
                ("2026-06-05", "2026-06-26", 0.28),
                ("2026-09-04", "2026-09-25", 0.32),
            ],
        )
        approvals = []
        for raw in self.verified["events"]:
            self.assertTrue(domain_matches(
                raw["source_url"], self.issuers["domains"]["BAC"]
            ))
            self.assertEqual(raw["currency"], "USD")
            self.assertEqual(raw["verification_method"], "manual_issuer_document")
            approvals.append({
                "ticker": raw["ticker"], "ex_date": raw["ex_date"],
                "amount_per_share": raw["amount_per_share"],
                "currency": raw["currency"],
                "payment_date": raw["payment_date"],
                "issuer_source_url": raw["source_url"],
                "reviewed_by": raw["reviewed_by"],
                "reviewed_at": raw["reviewed_at"],
            })
        reconstructed = prepare_review(
            approvals, self.candidates, self.issuers,
            {"schema_version": 1, "events": []}, dt.date(2026, 11, 6)
        )
        self.assertEqual(reconstructed, self.verified)

    def test_no_unverified_candidates_are_promoted(self):
        candidates = {
            (row["ticker"], row["ex_date"], round(float(row["amount_per_share"]), 10))
            for row in self.candidates["candidates"]
        }
        for event in self.verified["events"]:
            key = (event["ticker"], event["ex_date"], round(float(event["amount_per_share"]), 10))
            self.assertIn(key, candidates)
        self.assertEqual(len(self.verified["events"]), 3)


if __name__ == "__main__":
    unittest.main()
