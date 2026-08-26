# Vestra data architecture

## Principle

Vestra is **static-first, live-overlay**.

Opening Market, searching the universe, filtering, ranking, or opening a company dossier must never wait for the Cloudflare Worker or for a third-party live API.

The static GitHub dataset is the durable research layer. The Worker is a best-effort live overlay.

## Static GitHub layer

Published under `data/` by GitHub Actions.

### `stocks-index.json`

Lightweight startup/search index. It contains only fields required for:

- Market lists and search
- scanner filters and rankings
- compact 52-week-low/high views
- opportunity metadata
- dossier shard routing

It deliberately excludes heavy histories and large dossier-only structures.

### `dossiers-manifest.json` + `dossiers/*.json`

Full company/fund dossiers, partitioned by ticker shard and loaded only when needed.

A dossier may include historical prices, financial statements, valuation context, thesis evidence, source metadata, insiders and Congressional disclosure context.

### `politicians.json`

Canonical, freshness-gated STOCK Act disclosure snapshot.

Current primary source is the official U.S. House Clerk disclosure archive. The snapshot records its actual chamber coverage; the UI must never imply Senate coverage unless Senate data are genuinely present.

The browser does not call third-party Congress APIs. Market and company dossiers consume this same canonical snapshot.

### Legacy `stocks.json`

Retained temporarily as an emergency migration fallback. New frontend code must not load the full file during normal Market startup or navigation.

## Live Worker layer

The Cloudflare Worker is for Yahoo/live market enrichment only.

Supported responsibilities:

- single quote lookup
- batch quote lookup
- live market-detail enrichment

Congress/politician data do **not** belong in the Worker.

### Dossier open sequence

1. Resolve ticker from the lightweight static index.
2. Load only the ticker's dossier shard if it is not already hydrated.
3. Render the dossier immediately from static data.
4. Start the Worker `/market?ticker=...` request asynchronously.
5. If live data arrive, merge non-empty fields into the in-memory stock object.
6. Update only safe visible live fields in place (price, Forward P/E, ROE, revenue growth and FCF yield) plus the Live timestamp badge.
7. Never rebuild the complete open dossier DOM when the Worker response arrives; this protects iOS/Safari modal scroll and layout state.
8. If the Worker fails, keep the static dossier usable with no blocking error.

## Freshness and failure rules

- Static research data have explicit generation timestamps and pipeline guardrails.
- Politician snapshots are rejected when their newest disclosure is more than 60 days old.
- Live quote failures never invalidate a static dossier.
- Missing fundamentals are missing values, never silently converted to zero.
- Heavy data are lazy-loaded; no new dossier field may automatically enter the startup index without an explicit whitelist decision.

## Ownership of calculations

The Worker enriches raw/current market fields only. It does not recalculate or overwrite Vestra's durable research score architecture in the browser.

Core score, opportunity rank, historical evidence and dossier research remain reproducible from the static pipeline. Live data may improve presentation/context, but a temporary Worker/API outage must not change product availability or corrupt stored portfolio data.
