# v3 minimum-budget study: reproduction and freeze checks

The immutable methods contract is [minimum_budget_plan_v3.md](minimum_budget_plan_v3.md); its canonical machine path is `docs/minimum_budget_plan_v3.json`. This study changes the purchasing allowance only. It does not overwrite the original v2 failure or claim a same-budget algorithm improvement.

## Frozen model and development search

`inventory_lab.budget_search` reuses the original frozen v2 `score_strategy`, simulator and SQL. It checks their hashes against `examples/ablation-v2-development/frozen_calibration.json` before executing. The fixed policy class contains rolling and weekday order-up-to policies, both with z=3.29.

All 90 previously observed v2 paths are development history, divided into the three declared 30-path cohorts. One policy must achieve at least 27/30 separately in every cohort. The search completes both policies and all 90 paths at each budget, ascends the declared $100 grid without gaps, and stops only after the first qualifying grid point or exhaustion. It assumes no monotonicity. At the first qualifying budget, mean modeled cost, mean inventory capital and policy ID break ties.

```sh
python -m inventory_lab.budget_search develop \
  --plan docs/minimum_budget_plan_v3.json \
  --plan-commit e0428a808e52bcdd9827e0ebea9653b39ef2b428 \
  --output output/minimum-budget-v3-development \
  --workers 4
```

Workers only parallelize independent simulations inside one budget level. Results retain input order, and tests verify that serial and parallel runs produce identical files. No new external task environment or third-party Python package is required.

## Second freeze before fresh confirmation

Publish the full visited grid and `frozen_budget_selection.json` with unchanged calculation source in a separate remote commit. Independently verify that commit and its bytes before confirmation. The frozen record contains the selected policy/budget, all visited levels, input fingerprints, full cohort outcomes at the chosen budget, source hashes and CSV hashes. If no budget qualifies, both selection fields are null and the runner refuses to generate confirmation paths.

The `confirm` command requires `--plan`, `--plan-commit`, `--freeze`, `--budget-freeze-commit`, a new `--output` directory and optionally `--workers`. The published result's manifest supplies the actual second freeze reference. Confirmation independently reconstructs the development choice from the complete CSV grid before generating any new paths. It refuses skipped lower levels, continuing beyond an earlier qualifying level, tampered grid bytes, changed computational sources, or a different selected budget/policy.

Both predeclared fresh 30-path cohorts are evaluated regardless of the first cohort's outcome. The same frozen policy is run at the selected budget and at the original $18,000 allowance on each path. The candidate must pass at least 27/30 in each cohort. Failure is preserved; it cannot trigger unrecorded retuning on those paths.

## Artifacts

- `development_metrics.csv`: every visited budget × both policies × all 90 development paths.
- `development_summary.csv`: service, Wilson interval, all cost components and inventory capital for each budget/policy/cohort.
- `frozen_budget_selection.json`: the independently published second freeze.
- `DEVELOPMENT.md`: complete searched-grid results, including every unsuccessful lower budget.
- `confirmation_metrics.csv`: both budget arms for every fresh path, with the selected policy ID retained.
- `confirmation_summary.csv`: candidate and original-budget results for each fresh cohort, including individual pass/fail status.
- `paired_comparisons.csv`: selected minus original budget for the same policy on the same 60 paths. Four 95% percentile-bootstrap intervals are descriptive, not multiplicity-adjusted.
- `manifest.json`: actual freeze references, source and artifact hashes, input fingerprints, confirmation gate status and validation checks.
- `RESULTS.md` and `report.html`: clearly attributed budget changes, scoped minimum claim, fresh confirmation results, capital/procurement costs and preserved v2 failures.

Output directories must be new or empty. Full numerical outputs are deterministic; timing and filesystem modification dates are not evidence of prospective freezing.

## Tests without prospective-path leakage

```sh
python -m unittest discover -s tests -v
node tests/report_smoke.js
node tests/evidence_smoke.js
```

Budget-study tests use only tiny artificial cases and old public seeds 7, 17, 19, 27, 37 and 47. They check cohort-wise gating, same-policy requirements, tie breaks, undefined service, non-monotone search behavior, complete lower-grid coverage, infeasible abstention, phase isolation, independent choice reconstruction, both-cohort completion, source guards and serial/parallel reproducibility. The new confirmation seed ranges are never used in unit tests.
