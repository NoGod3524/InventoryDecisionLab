# Inventory Decision Lab: competition brief

## Decision question

For a small retailer, which replenishment rule can maintain an agreed unit-service level without exceeding purchasing-cash constraints? When no rule is reliable enough, which operational constraint should a manager test next?

The user of this product is an operations or business analyst reviewing purchasing policy, not an autonomous ordering agent. The deliverable is a decision gate, traceable evidence, and an actionable pilot hypothesis.

## Core finding

**Do not deploy the base configuration.** An independent 20-seed selection stage produced no policy satisfying the declared requirement: at least 95% fill in at least 90% of synthetic seeds. That abstention was frozen before the 30-seed held-out evaluation.

On those held-out base paths, the seasonal-buffer policy averages 95.92% fill but reaches 95% in only 70% of seeds. A mean above the target conceals unacceptable inconsistency. Fixed and rolling policies average 87.76% and 91.08%.

A previously narrower five-seed example looks substantially better. Keeping both makes the product's most important point: a favorable demo is not sufficient decision evidence.

## What a manager can do next

Two **predefined sensitivity scenarios**, not retrospectively validated replacements for the frozen base policy, indicate promising pilot directions:

| Conditional seasonal-buffer scenario | Mean fill | Seeds reaching 95% | Mean modeled operating cost, 180 days | Mean procurement spend |
|---|---:|---:|---:|---:|
| $18,000 daily allowance; 7-day review | 95.92% | 70% | $14,446 | $412,875 |
| $24,000 allowance; 7-day review | 98.55% | 100% | $6,791 | $427,351 |
| $18,000 allowance; 3-day review | 98.25% | 100% | $9,059 | $427,401 |

Increasing the review-day allowance by $6,000 (33%) is the clearest next hypothesis. Simulated 180-day procurement rises by about $14,476; this is purchasing more inventory to serve more demand, not an expense saving. The roughly $7,655 reduction in the modeled operating objective is dominated by an assumed shortage penalty and **is not realized profit**. Obtain working-capital approval and validate unit costs before any pilot.

More frequent reviews are another hypothesis, with a workflow burden and a modeling interaction: the daily allowance expires, so a shorter review cadence also grants more purchasing opportunities. It cannot be interpreted as a pure forecasting improvement.

Neither 30/30 simulated passes nor bootstrap intervals guarantee real-world service. A future pilot needs fresh evaluation periods and measured demand/stockout data.

## External-data challenge

A verified public UCI Online Retail workbook (541,909 rows) was parsed directly using Python's standard library. Training: 2010-12-01 through 2011-01-25. Evaluation: 2011-01-26 through 2011-07-24. Twenty-four SKUs were selected using training gross positive quantity only, in the United Kingdom subset.

In one deterministic hypothetical replay, seasonal buffering fulfills 85.98% of recorded positive sales versus 71.50% for the fixed policy and 71.14% for the rolling policy. No method approaches a 95% gate. This is an external-data challenge that weakens any blanket recommendation, not proof of real operational benefit.

Inventory availability, latent demand, lead times, supplier purchase prices and real lost sales are unavailable. Acquisition costs are a disclosed 50% fraction of training selling prices; other operating parameters are hypothetical. The replay models ability to serve recorded gross sales, not true historical demand. Customer IDs are not exported. Cancellations and adjustments are separated from positive sales. Published evidence is aggregated; local row-level provenance remains available on reproduction.

## Audit-driven data-quality sensitivity

The gross replay contains a 74,215-unit training order for SKU 23166 with a same-day complete cancellation. Keeping that positive row while merely separating its cancellation makes the SKU rank first and heavily distorts initial inventory. The gross replay therefore is a **data-quality challenge, not external validation of the policy**.

After that discovery, a separate [diagnostic rule](quality_sensitivity_plan.json) was recorded before its results were computed: match complete same-day cancellation/sale pairs on SKU, exact price, exact quantity, country and the same nonempty customer identifier; consume each row once in source-row order. Customer identifiers are used only in temporary matching keys and are not exported. Partial, different-day or unlinked cancellations are not netted arbitrarily.

The rule matches 336 pairs and 82,657 positive units in the configured country/window. It then rebuilds all daily sales, reselects 24 SKUs using training only, and recalculates cost proxies and initial stock. SKU 23166 leaves the selected set. Seasonal buffering moves from 85.98% to 86.06% recorded-sales fulfillment, still below 95%; its hypothetical acquisition spend changes from £170,761 to £137,857 and mean inventory per SKU from 3,807 to 920.

This is **post-hoc data-quality sensitivity**, not an originally preregistered independent validation. Because the selected catalog and demand denominator change, those differences are not controlled causal savings estimates. Full invoice correspondence cannot be proved from these matching fields. The service failure survives the diagnostic, while working-capital estimates prove highly data-sensitive. Both results are retained side by side.

## Contribution

- A business decision that can explicitly abstain rather than always recommend a policy
- Fair policy comparisons using shared exogenous demand, initial conditions, budget allocation and review calendars
- Independent selection and evaluation seeds, conditional paired uncertainty, and 12 declared sensitivity regimes
- SQL-derived metrics with underlying ledger and source/configuration fingerprints
- Explicitly different evidence modes: synthetic ground truth versus real recorded-sales replay
- An offline report and a dependency-free, reproducible workflow

The project does not claim to invent replenishment theory or a new forecasting method. Its contribution is the transparent decision workflow and evidence controls.

## Pilot plan and success criteria

1. Collect SKU-level on-hand stock, receipts, requested vs fulfilled orders, observed demand or defensible lost-demand estimates, supplier delays, and actual purchasing/holding costs.
2. Agree on service targets, approved purchasing-cash limits, and a credible shortage-cost range before evaluating candidate policies.
3. Choose between budget-cap and review-process interventions using operational feasibility, not just the cheapest simulated penalty total.
4. Predeclare the policy, allocation rule, comparison periods and stopping conditions; retain an unchanged baseline.
5. Run shadow recommendations before live ordering. Move to a bounded prospective pilot only after inventory accounting and approvals work.
6. Report achieved service, actual cash use, operational labor and confidence bounds. Stop if the service or cash guardrails fail.

## Submission positioning

This is a general business-analytics submission package. A named competition's rubric, eligibility, page limits, required slides and data-use terms still need to be applied before actual submission. No award or placement is promised.
