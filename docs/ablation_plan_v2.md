# InventoryDecisionLab v2: prospective plan for strong baselines and component ablation

Status: fixed before new evaluation execution; requires its own remote commit. This is a prospective extension of an already-explored simulator, not an originally preregistered study, blinded research, or proof that its authors have never explored similar hypotheses.

## Why this experiment is needed

The published v1 comparison changed two components together: weekday forecasts and safety inventory. A post-hoc audit on the already-public evaluation seeds found that rolling mean plus the same buffer nearly reproduced seasonal-buffer performance. Those results motivate this plan; the old seeds (including 100–119 and 1000–1029) are development history, never fresh confirmatory evidence. The question is which component contributes under the stated simulator, and whether a calibrated ordinary periodic order-up-to baseline is competitive.

## Version and execution gates

1. Publish this document and the unchanged machine plan in a separate GitHub commit before generating, reading, or evaluating any new evaluation demand paths. Record the actual commit SHA and verify the files match locally. The plan contains no claimed completion timestamp.
2. Implement and test using tiny artificial fixtures or old/public seeds only. Development data below may be generated after the plan commit is verified. Do not inspect evaluation seeds to select algorithms, fix a preferred effect size, choose a window, or tune parameters.
3. Run development calibration. Save the complete grid, selected/fallback parameters, configuration and input hashes, source-code hashes, and plan SHA-256. Publish the frozen calibration artifact in a second separate commit before evaluation. If no candidate passes the declared feasibility gate, retain that failure; do not expand the grid after seeing it.
4. Run the evaluation exactly once under frozen specifications. Safe reproduction to verify deterministic artifacts is allowed. An implementation error requires a documented correction, its effect on earlier evidence, and preservation of the prior result; any outcome-driven tuning requires a new prospective plan and new seeds.
5. No old result, empty directory, self-asserted boolean, or artifact file mtime proves a prospective chronology. Store actual immutable commit references and a transparent execution record.

## Fixed environment and shared operating constraints

Use the original synthetic generator, Config and event timing: 24 SKUs; 56 observed training days; 180 evaluation days; base SKU leads 4–6 days; review every 7 days; per-review-day accessible budget $18,000 including order fees; $2.50 per SKU-order; daily holding 5 basis points; shortage penalty $9/unit; demand scale 1.0; service target 0.95.

Initial on-hand stock remains ceil(training mean × (lead + review − 1)) for every policy, with zero initial pipeline. All policies observe the same complete demand history, including lost demand, use the same calendar, budget allocator and deterministic tie breaks, and receive the identical catalog and demand within each seed. Protection period H = lead + review − 1. No demand/model/scenario/window change is part of this study. Cash allocation, no carryover, free initial endowment and incomplete economic accounting remain limitations.

Development seeds: 20000–20029 inclusive (30 independent catalogs/paths). Evaluation seeds: 30000–30059 inclusive (60). A per-seed 56-day training prefix is distinct from cross-seed development calibration; a policy can update only through today's observations. No evaluation path is generated for even a smoke test before both execution gates pass.

## Strategy definitions

Let m be mean of the last 28 observed daily demands, s their population standard deviation, and H protection days. Define rolling forecast F_r = mH. Weekday forecast F_s sums the corresponding weekday's mean among the last 28 observations for each of the next H days, using existing v1 indexing. For a scalar z, target = ceil(F + z s sqrt(H)); order max(0, target − current inventory position), subject to the unchanged allocator/budget.

The use of raw demand dispersion is retained across cells to isolate components and preserve v1 equivalence. It is not a theoretically calibrated forecast-error quantile. No cell changes dispersion estimator, history window, weekday convention, timing, allocation or initial capital.

Policies:
- fixed_periodic: original frozen 56-day mean target, no buffer; retained as legacy context.
- rolling_no_buffer: F_r, z=0.
- rolling_buffer: F_r, z=1.28.
- seasonal_no_buffer: F_s, z=0.
- seasonal_buffer: F_s, z=1.28; numerically identical to v1 seasonal_buffer.
- calibrated_base_stock: periodic order-up-to F_r with z chosen exclusively on development data.
- calibrated_seasonal: F_s with z chosen on exactly the same grid, development data and decision rule.

The four uncalibrated cells form the component 2×2. The two calibrated policies answer the fairer comparison of tuned ordinary versus tuned weekday rules. Calling the baseline strong means it receives the same calibration opportunity; it does not mean globally optimal, theoretically novel, or guaranteed feasible.

## Calibration and abstention

For each forecast family independently, evaluate z ∈ [0, 0.64, 1.28, 1.96, 2.58, 3.29] on all 30 development seeds. Reuse identical predictor/z simulations rather than duplicating them for aliases. Record every grid result, including failures.

A grid candidate is empirically feasible only if at least 27/30 seeds have unit fill ≥0.95. Undefined fill never passes. Among feasible candidates choose minimum mean modeled operating cost, then minimum mean inventory-position value, then smaller z. These are lexicographic comparisons on unrounded computed values. Inventory-position value is end-of-day on-hand plus paid pipeline units, valued at each SKU's acquisition cost. The choice is a development decision, not a confidence guarantee.

