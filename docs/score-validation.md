# Vestra Score — validation standard

The Vestra score is an explainable screening model, not a return forecast. Production weights must not be changed merely because a different blend looks intuitively better in one current cross-section.

## Evidence already consistent with the model

The broad factor families used by Vestra have a reasonable research basis:

- profitability / operating quality;
- value;
- conservative balance-sheet / financing behaviour;
- earnings quality and cash conversion;
- disciplined share issuance / capital allocation;
- lower risk / stability as a quality characteristic.

This is directionally consistent with the profitability evidence associated with Novy-Marx, the profitability/investment factors in Fama–French, and the multi-component quality framework commonly described as profitability, growth, safety and payout discipline.

That does **not** validate Vestra's exact metrics or weights. Academic factor results are portfolio-level historical evidence; Vestra is a heterogeneous company-level screening system with specialist sector packs and missing-data re-normalisation.

## Important caveats

1. **No exact weight has scientific status yet.** The current vectors are product priors.
2. **Accrual quality is useful context, not a guaranteed anomaly.** Later research found that the classic accrual return anomaly weakened materially, so earnings-quality signals should not receive weight simply because an older anomaly once existed.
3. **Sector normalization is incomplete.** REIT, insurance, utility, energy and biotech packs use many model-specific peer comparisons, but some inherited components (for example growth, stability or interest coverage in certain packs) may still have been ranked against the full equity universe. This can create structural sector effects.
4. **Missing-data re-normalisation changes effective weights.** Two companies with the same named model can have different effective factor exposure when dimensions are absent.
5. **Current cross-sectional fit cannot establish predictive validity.** Any weight tuning from today's data alone risks overfitting.

## Required diagnostics before a production weight change

`scripts/score_audit.py` runs on every validated market build and records:

- dimension availability by score model;
- effective number of dimensions used;
- Pearson/Spearman dependence between dimensions;
- redundancy flags for |Spearman| >= 0.75;
- score-rank sensitivity when each real model weight is independently changed to 0.5x, 0.8x, 1.2x and 1.5x;
- top-decile membership stability;
- sector representation in the production top decile;
- agreement between the stored production score and a reconstruction from the emitted `score_dimensions`.

This audit is diagnostic only and never changes production scores.

## Prospective validation

`scripts/score_forward_validation.py` stores one weekly observation of the score that was actually available at that date, together with current price and model context. Future runs evaluate realised returns after approximately:

- 4 weeks (28 days);
- 12 weeks (84 days);
- 24 weeks (168 days).

For each horizon the report calculates:

- cross-sectional rank information coefficient (Spearman score vs subsequent return);
- mean return of the highest score quintile;
- mean return of the lowest score quintile;
- top-minus-bottom return spread.

This avoids reconstructing today's model backwards onto old prices and therefore provides genuine out-of-sample evidence from the date the validation system is introduced.

## Decision rule

Do not optimize weights until there are multiple independent cohorts and enough observations to assess stability by horizon and, where sample size permits, by sector/model. Prefer changes that:

- improve or preserve rank IC across more than one horizon;
- improve top-minus-bottom separation without extreme sector concentration;
- remain robust to modest weight perturbations;
- reduce redundant factor exposure rather than double-counting similar information;
- improve economic interpretability;
- do not lower data coverage or create incentives to reward missing information.

A proposed model should be evaluated out of sample before replacing the production model. The existing score should remain the control until evidence is strong enough to justify a versioned change.
