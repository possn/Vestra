# Vestra — Data source strategy (v4.1)

## Principle
No single provider is authoritative for every market. Vestra should merge sources, preserve provenance, and never turn missing data into zero.

## Active / implemented
- Yahoo Finance: quotes, market metadata, valuation, statements, price history, analyst context where available.
- SEC EDGAR Company Facts: official US/foreign-private-issuer XBRL when the pipeline can resolve the issuer safely. No API key; requires a compliant `SEC_USER_AGENT`.
- ESEF / filings.xbrl.org: European/UK filing enrichment after exact issuer/LEI resolution.
- GLEIF / ANNA ISIN→LEI: identity resolution used to connect listed instruments to legal entities without silent fuzzy matching.
- SEC Form 4: official US insider transactions.
- Official House/Senate disclosures / STOCK Act: canonical US political-trading provenance. Legacy Bargo labels are scrubbed from published market rows.
- Targeted Yahoo statements: gap-filling within the Yahoo source family; these do **not** count as an independent confirmation of Yahoo data.

## Provenance contract — v1

Every full company dossier published after `scripts/normalize_market_provenance.py` carries a `data_provenance` object. It is deliberately kept out of the lightweight startup index and remains in the lazy full dossier shards.

The contract records:
- `evidence_state`: `observed`, `carried_forward`, or `metadata_only`;
- source descriptors with canonical `name`, `family`, `role`, and whether the source is independent;
- unique source families and independent-source count;
- existing cross-source agreement checks and agreement percentage, when available;
- SEC/ESEF filing period-end dates;
- identity evidence (`identity_source`, ISIN, LEI) when present;
- derived metrics, explicitly marked as **not** an independent source;
- pipeline generation timestamp as publication context, not as a substitute for filing freshness.

Rules:
1. Provenance is descriptive evidence, not a new score.
2. Missing evidence stays missing.
3. Carried-forward rows must never be represented as fresh observed evidence.
4. Metadata-only catalogue rows have zero observed sources unless evidence is actually present.
5. Two endpoints from the same provider family do not count as two independent sources.
6. Official filings may corroborate historical fundamentals; market prices and consensus remain market-feed concerns.
7. Score/Confidence semantics are not changed until provenance coverage has been measured and validated.

## Recommended next sources
### Companies House XBRL/iXBRL (priority: medium)
Free UK accounts data. Useful for UK legal entities, especially where Yahoo fundamentals are sparse. Mapping listed security -> company number must be curated.

### Business Quant (priority: optional)
Normalized SEC statements, analyst estimates, insider transactions, institutional ownership, segments and filings. Useful as a second opinion for US-listed companies if an API key/business decision justifies it.

### Financial Modeling Prep / Alpha Vantage / Finnhub / EODHD (priority: optional)
Potential commercial/freemium fallbacks for global analyst estimates and normalized fundamentals. They should remain optional providers, never hard dependencies.

## Score roadmap
- Current dimensions include Quality, Growth, Balance, Cash Flow, Valuation, Execution and Stability plus later overlays.
- Next score work should use measured provenance coverage for earnings quality/accruals, share-based compensation, multi-year consistency, estimate revision breadth, capital allocation and sector-native models.
- Confidence should become source-aware only after validation: coverage + freshness + independent-source agreement.

## European Source Fusion
- **GLEIF / ANNA ISIN→LEI**: identity resolution from ISIN to legal entity.
- **filings.xbrl.org**: ESEF/UKSEF filings and xBRL-JSON, used only after sufficiently exact issuer resolution.
- Hierarchy: price/consensus remain in the market feed; official filings have priority for historical-account evidence where appropriate.
- Known coverage gaps remain missing rather than being guessed or silently mapped to another issuer.
