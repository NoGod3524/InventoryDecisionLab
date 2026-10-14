# v3: minimum qualifying budget in a fixed strategy class and $100 grid

Status: prospective simulation-only extension, to be published in a separate immutable plan commit before the new budget search or generation of fresh confirmation paths. No real purchases or financial commitments are authorized by this experiment. The user approved researching a higher simulated procurement allowance after the original setting was proved incapable of passing its specified 27-of-30 target.

## Motivation and cumulative disclosure

The original v2 development and evaluation evidence remains unchanged, including both null deployment choices, the 26/30 development result, and 45/60 evaluation passes. A later exact-integer capacity relaxation proves that four original development paths cannot reach95% at the $18,000 allowance and original calendar, even with favorable perfect-information assumptions. A time-indexed LP corroborates that finding. Consequently, this extension changes a resource constraint; it is not an algorithm-only repair of the original setting.

All90 previously observed v2 paths are now development data for v3, including the60 formerly labeled held-out. They must never again be described as unseen validation for this budget search. The known $18,062.47 necessary budget lower bound is not sufficient and does not establish the required final allowance.

## Fixed variables and search class

Retain original generator,24 SKUs,56 training days,180 evaluation days, SKU lead times4–6,seven-day review schedule,$2.50 SKU-order fee,daily holding5 basis points,$9 shortage penalty, full-demand visibility, no budget carryover, original initial-stock formula and empty initial pipeline. Retain the same allocation/tie-break rule. Unit fill target remains95%; passing a30-seed block requires at least27 seeds.

Only the uniform procurement allowance available on each review day changes. There are26 scheduled review opportunities; increasing this allowance changes accessible operating resources. Initial stock remains independent of the allowance and identical for all compared arms.

Two candidate policies are fixed before this search:
- rolling_base_stock_z329: trailing28-day mean protection forecast plus3.29×population standard deviation of raw trailing28-day demand×sqrt(protection).
- seasonal_base_stock_z329: corresponding weekday forecast plus exactly the same buffer.

Protection, history indexing, ceil rounding, current-day observation, lead timing, inventory-position ordering and budget allocation are numerically identical to frozen v2. Multipliers3.29 were selected as v2 diagnostic fallbacks and are not retuned at any budget. No added predictors, allocators, windows, seed filtering or thresholds enter this search.

## Development cohorts and budget grid

Use these three already observed development blocks:
- original_v2_development:20000–20029
- former_v2_evaluation_A:30000–30029
- former_v2_evaluation_B:30030–30059

A candidate must achieve≥27/30 in EACH block using the same policy and allowance. This three-block development qualification is deliberately stronger than merely fitting the original30; the final reported minimum is conditional on this declared qualification. Report the original30 result separately so the user's27-of-30 target remains visible.

Search budget cents from1,800,000 through3,000,000 inclusive in increments of10,000 ($18,000–$30,000 in $100 steps). Visit budgets in strictly ascending order. At each visited allowance evaluate both policies on all90 paths and retain all rows. The first allowance for which at least one policy passes all three blocks is the minimum qualifying allowance on this declared grid and two-policy class. Evaluate both candidates completely at that allowance before selecting.

Choose among qualifying policies at that allowance by minimum mean modeled operating cost across90 seeds, then minimum mean inventory-position value, then lexical policy identifier, using unrounded values. Mean inventory-position value includes on-hand plus paid pipeline at acquisition cost. The objective remains holding+fees+assumed shortage penalty; acquisition spend is reported separately. No candidate can qualify by averaging away a failing block.

Ascending exhaustive evaluation of all LOWER grid points is required; do not use binary search, assume monotonicity, stop a candidate early on its first failing seed, or skip lower levels. Stop higher-budget search at the first qualifying level; that is the declared minimum-finding algorithm, not optional stopping on fresh validation. If no candidate qualifies through$30,000, publish the complete failed search and do not generate fresh confirmation paths. Any expansion then requires a separately documented prospective amendment; no outcome is manufactured.

This is NOT a global optimum over all algorithms, continuous-dollar allowances, review calendars or forecasts. Budgets between grid points are untested. There is no claim that the previous $100 grid point is mathematically impossible for other policies.

## Two publication gates and fresh confirmation

1. Publish this plan and its machine JSON in their own remote commit, verify bytes, and record the commit reference before running v3 budget search. Implementation tests may use artificial fixtures or old/public seeds only.
2. After the development search, freeze the chosen budget/policy, full searched grid, per-seed data, all block summaries, plan/input/code/SQL hashes and selection reason in a second remote commit. Verify it remotely before generating fresh confirmation data.

Fresh blocks, fixed now and never generated before the second gate:
- confirmation_A:40000–40029
- confirmation_B:50000–50029

Run BOTH blocks under the unchanged frozen selected budget and policy, regardless of the first block's result. Overall confirmation passes only if BOTH blocks independently achieve≥27/30. Also evaluate the identical selected policy with the original$18,000 cap on the same paths, for a paired resource-intervention comparison. This baseline is not an alternative choice. Do not change the budget, policy or data after examining either block, choose the better block, or relabel a failure as validation success. Any subsequent redesign must preserve this result and use a new prospective plan; do not silently refresh seeds.

## Outputs and uncertainty

Retain complete development per-seed and cohort/candidate/budget summaries, frozen selection, confirmation per-seed metrics, per-block summaries and pooled descriptive summary, paired differences, machine manifest, results memo and offline report. Required metrics include fulfillment/demand/loss, passing count, mean/min/max fill, modeled-cost components, procurement, initial asset value, mean/peak on-hand+paid-pipeline value and terminal inventory/pipeline value. Check shared demand and initial stock, cash including fees, flow conservation and deterministic regeneration.

Report empirical passing counts with two-sided95% Wilson intervals, separately for each30-seed block. Wilson intervals do not redefine the empirical27/30 gate or imply a population reliability guarantee.

For the selected-budget versus original-budget comparison, report paired seed-level mean differences with deterministic10,000-resample percentile bootstrap,RNG seed913,using floor(q×(draws−1)) indexes for2.5% and97.5%. Do this for fill, modeled cost, procurement and mean inventory-position capital on the pooled60 confirmation seeds. These four intervals are descriptive, conditional on the generator and not multiplicity-adjusted. Undefined fills never pass; paired undefined metrics are excluded and counted. Do not present repeated SKU-days as independent evidence.

## Interpretation and completion

A successful result is a minimum qualifying DEVELOPMENT grid allowance for these two fixed policies, followed by two successful fresh30-seed confirmations of the frozen choice. Confirmation does not establish that this budget is the minimum in a real business or that all lower budgets fail on every new population. The study changes purchasing resources and remains hypothetical; there are no realized savings or deployment approvals.

If confirmation fails, report failure prominently and retain the chosen development optimum and all evidence. The task cannot be honestly completed by lowering95%, dropping hard paths, adding free stock, hiding fees, or testing until an attractive fresh sample appears. Operational constraints and cumulative testing history must remain explicit.
