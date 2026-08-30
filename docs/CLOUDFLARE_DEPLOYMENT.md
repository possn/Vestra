# Vestra Cloudflare Worker deployment contract

## Current audit status — 2026-08-30

Production Worker identified as:

`https://delicate-bar-cc80.pedrossnunes.workers.dev`

A GitHub Actions network audit was run against that exact endpoint from PR #51.

Observed production behaviour before the repository integration was corrected:

- `GET /` -> HTTP 200, service identifies itself as `Vestra Market Proxy v4.2`.
- `GET /quote?ticker=MSFT` -> HTTP 200.
- `GET /quote?ticker=AAPL` -> HTTP 200.
- `GET /quotes?tickers=MSFT,AAPL` -> HTTP 200.
- Batch and individual prices were identical for both probes.
- `GET /market?ticker=MSFT` -> HTTP 200.
- Vestra production origin receives `Access-Control-Allow-Origin: https://possn.github.io`.
- Unrelated browser origin receives `Access-Control-Allow-Origin: null`.
- Production does **not** currently return `Vary: Origin`.
- `GET /health` -> HTTP 404.
- Quote payloads expose `_cached` and `updated`; repeated probes showed the same cached generation timestamp.
- The production root still advertises `/congress` endpoints, while the current source-controlled Worker has already removed that obsolete proxy.

This proved deployment drift: the Worker serving production did not correspond to the current source-controlled `worker.js`.

## Deployment identity and Git integration

PR #51 introduces:

- `wrangler.toml` with Worker name `delicate-bar-cc80` and `main = "worker.js"`;
- `scripts/verify_worker_deployment.py` and `.github/workflows/verify-cloudflare-worker.yml` for repeatable production verification;
- Worker v4.3 source with `/health` and deployment metadata support.

The Cloudflare Worker is now connected directly to GitHub repository `possn/Vestra` using Cloudflare Workers Builds.

Cloudflare configuration confirmed in the dashboard:

- Git repository: `possn/Vestra`;
- Production branch: `main`;
- Builds for non-production branches: enabled;
- Deploy command: `npx wrangler deploy`;
- Version command: `npx wrangler versions upload`;
- Root directory: `/`;
- Include paths: `*`;
- Cloudflare-managed Workers Builds API token configured by Cloudflare.

Because Cloudflare now owns GitHub-to-Worker deployment through its native Git integration, Vestra does **not** require `CLOUDFLARE_API_TOKEN` or `CLOUDFLARE_ACCOUNT_ID` GitHub Actions secrets. The temporary GitHub deploy workflow used during the audit was removed.

## Required production contract

Before expanding Worker responsibilities, production should expose a reproducible deployment contract with all of the following:

1. **Versioned Wrangler configuration**
   - Worker name.
   - `main = "worker.js"` or equivalent.
   - Compatibility date.
   - Routes/domains when applicable.
   - No secrets committed to the repository.

2. **Secret separation**
   - Provider/API secrets are stored only as Cloudflare secrets/environment bindings.
   - The browser must never receive provider secrets.
   - `POST /ai-brief`, when enabled, must consume only server-side secrets.

3. **Deployment traceability**
   - Production deployment is performed by Cloudflare Workers Builds from the connected GitHub repository.
   - `main` is the production branch.
   - Non-production branches may be built separately for validation without replacing production.
   - The deployed runtime should expose a harmless revision identifier such as `git_sha` or `build_id` at `/` or `/health` when available.

4. **Health endpoint**
   A production health response should identify capability without leaking secrets, for example:

   ```json
   {
     "service": "Vestra Market Proxy",
     "version": "4.x",
     "git_sha": "<commit>",
     "capabilities": ["quote", "quotes", "market"]
   }
   ```

5. **CORS policy**
   - Production browser access should be restricted to the Vestra production origin plus explicit localhost development origins.
   - `Vary: Origin` must be returned when origin-dependent CORS is used.
   - CORS must not be treated as authentication.

6. **Quote freshness policy**
   - Browser cache, Worker cache and upstream fetch policy must be deliberately aligned.
   - A user-triggered refresh must not normally return a quote substantially older than the application's visible freshness policy simply because the Worker CDN cache has a longer TTL.
   - Quote cache metadata should make age/source diagnosable (`updated`, cache hit flag and ideally cache age or generated timestamp).
   - Slow-changing market detail/fundamental data may use a longer TTL than live quote data; these caches should be separate.

7. **AI brief separation**
   - `POST /ai-brief` is a separate server-side capability from market quote transport.
   - It must implement the contract in `docs/AI_BRIEF_CONTRACT.md`.
   - It must have its own timeout, cache key, rate limiting and error handling.
   - Failure of AI brief generation must never block deterministic local dossier rendering or quote transport.

## Recommended rollout order

1. Merge/version the deployment identity and verification tooling into `main`.
2. Allow Cloudflare Workers Builds to deploy the `main` revision automatically.
3. Re-run the production verifier and confirm `/health`, v4.3, CORS and removal of the obsolete `/congress` deployment.
4. Align quote TTL/freshness semantics and add stronger cache-age diagnostics.
5. Regression-test `/quote`, `/quotes` and `/market` from the Vestra production origin and iOS PWA.
6. Only then add `POST /ai-brief` and provider secrets.

## Acceptance checks

A Worker deployment is considered verified only when all of the following are true:

- the repository identifies how `worker.js` is deployed;
- the production URL is documented;
- `/health` or `/` reports the expected deployed revision/version;
- CORS succeeds from the Vestra production origin and rejects unrelated browser origins;
- origin-dependent responses include `Vary: Origin`;
- `/quote` and `/quotes` return equivalent identity-safe prices for the same instruments;
- production capabilities match the source-controlled Worker (no obsolete `/congress` drift);
- a second refresh after the browser cache expires does not silently serve an unexpectedly old Worker cache entry;
- Worker failure leaves the app's last-known-value behavior intact;
- no provider/API secret is present in frontend assets or repository history.
