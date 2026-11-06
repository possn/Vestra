# Discovery dividend verification — manual evidence gate

**Vendor observations are never automatically treated as paid dividends.** The daily `discovery-dividend-candidates.yml` scan records Yahoo ex-dates and per-share amounts in `data/dividend_event_candidates.json` with `pending_issuer_verification`. This file does not establish the announced payment date, ownership entitlement, the cash payment or issuer provenance.

## Review process (explicit human action)

1. Find a candidate with matching ticker, ex-date and per-share amount. Independently consult a **primary issuer announcement** and verify the payment actually took place. Cross-check share class, corporate action basis, currency and source identity.
2. Add the issuer's independently confirmed registrable domain to `data/dividend_issuer_domains.json`. Start with an empty registry; do **not** trust an automatically inferred issuer domain or a vendor link.
3. Create a local approvals JSON **array** with the matched candidate and documented details, for example (illustrative, not real data):

```json
[
  {
    "ticker": "EXAMPLE",
    "ex_date": "2026-09-01",
    "amount_per_share": 0.25,
    "currency": "USD",
    "payment_date": "2026-09-15",
    "issuer_source_url": "https://investors.issuer-example.com/news/dividend",
    "reviewed_by": "Reviewer identity",
    "reviewed_at": "2026-09-16"
  }
]
```

4. Run a dry run: `python scripts/discovery_dividend_review.py --approvals /path/to/approvals.json`. Review all results. Explicitly publish only after evidence inspection with `--write`; commit the verified ledger through the normal PR/CI process. The tool does not fetch or certify the issuer page itself.
5. Never treat the resulting cash-attribution diagnostics as complete total shareholder return: omitted dividends, currency changes, taxes, corporate actions and terminal delisting outcomes can still invalidate completeness. Production ranking IC, weights and gates are unchanged.

The validation rejects an absent vendor candidate, a mismatched ticker/ex-date/amount/currency, duplicate approval, future or pre-ex-date payment, absent reviewer, unregistered issuer domains, Yahoo/aggregator/lookalike hostnames, and inconsistent chronology. An issuer-domain check is a **necessary identity control, not proof of the page contents**: the reviewer must inspect and retain the actual statement.

There is intentionally no scheduled workflow to approve candidates. Historical snapshots remain immutable.
