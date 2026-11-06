# First issuer-reviewed dividend evidence — 2026-11-06

## Provenance

Official Bank of America Corporation Investor Relations dividend history:
https://investor.bankofamerica.com/shareholder-information/dividends

This is an issuer-controlled historical dividend table, **not a Yahoo estimate**.
The table gives the common-stock amounts in USD, ex-dividend dates and payment
dates. The three events were cross-checked against the vendor candidate records
published in `data/dividend_event_candidates.json`, and accepted through the
`prepare_review` contract in `scripts/discovery_dividend_review.py`.

| Symbol | Ex-dividend | Payment | Cash/share | Official primary evidence |
|---|---|---|---|---|
| BAC | 2026-03-06 | 2026-03-27 | USD 0.28 | Issuer IR dividend history |
| BAC | 2026-06-05 | 2026-06-26 | USD 0.28 | Issuer IR dividend history |
| BAC | 2026-09-04 | 2026-09-25 | USD 0.32 | Issuer IR dividend history |

Reviewed by: Vestra AI-assisted primary-source review, 2026-11-06.
This records an **issuer-documented historical payment schedule**, not access
to custodial/bank settlement statements for every individual shareholder.
The reviewer and source are explicit to avoid implying human or custodian
attestation. Future corrections require an audited PR, not silent history edits.

## Scope limitations

Only three BAC 2026 dividends are confirmed by this batch; no other vendor
candidate is automatically elevated. Quote currencies in all 65 initial
candidates were absent, so source-domain-reviewed USD is required rather than
assuming quote-denominated units. The source of truth for actual paid cash
remains the issuer announcement and registered historical record.

These ex-dividend dates precede the current October–November prospective
Discovery cohorts. **They do not magically backfill cohort total returns**.
Price-return IC, production Opportunity ranking and validation readiness stay
unchanged. Further corporate actions, tax/FX effects, additional dividends
and delisted issuers remain unverified.
