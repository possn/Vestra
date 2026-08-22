# Vestra — Data source strategy (v3.8)

## Principle
No single provider is authoritative for every market. Vestra should merge sources, preserve provenance, and never turn missing data into zero.

## Active / implemented
- Yahoo Finance: quotes, market metadata, valuation, statements, price history, analyst context where available.
- SEC EDGAR Company Facts (optional pipeline fallback): official US/foreign-private-issuer XBRL. Enabled with `SEC_USER_AGENT`; no API key.
- SEC Form 4: US insider transactions.
- Bargo / STOCK Act: US Congress disclosures.

## Recommended next sources
### filings.xbrl.org (priority: high)
Public API for ESEF/UKSEF filings and xBRL-JSON. Best candidate to improve European listed-company fundamentals. Main engineering requirement is robust ticker/ISIN -> LEI resolution.

### Companies House XBRL/iXBRL (priority: medium)
Free UK accounts data. Useful for UK legal entities, especially where Yahoo fundamentals are sparse. Mapping listed security -> company number must be curated.

### Business Quant (priority: high, optional API key)
Normalized SEC statements, analyst estimates, insider transactions, institutional ownership, segments and filings. Useful second opinion for US-listed companies and source cross-checking.

### Financial Modeling Prep / Alpha Vantage / Finnhub / EODHD (priority: optional)
Potential commercial/freemium fallbacks for global analyst estimates and normalized fundamentals. Should remain optional providers, never hard dependencies.

## Score roadmap
- v2: Quality, Growth, Balance, Cash Flow, Valuation, Execution, Stability.
- Next: earnings quality/accruals, share-based compensation, multi-year consistency, estimate revision breadth, capital allocation, sector-native models.
- Confidence should be source-aware: coverage + freshness + independent-source agreement.

## v3.9 roadmap confirmado

### filings.xbrl.org — ESEF / UKSEF
API pública JSON-API (`/api/filings`, `/api/entities`) e xBRL-JSON por filing. Será usada como fallback europeu quando existir identificação robusta por LEI/issuer; não se fará fuzzy matching silencioso de empresas.

### Companies House — Reino Unido
API oficial live, mas requer API key. Boa candidata para identidade societária e filing history; o conteúdo contabilístico será ligado apenas quando a correspondência company-number/issuer for inequívoca.

### Regra de provenance
Nenhuma nova fonte substitui silenciosamente um valor existente. O pipeline deve guardar a origem por métrica, preferir filings oficiais para contas históricas e manter Yahoo/consenso para preços/estimativas.
