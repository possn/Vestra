# Vestra Pre-Breakout — independent PIT quantitative laboratory (research only)

**Status:** specification + deterministic primitives; NOT a predictive model, NOT a backtest, NOT deployable as trading advice.

## Data acquisition gate
Dataset is BLOCKED until sources provide multi-year, exchange-calendar-aligned, adjusted and *point-in-time* OHLCV, company IDs including delistings, timestamped universe membership/capitalization, survivorship history, sector classification, FX quote units, splits/dividends, corporate action versioning, benchmark and realistic cost/spread proxies. Record vendor/license, bar availability timestamp, missing sessions, adjusted/unadjusted basis, corporate actions, checksum and original immutable files. Do not construct an investment universe from today's stocks-index and claim historical OOS significance.

## Pre-registered hypothesis / protocol
- Unit of analysis: **distinct base/pivot episode** with stable issuer identity; implement non-overlapping event cooldown; no duplicate slot snapshots or ticker/stage duplicates as independent training examples.
- Feature cutoff: only data verifiably available *before* the signal session ends; exclude same-day earnings revisions published after evaluation and all future rows.
- Pivot: max preceding 40 completed high bars, strictly *excluding* signal bar. Record original pivot in immutable event row; never recalculate it from future OHLCV.
- Confirmation: first future complete session close > immutable pivot × 1.005, above previous close, in upper 25% of daily range, session volume >= 1.5 × mean of 20 previous strictly positive session volumes. Any missing OHLCV/holiday/exchange calendar ambiguity means unknown, not negative.
- Event windows: next 5, 10, 20 *exchange* sessions; confirmed and not-confirmed labels only after the entire chosen horizon is mature. Independently classify pivot survival, sustained breakout, target-before-stop, and net return under an ex-ante trading policy.
- Split: terminal untouched chronological holdout; walk-forward with purging of *full realized label lifetimes* and session embargo; same issuer/date clustering. No rolling-snapshot pseudoreplication.
- Baselines: random *eligible* entries with matched date/liquidity/sector, simple momentum, classic confirmed breakout, investable market benchmark.
- Measure coverage/abstention, precision@3/5, recall, false-breakout rate, Brier/reliability when probabilities exist, median and mean after spread/commissions/slippage/impact, expected net payoff, MAE/MFE, drawdown, capacity, cluster-bootstrap CIs and multiple-testing correction.
- Candidate models: deterministic baseline first, then regularized logistic/hazard/boosting only after ablation, leakage checks and OOS gains with uncertainty. Calibrate only within training folds (never on final test).
- Promotion gate: no app-facing feature/ranking/probability modification until empirical report establishes incremental OOS performance and feasible net economics under pessimistic costs; shadow-first rollout and rollback.

## Initial implementation
`pit_events.py`: strict daily OHLCV validation; prospective first-confirmation labels at 5/10/20 completed sessions; coarse deterministic temporal purge requiring global trading session ordinals. These are *primitives*, not complete historical study. `test_pit_events.py`: synthetic integrity tests; no real datasets included.

### Known limitations explicitly retained
A global-calendar ordinal alone does not align cross-market issuer holidays, so a full market-aware calendar service is still needed; no PIT historical data currently attached; no multi-year sample; no empirical calibration, costs, trade simulator or profitability estimates. This branch does NOT touch scanner, UI, quotes, market ranking or existing engines.
