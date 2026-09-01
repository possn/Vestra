# Vestra Cloudflare Worker deployment contract

Updated 1 September 2026.

## Production identity

Production Worker:

`https://delicate-bar-cc80.pedrossnunes.workers.dev`

Deployment source of truth:

- repository: `possn/Vestra`;
- production branch: `main`;
- manifest: `wrangler.toml`;
- Worker name: `delicate-bar-cc80`;
- entrypoint: `worker-router.js`;
- deployment: Cloudflare Workers Builds native Git integration;
- deploy command: `npx wrangler deploy`;
- no GitHub `CLOUDFLARE_API_TOKEN` / `CLOUDFLARE_ACCOUNT_ID` secrets are required for normal production deploys.

The audit originally found production/source drift. That drift was repaired and is now guarded by `.github/workflows/verify-cloudflare-worker.yml`.

## Runtime boundaries

### Market transport

`worker.js` owns:

- `GET /quote?ticker=...`;
- `GET /quotes?tickers=...`;
- `GET /market?ticker=...`;
- base health metadata.

Quotes use the short quote freshness contract; slower fundamentals may use the longer market cache, but `/market` overlays fresh price-sensitive fields before returning cached fundamentals.

### Router

`worker-router.js` is the deployed entrypoint. It delegates market transport and adds:

- `GET|POST /learned-universe`;
- `POST /ai-brief`;
- enriched `GET /health`.

### Learned universe

`LEARNED_UNIVERSE` is a Durable Object binding declared in `wrangler.toml`. POST accepts only authorized Vestra/local browser origins and validates the ticker through the canonical quote transport before persistence.

### AI Brief

`worker-ai-brief.js` owns the optional server-side explanatory layer.

Production configuration:

- Workers AI binding: `AI`;
- model: `@cf/meta/llama-3.3-70b-instruct-fp8-fast`;
- rate-limit binding: `AI_BRIEF_RATE_LIMITER`;
- limit: 12 calls / 60 s per random Vestra PWA session key;
- response contract: JSON Schema;
- cache: ticker + SHA-256 of normalized evidence, 30-minute TTL;
- model timeout: 10 s;
- browser fallback: deterministic local brief remains visible on any failure.

The AI layer receives only allowlisted Vestra evidence. It does not receive the portfolio, transaction history or account identity and does not modify Score, valuation or portfolio actions.

## CORS contract

- Production browser origin: `https://possn.github.io`.
- Localhost loopback origins are allowed for development.
- Unrelated browser origins are rejected.
- Origin-dependent responses include `Vary: Origin`.
- CORS is not authentication.
- `/ai-brief` preflight explicitly permits `Content-Type` and `X-Vestra-Session`.

## Health contract

Production `/health` exposes capability metadata without secrets. Current capabilities include:

- `quote`;
- `quotes`;
- `market`;
- `learned_universe`;
- `ai_brief`.

It also exposes the AI Brief provider/model and whether the rate-limit binding is available. The health endpoint is diagnostic only and does not expose binding credentials.

## Verification

`Verify Cloudflare Worker` runs on relevant `main` changes and deliberately tolerates a short deployment-propagation window.

The verification chain checks:

1. root and `/health` availability;
2. deployed/source Worker version and cache/null semantics;
3. `/quote` single-ticker responses;
4. `/quotes` batch equivalence;
5. `/market` price equivalence and fresh quote overlay on cached fundamentals;
6. production CORS and unrelated-origin rejection;
7. learned-universe health/preflight contract;
8. AI Brief health capability, provider/model, rate-limit binding and `OPTIONS /ai-brief` CORS contract.

Production CI does **not** invoke the AI model. Model behavior is covered deterministically by the runtime test with mocked `env.AI`, avoiding inference cost and nondeterministic CI output.

## Post-audit rollout status

The rollout order defined during the Worker audit is complete:

1. versioned deployment identity and verification tooling — complete;
2. Cloudflare Workers Builds from `main` — complete;
3. `/health`, CORS and obsolete Congress drift repair — complete;
4. quote TTL/freshness alignment and diagnostics — complete;
5. `/quote`, `/quotes`, `/market` regression coverage — complete;
6. `POST /ai-brief` server-side boundary — complete and production-verified on 1 September 2026.

## Acceptance rules for future Worker changes

A Worker change is not considered finished until:

- Wrangler configuration reflects any new binding/runtime dependency;
- provider secrets remain server-side only;
- source contracts and Architecture invariants pass;
- production deployment is traceable to `main`;
- production verifier closes green after Cloudflare propagation;
- quote failures preserve last-known-value behavior;
- AI/auxiliary capability failure cannot break deterministic portfolio/market rendering;
- no missing numeric value is converted to zero merely because a source failed.