If none is feasible, deployment_choice is null. To keep the comparison informative, freeze a diagnostic candidate by maximum passing-seed count, then maximum mean defined fill, then minimum mean modeled cost, then smaller z. With no defined fill, its ordering value is −infinity. Label this as an infeasible diagnostic fallback everywhere. It must not become a recommended policy or be silently described as meeting the service target. Evaluation uses this already-frozen fallback for the policy's diagnostic row and contrasts. A family with an entirely undefined development sample remains non-deployable.

Calibration is the only tuning in this plan. There is no grid expansion, evaluation-based z selection, or selection of a favorable scenario. If neither family is feasible, report that directly rather than making this task's completion depend on manufacturing a winner.

## Metrics and service/capital comparability

Per seed/policy retain unit demand, fulfillment, lost units, fill, order count, procurement, holding, fees, shortage, modeled operating cost, constrained reviews, average on-hand units; additionally report initial on-hand acquisition value, mean and peak end-of-day (on-hand + paid pipeline) acquisition value, terminal on-hand value, and terminal pipeline value. All USD values derive from exact SKU unit costs; money units are explicit.

Strategies share the same starting assets, procurement opportunities and cap. They do not necessarily use the same realized working capital or achieve identical fill. The common service gate enables conditional cost comparison, while a fill-versus-capital chart/table shows trade-offs. Do not assert an equal-capital causal effect or equal-service savings from unmatched realized outcomes. Show all development grid points and their observed feasibility so readers can inspect the service/capital frontier; the grid is descriptive development evidence, not an evaluation-selected frontier.

Report mean and seed distribution of service, passing count/60, modeled cost, procurement and capital. Feasible deployment status remains a separately frozen development result. Evaluate whether that choice continues to meet the empirical service gate; a failure must be prominent. Do not pool SKU-days as independent samples.

## Comparisons and uncertainty

The unit of inference is a seed (shared catalog and demand path). Every contrast uses candidate minus comparator within the same seed. Five primary fill contrasts are fixed:
1. seasonal_no_buffer − rolling_no_buffer (weekday contribution without buffer).
2. seasonal_buffer − rolling_buffer (weekday contribution with equal buffer).
3. rolling_buffer − rolling_no_buffer (buffer contribution within rolling).
4. seasonal_buffer − seasonal_no_buffer (buffer contribution within weekday).
5. calibrated_seasonal − calibrated_base_stock (equal tuning opportunity).

Use deterministic percentile bootstrap of seed-paired differences: 10,000 resamples; RNG seed 913; lower/upper indexes floor(q×(draws−1)). Report point estimate and 95% interval for each. Additionally report 99% intervals for these five primary fill comparisons, a Bonferroni nominal family-wise 95% construction. Percentile bootstrap coverage is approximate and conditional on this generator; no guarantee of exact family-wise control is claimed. A CI containing zero is not evidence of equivalence. If costs or service trade off, say so.

Secondary descriptive outputs: the factorial interaction (seasonal_buffer−seasonal_no_buffer)−(rolling_buffer−rolling_no_buffer); paired modeled cost, procurement and mean/peak capital differences for the same five policy pairs; 95% paired bootstrap intervals. Do not promote these to multiplicity-adjusted confirmatory endpoints after looking at results. For undefined fills retain paired-valid and undefined counts; compare only pairs with both metrics defined, and the interaction only seeds with all four defined.

Report passing proportions with 95% Wilson intervals (z=1.959963984540054), explicitly separate from empirical ≥90% feasibility. No lower-confidence-bound deployment rule is added retroactively. Do not claim 60/60 observed passes proves real-world reliability.

## Artifacts and reproducibility

Required outputs: complete development per-seed grid metrics; development candidate summary/frontier; frozen calibration JSON; evaluation per-seed policy metrics; evaluation summary; primary and secondary paired comparisons including contrast and interval definitions; report/method memo; manifest with plan bytes hash, remote plan and calibration commit references, code/SQL hashes, parameter freeze hash, input hashes, CSV hashes and validation results. Report deterministic seeds and versions, with no absolute local path needed to reproduce numerical artifacts.

The full evaluation ledger may be omitted to control artifact size if deterministic reproduction instructions and per-seed input fingerprints/metrics are retained. Include a representative ledger audit and automatically validate accounting, budget including fees, matching initial conditions, equal demand and no-future-leakage for all simulated strategies. Manifest validation must fail loudly if inputs or frozen parameters differ from the declared plan.

## Acceptance and interpretation

Completion means: validated 2×2 implementation; strong calibrated baseline with equal tuning opportunity; development freeze publicly recorded before new evaluation; completed fresh-seed paired evaluation; accurately regenerated documentation and artifacts; tests and release checks pass. It does not require seasonal superiority, feasibility, significance, deployment or a favorable numerical outcome.

This study identifies components within the fixed simulator. The earlier UCI replay remains a separately labeled post-hoc historical-sales diagnostic. This extension does not turn missing real inventory/supplier/demand data into causal business evidence or claim a competition result.
