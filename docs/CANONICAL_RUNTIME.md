# Vestra canonical runtime

This document defines the production runtime source of truth after the first architecture cleanup.

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
6. Navigation, dossier routing and quote refresh should converge on single canonical services rather than accumulating document-level listeners.
7. Structural cleanup is protected by regression tests.

## Phase 1 removals

The following abandoned overlays were removed because they are not part of the production loader and their responsibilities are already represented by canonical modules:

- `market-hotfix.js`
- `vestra-ai-brief-v459.js`
- `vestra-portfolio-nav-fix-v464.js`
- `vestra-portfolio-tabs-v479.js`
- `vestra-portfolio-dossier-routing-v482.js`

## Next extraction boundaries

The next architecture work should reduce responsibility in `app.js` and `market.js`, beginning with:

1. navigation and dossier orchestration;
2. quote refresh boundaries;
3. shared state ownership for overlays/sheets.

Each extraction should preserve current user flows and add regression coverage before removing legacy ownership.
