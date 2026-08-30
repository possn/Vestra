# Vestra Cloudflare Worker deployment contract

## Current audit status — 2026-08-30

The repository contains `worker.js`, but it does not currently contain enough deployment metadata to prove which Cloudflare Worker deployment is serving the production app.

Specifically, the repository does not currently version:

- `wrangler.toml`, `wrangler.json` or `wrangler.jsonc`;
- the Cloudflare account/project association;
- the Worker deployment name;
- the production `workers.dev` hostname or custom route;
- a GitHub Actions workflow that deploys `worker.js`;
- a deployment SHA/version endpoint that lets the browser or an operator verify the running revision.

Until this is added, `worker.js` is source code, not proof of the deployed runtime.

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
   - Deployment should be performed by a documented manual Wrangler command or a GitHub Actions workflow.
   - The deployed runtime should expose a harmless revision identifier such as `git_sha` or `build_id` at `/` or `/health`.
   - The identifier should correspond to the Git commit that supplied `worker.js`.

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

1. Version the deployment configuration and production hostname/route.
2. Add a revision/health identifier and verify the deployed SHA.
3. Align quote TTL/freshness semantics and add cache diagnostics.
4. Regression-test `/quote`, `/quotes` and `/market` from the Vestra production origin and iOS PWA.
5. Only then add `POST /ai-brief` and provider secrets.

## Acceptance checks

A Worker deployment is considered verified only when all of the following are true:

- the repository identifies how `worker.js` is deployed;
- the production URL is known and versioned or otherwise documented;
- `/health` or `/` reports the expected deployed revision;
- CORS succeeds from the Vestra production origin and rejects unrelated browser origins;
- `/quote` and `/quotes` return equivalent identity-safe prices for the same instruments;
- a second refresh after the browser cache expires does not silently serve an unexpectedly old Worker cache entry;
- Worker failure leaves the app's last-known-value behavior intact;
- no provider/API secret is present in frontend assets or repository history.
