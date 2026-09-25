# Vestra Score — semantic and dependency audit

Status: **Phase 3 audit baseline**  
Production weights changed: **no**

This document maps what the current Vestra scoring layers actually mean and where signals are intentionally reused. It is an audit baseline, not a proposal to change weights.

## 1. Core Score: asset characteristics, not a recommendation

`scripts/score.py` produces the raw cross-sectional factor score. It is an explainable screening model, not a return forecast and not a portfolio action.

The engine selects one of eight score packs:

| Model | Production dimensions / weights |
| --- | --- |
| general | Quality 18%, Growth 15%, Balance 14%, Cash Flow 8%, Valuation 12%, Execution 10%, Earnings Quality 10%, Capital Allocation 8%, Stability 5% |
| growth_tech | Quality 20%, Growth 22%, Balance 12%, Cash Flow 10%, Valuation 7%, Execution 12%, Earnings Quality 9%, Capital Allocation 5%, Stability 3% |
| bank | Bank Quality 22%, Efficiency 13%, Asset Quality 10%, Capital Proxy 15%, Growth 15%, Valuation 15%, Income 5%, Stability 5% |
| reit | REIT Quality 22%, Growth 16%, Leverage 20%, P/FFO Value 20%, Distribution 17%, Stability 5% |
| insurance | Quality 22%, Underwriting 18%, Capital 18%, Growth 12%, Valuation 17%, Income Quality 8%, Stability 5% |
| utility | Quality 18%, Balance 22%, Income 18%, Valuation 17%, Growth 10%, Stability 10%, Cash 5% |
| energy | Quality 20%, Cash Flow 22%, Balance 18%, Valuation 20%, Growth 10%, Stability 10% |
| biotech | Cash Runway 25%, Net Cash 15%, Dilution Discipline 20%, Growth 20%, Operating Quality 10%, Stability 10% |

Missing dimensions are excluded and the remaining weights are re-normalised by `_weighted()`. Therefore the effective factor exposure can differ between two companies using the same named model.

### Structural Risk Gate

The raw composite is already subject to a structural Risk Gate in `score.py`:
- watch can cap the score;
- high can cap it more strongly;
- severe has the strongest cap;
- capital-structure risk can impose an even tighter cap.

Risk Gate is therefore **not independent** of the stored raw score.

## 2. Evidence Confidence: reliability, not attractiveness

`scripts/confidence.py` runs after the raw score has been created.

It computes `confidence_score` from:
- fundamental coverage 34%;
- source quality 24%;
- freshness 20%;
- source agreement 14%;
- identity quality 8%.

It then preserves the incoming score as `score_raw` and publishes a moderated `score`:
- insufficient fundamental/critical coverage -> public score suppressed;
- limited evidence -> public score capped at 59;
- moderate evidence -> public score capped at 69.

Therefore:
- `score_raw` = factor result after structural score caps from the scoring engine;
- `score` = public factor score after evidence-reliability moderation;
- `confidence_score` = reliability of the evidence itself.

These three fields must not be presented as synonyms.

## 3. Analyst estimates are outside the core Score

`scripts/analyst.py` explicitly keeps analyst estimates, revisions, surprise history, recommendations and analyst price targets outside the core score because coverage is uneven across markets.

They are contextual evidence and may later affect thesis / timing / portfolio layers, but they must not be described as components of the raw Vestra Score.

## 4. Valuation is a separate overlay, but shares inputs with Score

`scripts/valuation.py` creates an explainable peer-relative fair-value range and `valuation_signal`.

The core Score already contains a valuation dimension. The valuation overlay then reuses underlying valuation data, plus:
- public `confidence_score`;
- `risk_gate`;
- quality/growth adjustments for general and growth-tech models.

Therefore `valuation_signal` is useful contextual evidence but **not statistically independent from the Vestra Score**.

## 5. Portfolio Conviction is a synthesis layer

Current runtime `portfolioConviction(stock)` combines:
- public Vestra Score: 55%;
- confidence_score: 20%;
- estimate_momentum_score: 10%;
- valuation_signal mapped to a numeric value: 15%;
- thesis direction adjustments;
- estimate deterioration adjustment;
- Risk Gate caps.

This is intentionally a portfolio/research synthesis, not the core asset Score.

### Audit implication

