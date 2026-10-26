# Pre-breakout: first real-data pilot — decision and execution protocol

Date: 2026-10-26. Research only. **No observed empirical alpha yet.**

## Decision
**Prefer Sharadar SEP as primary candidate for a multiyear US-stock panel. Keep EODHD as a fallback pilot.** This is a provider-selection hypothesis based on published documentation, *not* proof of vendor accuracy, purchased rights or available credentials.

| Criterion | Sharadar SEP | EODHD |
|---|---|---|
| US active + delisted equities | Documented | Documented (delisted symbol lookup) |
| EOD OHLCV and adjustments | Documented | Documented |
| Ticker rename and delist histories | Documented | Documented via separate workflows |
| PIT universe / membership | Reconstruct and independently verify | S&P 500 history only with documented pre-2012 incompleteness; must audit |
| Rights to download/use within Vestra | **Not verified** | **Not verified** |
| Account subscription / valid access | **Not verified** | **Not verified** |
| Historical integrity on real rows | **Not verified** | **Not verified** |

Sources, consulted 2026-10-26:
- https://data.nasdaq.com/databases/SEP/documentation
- https://sharadar.com/docs/stocks
- https://eodhd.com/financial-apis/delisted-stock-companies-data-2
- https://eodhd.com/financial-apis/api-for-historical-data-and-volumes
- https://eodhd.com/financial-apis/stock-etfs-fundamental-data-feeds

## Stop expanding the research framework
The next PR with executable research should *consume real licensed raw observations* or be a minimal connector needed to ingest them. No more simulated findings or generic methodological PRs as substitutes for the pilot. Never embed API credentials or restricted market rows in git.

## Smallest defensible pilot
1. Establish whether the operator already has a legally usable SEP/EODHD (or equivalent) subscription and access to historical listing and delisting information. Check supported secrets and existing ingestion paths without printing secret values. If not, record `BLOCKED_DATA_ACCESS` and list exact access needed. Do not imply a provider was connected.
2. On permitted, privately stored immutable raw data: capture raw checksum, vendor/version/retrieval timestamp, per-row availability, corporate actions, exchange sessions, stable instrument identities and listing / delisting intervals. Keep audit report, rejected observations and sample diagnostics. De-identify/restrict artifacts to comply with licensing.
3. Select universe using **as-of** membership, not today's tickers. Include bankrupt and delisted constituents; distinguish genuine absence of trading due to listing/suspension from missing provider rows. Avoid convenience 2026 survivors-only samples.
4. Pilot periods must cover distinct regimes, and include enough independent issuers/months. If data access only offers a handful of demo tickers, label *connectivity smoke-test only*.
5. Pre-register **one** technical pre-breakout rule (base compression with price/volume evidence) and **one** date/sector/size/liquidity/volatility matched baseline; freeze features and thresholds before evaluating reserved periods. Define next-session executable entry and 5/10/20 trading-session marks. Event maturity and delisting cash payouts must be reflected.
6. Time-purged/embargoed train/test folds; reserve terminal 20% of historical calendar time as sealed holdout. Derive all normalization and thresholds strictly from training. Avoid repetitive trial-and-error on terminal holdout.
7. Include gross-to-net bridge: spreads, realistic commissions, slippage, liquidity/market impact bands, stress at 2x base cost. Track turnover, trading eligibility and delisting liquidations.
8. Report per-fold and pooled sample coverage, counts and concentration, incremental paired net returns, drawdown / profit factor if defined, false-breakout rate under predeclared criterion, effective uncertainty across issuers and market periods, regime stability, multiplicity and null/inconclusive status.
9. **Decision:** NO EDGE, INCONCLUSIVE or RESEARCH CANDIDATE. A candidate requires convincing robust out-of-sample results, and then prospective paper/shadow evaluation before any production signal; never equate historical returns with calibrated success probabilities.

## Hard admission checklist
- [ ] Access and permitted use verified
- [ ] Data schema and provenance independently inspected
- [ ] As-of universe incl. delistings validated
- [ ] Stable instrument IDs / rename and split handling verified
- [ ] Independent trading calendar available
- [ ] Executable price, corporate action and volume rows audited
- [ ] Experiment and baseline preregistered
- [ ] Terminal holdout sealed, not inspected during tuning
- [ ] Cost assumptions explicitly justified
- [ ] Report reproducible from authorized inputs

## Current truth
Only deterministic synthetic contract tests and code-quality gating have been integrated to date. There is no authorized historical panel verified in this branch and no observed trade performance to report. This memo is **not a data admission decision**.