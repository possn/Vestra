# Vestra canonical runtime

Updated 1 September 2026.

This document defines the production runtime source of truth after the architecture audit and post-audit hardening.

## Canonical production entrypoints

- Browser/PWA loader: `index.html`.
- Service Worker: `sw.js` (`Vestra Service Worker v10.11`, cache `vestra-cache-v125`).
- Cloudflare Worker deployment manifest: `wrangler.toml`.
- Cloudflare Worker entrypoint: `worker-router.js`.
- Production Worker: `https://delicate-bar-cc80.pedrossnunes.workers.dev`.

Runtime files loaded by `index.html`, together with modules reachable from those files and the Service Worker app shell, are the supported browser runtime. Cloudflare Worker modules reachable from the Wrangler entrypoint are a separate supported runtime graph.

## Core browser ownership boundaries

### Application shell / portfolio

Core application modules include `app-utils.js`, `app-feedback.js`, `app-storage.js`, identity/parsing modules, `app-market-client.js`, `app-quote-errors.js`, `app-financial-engine.js` and `app.js`.

`app.js` remains the high-level portfolio/UI orchestrator. Do not create a second quote refresh owner or a second persistent storage schema.

### Market

`market.js` remains the primary Market renderer and normal Market sheet owner. The following responsibilities have canonical extracted owners:

- live dossier price/metric overlay: `market-live-overlay.js`;
- Congress live state/feed: `market-congress-live.js`;
- portfolio context helpers: `market-portfolio-context.js`;
- watchlist persistence and change snapshots: `market-watch-snapshots.js`;
- startup static universe loading: `market-static-universe.js`;
- catalyst/recovery/drawdown signal panels: `market-dossier-signals.js`;
- local search suggestion matching/rendering: `market-search-suggestions.js`;
- base market row presentation/fund classification/score CSS: `market-row-ui.js`;
- lazy dossier hydration: `market-data-loader.js`;
- global market search: `market-global-search.js`;
- local learned-universe persistence: `market-learned-universe.js`.

Do not move Score, Low52, Opportunity Rank, scanner or valuation mathematics into presentation modules.

## Canonical navigation ownership

- `portfolio-sheet-navigation.js` exposes `window.VestraNavigation.openCompany()` as the dossier-opening boundary.
- `market-data-loader.js` owns lazy dossier hydration and delegates opening to the navigation boundary.
- `portfolio-dossier-routing.js` owns portfolio row/ticker discovery and delegates navigation.
- Watchlist controls inside ticker cards are actions, not navigation requests; capture-phase dossier handlers must explicitly exclude `[data-market-watch]`.
- Portfolio-origin dossiers preserve their return target and must remain usable on iPhone/WebKit.

## Canonical quote refresh ownership

- `app.js` contains one refresh orchestrator: `refreshLiveQuotes()` / `refreshLiveQuotesCore()`.
- `quoteRefreshPromise` is the single-flight gate used by manual, startup and foreground refresh.
- `autoRefreshQuotesIfStale()` is the only automatic refresh policy and uses the same gate.
- `app-market-client.js` owns Worker transport, timeout handling, FX retrieval, request de-duplication and the effective quote concurrency ceiling.
- Logical quote requests may be coalesced into Worker `GET /quotes` batches, with conservative fallback to `GET /quote`.
- Browser and Worker quote freshness policies must remain aligned; slow-changing `/market` fundamentals may have a longer cache but price-sensitive fields receive the fresh quote overlay.
- Quote failures preserve last-known-value/sanity behaviour. Missing or failed numeric data must never be converted to zero.

## Cloudflare Worker ownership

### `worker.js`

Owns the Yahoo Finance market transport:

- `GET /quote`;
- `GET /quotes`;
- `GET /market`;
- base `/health` market metadata.

Congress is not proxied by the Worker.

### `worker-router.js`

Is the production Wrangler entrypoint. It delegates market transport to `worker.js` and owns additional server-side routing:

- `GET|POST /learned-universe`;
- `POST /ai-brief`;
- enriched `GET /health` capability reporting.

### `worker-ai-brief.js`

Owns the evidence-only AI boundary:

- Cloudflare Workers AI binding `env.AI`;
- model `@cf/meta/llama-3.3-70b-instruct-fp8-fast`;
- JSON Schema response contract;
- evidence allowlist and null-safe normalization;
- cache by ticker + SHA-256 evidence hash;
- short timeout;
- fail-closed normalization for malformed output or direct trading/position-sizing instructions;
- per-session Cloudflare rate limiting through `AI_BRIEF_RATE_LIMITER`.

The browser never receives a provider secret. AI failure must leave the deterministic local dossier brief intact and must not affect quote transport.

### Learned universe

`LEARNED_UNIVERSE` is a Durable Object binding. Browser global search persists locally first, posts validated identities centrally, and the data pipeline later promotes learned tickers into the official universe.

## Runtime rules

1. Do not add root runtime modules with numeric release suffixes such as `*-v482.js`.
2. Temporary repair overlays/workflows/scripts must be folded into a canonical owner or removed before merge.
3. `index.html` and `sw.js` must agree on browser runtime modules that require offline availability.
4. Canonical modules must not dynamically load retired overlays.
5. Missing financial data remains missing; runtime cleanup must not convert absence to zero or alter financial semantics.
6. Navigation, dossier routing and quote refresh must use the canonical ownership boundaries above rather than accumulating duplicate document-level owners.
7. Worker expansion must be represented in `wrangler.toml`, source-controlled routing and production verification.
8. Structural cleanup is protected by Architecture invariants and browser-critical changes by WebKit/iPhone E2E.
9. Score Vestra weights are not to be recalibrated before prospective validation cohorts mature.

## Production verification

- Architecture invariants validate syntax, reachability, runtime contracts and the historical regression suite.
- Browser E2E validates the critical iPhone/WebKit journeys, including portfolio alternative navigation and AI Brief handoff.
- Production Pages smoke validates published browser assets/journeys.
- `Verify Cloudflare Worker` validates the deployed Worker after relevant `main` changes, including market endpoints, learned-universe contract and AI Brief health/preflight without incurring model inference in CI.

## Completed post-audit boundaries

- concurrent data publication race hardening;
- real WebKit/iPhone E2E;
- production Pages smoke;
- Low52 dedicated contracts;
- learned-universe pipeline/E2E/production contracts;
- observability and operational docs;
- live dossier overlay extraction;
- Congress live extraction;
- portfolio alternative card -> dossier event routing fix;
- watch/snapshots extraction;
- portfolio context extraction;
- retirement of obsolete one-shot mutators;
- static universe loading extraction;
- dossier signal-panel extraction;
- market search-suggestion extraction;
- market row UI extraction;
- server-side Workers AI Brief activation and production verification.

## Next architecture work

Do not continue extracting code merely to reduce line count. The next work should be driven by a concrete operational or product gap revealed by audit, production diagnostics or user flows. Score/Low52/scanner mathematics remain frozen unless a separate evidence-backed change is justified.