Confidence, valuation and Risk Gate are represented both indirectly inside/upstream of the public Score and explicitly again in Conviction. This is a **dependency overlap**, not automatically a bug.

Before changing Conviction weights, Phase 4/5 must decide whether this repeated emphasis is:
1. an intentional conservative gate; or
2. unwanted double-counting that distorts ranking.

No production change is justified from dependency overlap alone.

## 6. Best Opportunities is a Discovery layer

`scripts/opportunity_rank.py` is not a simple sort by Vestra Score.

It requires minimum evidence and combines:
- Vestra Score 19%;
- confidence 9%;
- moat 11%;
- capital-allocation intelligence 8%;
- QARP 14%;
- inverse value-trap risk 10%;
- sector-native score 5%;
- low-52 context 5%;
- recovery 7%;
- valuation 2%;
- timing 20%.

It also applies evidence gates/caps, Risk Gate caps, value-trap caps and overextension/timing caps.

This is semantically a **Discovery Engine**: “worth investigating now”, not “buy this” and not “best fit for the user's portfolio”.

### Audit implication

Confidence is used three ways in Best Opportunities:
- the public Vestra Score has already been reliability moderated;
- confidence receives a direct 9% component weight;
- confidence/coverage also gate and cap the opportunity result.

This may be a deliberate evidence-conservatism policy, but it is a clear repeated dependency that Phase 4/5 should test rather than silently preserve or remove.

## 7. Current pipeline order

The current production sequence is materially:

1. fundamentals + SEC/ESEF + derived fundamentals + capital-risk enrichment;
2. raw `score_universe()` / structural Risk Gate;
3. analyst evidence collection;
4. earnings intelligence;
5. evidence confidence -> `score_raw` + public `score`;
6. valuation overlay;
7. capital-allocation / moat / sector-native / value-trap overlays;
8. thesis classification/evolution;
9. catalysts / low-52 / drawdown / scanner;
10. late `postprocess_market.py` refreshes Best Opportunities after same-run recovery evidence exists.

This order is important because downstream layers consume already-moderated upstream fields.

## 8. Quantitative findings from the current score audit

Latest `data/score_audit.json` analysed 1,708 rows.

At the configured redundancy threshold |Spearman| >= 0.75:
- general: no redundant dimension pair flagged;
- growth-tech: Quality × Capital Allocation, Spearman 0.814;
- biotech: Cash Runway × Operating Quality, Spearman 0.765;
- energy, bank, utility, REIT and insurance: no pair above the threshold in the current snapshot.

These are **diagnostic flags, not reasons to delete a factor**. They need prospective/out-of-sample evidence.

The existing audit also shows material rank sensitivity to weight perturbations in several models. This reinforces the existing rule in `docs/score-validation.md`: do not tune production weights from a single cross-section.

## 9. Semantic contract for the next phases

Until a versioned redesign is validated:

- **Vestra Score** = cross-sectional asset-characteristic score, evidence moderated before publication.
- **Confidence** = reliability/completeness/freshness of evidence.
- **Risk Gate** = structural safety veto/cap, not a performance forecast.
- **Valuation** = peer-relative valuation overlay, not an independent factor from Score.
- **Conviction** = downstream research/portfolio synthesis.
- **Opportunity Score** = discovery/timing prioritisation, not portfolio fit.
- **Portfolio Decision Engine** = evaluates a proposed move in the actual portfolio context.

No UI or algorithm should describe any single one of these as an automatic buy/sell recommendation.

## 10. Phase 4/5 questions to answer before changing mathematics

1. Should public `score`, already confidence-moderated, still carry a separate 20% confidence weight inside Conviction?
2. Should Best Opportunities use confidence as both a component and a gate/cap, or should one role be enough?
3. How much valuation emphasis is intended when core Score already includes valuation and Conviction adds `valuation_signal`?
4. Do growth-tech Quality and Capital Allocation need de-correlation or is their current overlap economically intended?
5. Is biotech Cash Runway × Operating Quality overlap stable across future cohorts?
6. Should specialist-model dimensions use peer-first percentiles more consistently where sufficient peer counts exist?
7. Should missing-dimension re-normalisation have a minimum effective-dimension rule beyond the existing evidence gate?

Any change to those questions should be versioned, benchmarked against the current score, and subjected to prospective validation before production replacement.
