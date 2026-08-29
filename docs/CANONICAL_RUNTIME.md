# Vestra canonical runtime

This document defines the production runtime source of truth after the architecture cleanup.

## Canonical production modules

The production loader is `index.html`. Runtime files loaded there, together with the Service Worker app shell, are the supported browser runtime.

Core application modules currently include:

- `app-utils.js`
- `app-feedback.js`
- `app-storage.js`
- `app-asset-identity.js`
- `app-ui-core.js`
- `app-broker-normalization.js`
- `app-xtb-normalization.js`
- `app-broker-identity-data.js`
- `app-broker-parsing-core.js`
- `app-file-parsing.js`
- `app-broker-workbook.js`
- `app-broker-parsers.js`
- `app-market-client.js`
- `app-quote-errors.js`
- `app-return-assumptions.js`
- `app-financial-engine.js`
- `app.js`
- `market.js`
- `market-data-loader.js`
- `market-company-brief.js`
- `market-metric-cleanup.js`
- `market-metals.js`
- `market-opportunities.js`
- `market-opportunity-lenses.js`
- `portfolio-collapsibles.js`
- `portfolio-sheet-navigation.js`
- `portfolio-card-classifier.js`
- `portfolio-diagnostics.js`
- `portfolio-dossier-routing.js`
- `politicians.js`
- `vestra-portfolio-focus.js`
- `vestra-portfolio-hierarchy.js`
- `vestra-swap-lab.js`
- `vestra-ai-brief.js`
- `vestra-portfolio-ui.js`

## Runtime rules

1. Do not add root runtime modules with numeric release suffixes such as `*-v482.js`.
2. Temporary repair overlays must be folded into the canonical owner module or removed.
3. `index.html` and `sw.js` must agree on production runtime modules.
4. Canonical modules must not dynamically load retired overlays.
5. Missing financial data remains missing; runtime cleanup must not convert missing values to zero or alter financial semantics.
6. Navigation, dossier routing and quote refresh must use the canonical ownership boundaries below rather than accumulating document-level listeners.
7. Structural cleanup is protected by regression tests.

## Canonical navigation ownership

- `portfolio-sheet-navigation.js` exposes `window.VestraNavigation.openCompany()` as the canonical dossier-opening boundary.
- `market-data-loader.js` owns lazy dossier hydration and delegates opening to `VestraNavigation`.
- `portfolio-dossier-routing.js` owns portfolio row/ticker discovery and delegates navigation.
- `market.js` remains the dossier renderer and normal Market sheet owner.
- Portfolio-origin dossiers preserve their return target; the latest async dossier request wins before rendering.

## Canonical quote refresh ownership

- `app.js` contains one refresh orchestrator: `refreshLiveQuotes()` / `refreshLiveQuotesCore()`.
- `quoteRefreshPromise` is the single-flight gate used by manual refresh, startup auto-refresh and foreground auto-refresh.
- `autoRefreshQuotesIfStale()` is the only automatic refresh policy and uses the same refresh gate.
- `app-market-client.js` owns Worker transport, timeout handling, FX retrieval and the effective quote concurrency ceiling (`MAX_QUOTE_CONCURRENCY`).
- The active portfolio refresh path uses proven individual `/quote` requests with per-asset fallbacks. `fetchQuotesBatch()` remains a compatibility helper but is not wired into `app.js`.
- Quote failures preserve the existing last-known-value/sanity behavior and are surfaced through `app-quote-errors.js`; missing or failed data must never be converted to zero.

## Phase 1 removals

The following abandoned overlays were removed because they are not part of the production loader and their responsibilities are already represented by canonical modules:

- `market-hotfix.js`
- `vestra-ai-brief-v459.js`
- `vestra-portfolio-nav-fix-v464.js`
- `vestra-portfolio-tabs-v479.js`
- `vestra-portfolio-dossier-routing-v482.js`

## Completed extraction boundaries

1. Navigation and dossier orchestration: consolidated behind `VestraNavigation` with async latest-request protection.
2. Quote refresh boundary: audited and locked to one orchestrator/single-flight gate plus one transport owner; no additional runtime abstraction was added because the current split is already canonical after the iOS quote hotfix.

## Next architecture boundary

The next architecture work should focus on data provenance and source confidence before altering score semantics. Any later extraction from `app.js` or `market.js` should preserve current user flows and add regression coverage before removing existing ownership.
