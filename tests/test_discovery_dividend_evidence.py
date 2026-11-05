"""Tests for issuer-documented cash dividends: diagnostic, never assumed complete."""
import datetime as dt
import unittest

from scripts.discovery_dividend_evidence import validated_events, documented_dividend_cash
from scripts import opportunity_forward_validation as opportunity


def event(**overrides):
    value = {
        "ticker": "AAA", "ex_date": "2026-08-10",
        "payment_date": "2026-08-20", "amount_per_share": 0.5,
        "currency": "USD", "source_url": "https://example.org/dividend/2026",
        "status": "confirmed",
    }
    value.update(overrides)
    return value


class DocumentedDividendTests(unittest.TestCase):
    def test_missing_ledger_is_no_evidence(self):
        self.assertEqual(validated_events(None), [])
        self.assertEqual(documented_dividend_cash("AAA", "2026-08-02",
                         "2026-08-30", "USD", [])["event_count"], 0)

    def test_paid_event_is_separate_from_ranking_return(self):
        rows = validated_events({"schema_version": 1, "events": [event()]})
        cash = documented_dividend_cash("AAA", "2026-08-02", "2026-08-30", "USD", rows)
        self.assertEqual(cash["event_count"], 1)
        self.assertAlmostEqual(cash["cash_per_terminal_share"], 0.5)
        snap = [{"date": "2026-08-02", "observations": {
            "AAA": {"price": 100, "currency": "USD", "opportunity_score": 80},
        }}]
        outcomes = []
        opportunity.materialise_outcomes(
            dt.date(2026, 8, 30), snap,
            {"AAA": {"current_price": 110, "currency": "USD"}}, outcomes, rows
        )
        self.assertEqual(outcomes[0]["return_pct"], 10.0)
        self.assertEqual(outcomes[0]["documented_dividend_event_count"], 1)
        self.assertEqual(outcomes[0]["documented_cash_inclusive_return_pct"], 10.5)

    def test_payment_after_evaluation_is_not_cash_received(self):
        rows = validated_events({"schema_version": 1, "events": [
            event(payment_date="2026-09-10")
        ]})
        self.assertEqual(documented_dividend_cash("AAA", "2026-08-02",
             "2026-08-30", "USD", rows)["event_count"], 0)

    def test_pre_snapshot_ex_date_does_not_belong_to_cohort(self):
        rows = validated_events({"schema_version": 1, "events": [
            event(ex_date="2026-08-01")
        ]})
        self.assertEqual(documented_dividend_cash("AAA", "2026-08-02",
             "2026-08-30", "USD", rows)["event_count"], 0)

    def test_forecast_and_dividend_yield_are_not_evidence(self):
        for changed in (
            {"status": "estimated"},
            {"source_url": ""},
            {"source_url": "http://example.org/dividend"},
            {"amount_per_share": -1},
            {"payment_date": "2026-08-01"},
        ):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                validated_events({"schema_version": 1, "events": [event(**changed)]})

    def test_currency_mismatch_and_missing_currency_fail_closed(self):
        rows = validated_events({"schema_version": 1, "events": [event()]})
        for currency in ("EUR", ""):
            with self.subTest(currency=currency), self.assertRaises(ValueError):
                documented_dividend_cash("AAA", "2026-08-02", "2026-08-30",
                                         currency, rows)

    def test_registry_rejects_duplicate_payments(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            validated_events({"schema_version": 1, "events": [event(), event()]})

    def test_reverse_split_cash_moves_to_end_share_basis(self):
        rows = validated_events({"schema_version": 1, "events": [
            event(ticker="NFE", ex_date="2026-09-01",
                  payment_date="2026-09-05", amount_per_share=0.1)
        ]})
        cash = documented_dividend_cash("NFE", "2026-08-01",
              "2026-10-01", "USD", rows)
        self.assertAlmostEqual(cash["cash_per_terminal_share"], 5.0)


if __name__ == "__main__":
    unittest.main()
