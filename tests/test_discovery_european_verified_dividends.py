"""Audit contract for eight issuer-verified European dividend records.

Only listed legacy candidates are promoted; original BAC records remain fixed.
Cash unit must be sourced from the issuer, never from Yahoo quote denomination.
"""
import datetime as dt
import json
import unittest
from pathlib import Path

from scripts.discovery_dividend_evidence import validated_events
from scripts.discovery_dividend_review import prepare_review, domain_matches

ROOT = Path(__file__).resolve().parents[1]
EXPECTED = {
    ("ENEL.MI", "2025-01-20"): ("2025-01-22", 0.215),
    ("ENEL.MI", "2025-07-21"): ("2025-07-23", 0.255),
    ("ENEL.MI", "2026-01-19"): ("2026-01-21", 0.23),
    ("ENEL.MI", "2026-07-20"): ("2026-07-22", 0.26),
    ("UCG.MI", "2024-11-18"): ("2024-11-20", 0.9261),
    ("UCG.MI", "2025-04-22"): ("2025-04-24", 1.4764),
    ("UCG.MI", "2025-11-24"): ("2025-11-26", 1.4282),
    ("UCG.MI", "2026-04-20"): ("2026-04-22", 1.7208),
}


class EuropeanVerifiedDividendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.candidates = json.loads(
            (ROOT / "data" / "dividend_event_candidates.json").read_text(encoding="utf-8")
        )
        cls.issuers = json.loads(
            (ROOT / "data" / "dividend_issuer_domains.json").read_text(encoding="utf-8")
        )
        cls.ledger = json.loads(
            (ROOT / "data" / "verified_dividend_events.json").read_text(encoding="utf-8")
        )

    def test_eight_records_have_issuer_evidence_and_exact_matching_candidates(self):
        verified = validated_events(self.ledger)
        self.assertGreaterEqual(len(verified), 11)
        european = [e for e in verified if e["ticker"] in {"ENEL.MI", "UCG.MI"}]
        self.assertGreaterEqual(len(european), 8)
        observed = {
            (e["ticker"], e["ex_date"].isoformat()): (
                e["payment_date"].isoformat(), e["amount_per_share"]
            ) for e in european
        }
        for key, outcome in EXPECTED.items():
            self.assertEqual(observed.get(key), outcome)
        candidates = {
            (c["ticker"], c["ex_date"], round(float(c["amount_per_share"]), 10))
            for c in self.candidates["candidates"]
        }
        for record in (r for r in self.ledger["events"] if r["ticker"] in {"ENEL.MI", "UCG.MI"}):
            self.assertIn(
                (record["ticker"], record["ex_date"], round(float(record["amount_per_share"]), 10)),
                candidates,
            )
            self.assertEqual(record["currency"], "EUR")
            self.assertTrue(domain_matches(
                record["source_url"], self.issuers["domains"][record["ticker"]]
            ))
            self.assertEqual(record["verification_method"], "manual_issuer_document")
            self.assertLessEqual(record["payment_date"], record["reviewed_at"])

    def test_european_records_pass_manual_approval_gate_and_preserve_bac(self):
        approvals = [{
            "ticker": r["ticker"], "ex_date": r["ex_date"],
            "amount_per_share": r["amount_per_share"], "currency": r["currency"],
            "payment_date": r["payment_date"], "issuer_source_url": r["source_url"],
            "reviewed_by": r["reviewed_by"], "reviewed_at": r["reviewed_at"],
        } for r in self.ledger["events"] if r["ticker"] != "BAC"]
        old = {"schema_version": 1, "events": [
            r for r in self.ledger["events"] if r["ticker"] == "BAC"
        ]}
        rebuilt = prepare_review(
            approvals, self.candidates, self.issuers, old, dt.date(2026, 11, 6)
        )
        self.assertEqual(rebuilt, self.ledger)

    def test_unverified_remaining_events_are_not_auto_confirmed(self):
        candidates = self.candidates["candidates"]
        verified = self.ledger["events"]
        self.assertGreaterEqual(len(verified), 11)
        self.assertGreaterEqual(len(candidates), len(verified))
        self.assertGreaterEqual(len(candidates) - len(verified), 0)
        self.assertEqual(
            sum(e["ticker"] in {"ENEL.MI", "UCG.MI"} and
                (e["ticker"], e["ex_date"]) in EXPECTED
                for e in verified), 8
        )


if __name__ == "__main__":
    unittest.main()
