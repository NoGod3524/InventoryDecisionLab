# Reproducing the v2 strong-baseline and component-ablation experiment

The fixed scientific contract is [ablation_plan_v2.md](ablation_plan_v2.md), with machine-readable inputs in [../ablation_plan_v2.json](../ablation_plan_v2.json). The protocol was separately committed before new evaluation paths were generated. Preserve existing v1 reports and the full development grid, including failed candidates.

## Strategy mechanism

`inventory_lab.core.StrategySpec(predictor, buffer_multiplier)` makes forecast and buffer independent. `simulate(..., policy, strategy=spec)` retains an explicit policy identifier. Calling `simulate` without the new optional parameter retains v1 behavior exactly; tests compare the full ledgers of all three legacy strategies.

The v2 runner reads the strategy registry from the plan, passes every strategy through the same simulator, and uses the existing versioned SQL aggregation without adding policy-name branches. Reports enumerate all seven registry entries. Calibrated aliases reuse a predictor/z simulation if it is identical to a factorial arm; aliases remain separate reported rows and contrasts.

## Two separately committed freezes

The following commands illustrate the exact two-phase interface. The calibration commit must be the actual separate commit published after development, not the plan commit. Offline tools validate commit syntax and frozen bytes; verification that each remote commit exists and precedes the next execution is a separate publication responsibility.

```sh
python -m inventory_lab.ablation develop \
  --plan ablation_plan_v2.json \
  --plan-commit 72906cc5cd47fb2eb623660660b624af2a02cbe5 \
  --output output/ablation-v2-development
```

Review and publish `development_metrics.csv`, `development_summary.csv` and `frozen_calibration.json` as a separate immutable commit. The freeze records the exact plan hash, development seeds, per-seed input hashes, complete grid, selected or explicitly infeasible diagnostic parameters, CSV hashes, calculation-source hashes, and accounting audit count. Do not generate evaluation paths before this remote freeze is independently verified.

```sh
python -m inventory_lab.ablation evaluate \
  --plan ablation_plan_v2.json \
  --plan-commit 72906cc5cd47fb2eb623660660b624af2a02cbe5 \
  --calibration output/ablation-v2-development/frozen_calibration.json \
  --calibration-commit 82f0e03937a5c9ccdbd50f37cd0648493154b80c \
  --output output/ablation-v2
```

The runner refuses a nonempty output directory, overlapping seed splits, changed plan bytes, changed development CSVs, changed calculation sources, or an out-of-grid frozen multiplier. Changing calculation source requires preserving the prior freeze and publishing a corrected freeze before evaluation. Deliberate tuning after evaluation needs a new plan and fresh seeds, not an overwrite or silent rerun.

`source_code_sha256` includes the core simulator, existing SQL aggregation wrapper, v2 experiment code and report renderer. `sql_sha256` identifies the exact metric query. Full per-seed metrics and demand/catalog fingerprints allow deterministic reconstruction without committing large full-run ledgers. `representative_ledger.csv` retains the first seven days of the first evaluation seed for each distinct mechanism; every simulated ledger, including omitted days, is checked for accounting, cash, initial endowment, pipeline and receipt timing. A calibrated alias may share the representative mechanism's policy label.

## Reproduce the already-frozen evidence directly

Reviewers do not need to publish new commits or repeat development calibration to reproduce these exact results. From the repository root (including the custom ZIP), use the committed calibration and actual two freeze references:

```sh
python -m inventory_lab.ablation evaluate \
  --plan ablation_plan_v2.json \
  --plan-commit 72906cc5cd47fb2eb623660660b624af2a02cbe5 \
  --calibration examples/ablation-v2-development/frozen_calibration.json \
  --calibration-commit 82f0e03937a5c9ccdbd50f37cd0648493154b80c \
  --output output/ablation-v2-reproduced
```

Compare the newly generated CSV/report bytes with `examples/ablation-v2/`. This is deterministic reproduction of already-observed evidence, not another independent validation. New choices, scenarios or tuning require a new prospectively frozen protocol.

## Read the outputs

- `development_metrics.csv`: every development seed × forecast family × grid multiplier.
- `development_summary.csv`: service/cost/capital frontier on development data only.
- `frozen_calibration.json`: feasible selection or explicitly infeasible diagnostic fallback; a fallback is never deployment approval.
- `evaluation_metrics.csv`: every held-out seed × policy, with all cost components and capital measures.
- `evaluation_summary.csv`: mean, range, fill dispersion, passing count, Wilson interval and currency metrics. The `mean_mean_inventory_position_value_dollars` column is the across-seed mean of each seed's temporal mean; `mean_peak_inventory_position_value_dollars` is the across-seed mean of each seed's temporal peak.
- `paired_comparisons.csv`: candidate-minus-baseline contrasts. Fill effects are fractions in CSV and percentage points in the report. Five primary fill contrasts have 95% descriptive and 99% marginal Bonferroni intervals. Secondary cost/procurement/capital and interaction contrasts have only 95% descriptive intervals.
- `manifest.json`: freeze references, source hashes, per-seed input fingerprints, CSV hashes and validation counts.
- `RESULTS.md` and `report.html`: all policies, both calibration statuses, the entire development grid, service/capital trade-offs, primary and secondary contrasts, and limitations. The HTML works offline and makes no network calls.

Capital is acquisition-value on-hand plus already-paid pipeline at the end of each day. Shared initial assets and daily purchasing caps do not imply equal realized capital or equal service. All cost comparisons retain the common empirical service gate and report capital alongside fill.

## Tests without touching fresh evaluation data

```sh
python -m unittest discover -s tests -v
node tests/report_smoke.js
node tests/evidence_smoke.js
```

`test_ablation_core.py` and `test_ablation.py` use artificial arithmetic fixtures and already-public seeds 7, 17, 27 and 37 only. They check full legacy equivalence, no future leakage for every mechanism, budget/cash identities, initial-state fairness, calibration lexicographic selection and abstention, paired signs and seed alignment, undefined service, interval boundaries, capital accounting, two-phase isolation, frozen-file guards and byte-identical reproduction. They must never substitute seeds from the prospective evaluation range.
