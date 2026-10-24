# Vestra 2.0 — Product & engineering readiness baseline

Baseline: `8e1a1a5a0db85432a00675eb4aa403af823f0c92` (2026-10-08). This is a source/CI audit, not a production-browser certification.

## Confirmed from the repository

- The existing score validation is prospective, with 7 available weekly snapshots and 2 mature 28-day cohorts; no mature 84/168-day cohorts (report generated 2026-10-07).
- The 28-day aggregate rank IC is 0.1049 and top-minus-bottom mean return spread is +2.91 percentage points, **not yet** proof of reliable alpha.
- `app.js` is ~758 KB and `index.html` ~94 KB. Size is a maintenance warning, **not proof** of load slowness.
- The existing architecture / runtime JS / Browser E2E workflows are mandatory checks before any UX rollout.
- Broker-import identity and idempotency, portfolio risk completeness, source provenance, score confidence, and crypto production-data completeness are particularly high-risk user journeys.
- At baseline 29 PRs remained open, many older than current main and overlapping in functional scope. Revalidate rather than batch-merge.

## P0 — invariants before visual redesign

1. **Positions and cash:** same broker file reimported twice produces the same normalized ledger, holdings, FX-aware cost basis, cash and total value. Duplicate IDs must be stable across reorderings.
2. **Data readiness:** missing / stale price, score, portfolio factor, fund look-through and crypto metrics must show unknown/stale; never present zero or healthy by default.
3. **Published production:** check deployed Pages + Cloudflare Worker endpoints, not just repository source. Record last updated timestamp, source and coverage per feature.
4. **Navigation/resume:** a Market dossier, news external-return, portfolio modal and a backgrounded iPhone PWA must preserve view ownership and must not flash a synthetic zero balance.
5. **Performance:** measure iPhone cold/warm load, interaction latency, quote-to-paint, route transitions, memory and layout shifts on actual published build. Save a baseline before changes; no guessed thresholds.
6. **Risk/score:** Decision / Conviction / Confidence / Risk Gate are independent semantics; unavailable evidence is not an implicit clearance. No new trade instruction from weakly validated scores.

## Product information architecture

- **Hoje** — 3 prioritized and explainable decisions; regime overview; material changes only.
- **Mercados** — indices, breadth, risk, liquidity, sector rotation and macro; always show time/source.
- **Investigar** — opportunity radar, screeners, company dossier, thesis tracker, valuation and technical setup.
- **Carteira** — accounting first, look-through exposure, risk budget, marginal impact simulator.
- **Cripto** — BTC/ETH/SOL, dominance, spot/derivatives, on-chain and explicit data-health warnings.

## Sequential milestones and acceptance

### M0: baseline + dependency triage
- Catalogue existing PRs into obsolete / duplicate / still relevant; do not merge blindly.
- Store reproducible data-quality and production-smoke results.
- Run all 3 required gates on the **same head SHA**.

### M1: new shell, behind a reversible feature flag
- Introduce mobile-first 5-section navigation and semantic layout components.
- Keep original data handlers and quote engine untouched.
- Verify all existing routes, WebKit viewport/safe area and deep links.
- Compare baseline performance and preserve user state on transitions.

### M2: evidence-led decisions
- Separate business quality, valuation, technical timing and portfolio risk (do not blend into an arbitrary aggregate).
- Show evidence provenance, freshness, coverage, invalidators and uncertainty at each decision.
- Do not claim predictive validation from 2 independent mature cohorts.

### M3: tracking & calibration
- Immutable thesis snapshots at decision time, subsequent realised outcomes, transaction costs and benchmark comparisons.
- Review outcomes at 28/84/168 days, controlling for overlapping observations and look-ahead bias.

## Release gates

1. Runtime JavaScript syntax success.
2. Architecture invariants success.
3. Browser E2E including WebKit iPhone success.
4. For market-data changes: production smoke after deployment; no silent partial coverage.
5. Immediately before merge: PR open, same head SHA, mergeable, behind 0, unchanged main; merge with `expected_head_sha`.
6. Any new commit after green gates invalidates the previous approval: rerun all three.

## Not established by this audit

- Actual published-app speed, exact current UX friction, or current live market accuracy.
- Real-user profitability of Vestra signals.
- That all open PRs can safely merge or that the crypto Worker is currently complete.
