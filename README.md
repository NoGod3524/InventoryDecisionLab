# Inventory Decision Lab

**A reproducible, offline-first inventory decision experiment using Python + SQL.**

> Which replenishment policy meets an agreed service level at the lowest modeled operating cost, and when do cash and supplier constraints make that target infeasible?

Compare transparent replenishment rules across the **same demand paths**: the preserved v1 has three policies, and the v2 extension adds seven fixed specifications for strong-baseline and component-ablation analysis. Explore a self-contained HTML report, inspect every movement in SQLite/CSV, and reproduce the results without API keys, accounts, data downloads, or third-party Python packages.

**All published results are simulated. This is an auditable business-analytics research project, not a production ordering system or evidence of real retailer savings.**

## v2: strong baselines and component ablation

The new [v2 results](examples/ablation-v2/RESULTS.md) and [offline report](examples/ablation-v2/report.html) separate the weekday forecast from its safety buffer using a 2×2 design, and give rolling and weekday policies the same development calibration opportunity. The [plan](ablation_plan_v2.json) and [calibration](examples/ablation-v2-development/frozen_calibration.json) were separately committed before evaluating 60 new seeds. All v1 evidence below is preserved.

- Adding the same 1.28 buffer to rolling mean improves mean fill by **4.664 percentage points**. With that buffer held fixed, weekday forecasts add **0.110 points** (99% paired interval +0.047 to +0.168).
- After equal-opportunity calibration, weekday versus ordinary periodic base-stock differs by **+0.012 points**, with a 99% interval of **−0.049 to +0.073**. This does not establish superiority or equivalence.
- Neither calibrated family met the development feasibility gate: both topped out at **26/30**, short of 27/30. Their frozen z=3.29 diagnostic fallbacks subsequently passed in only **45/60** evaluation seeds, short of 54/60. **Both deployment choices remain null.**

These are conditional simulator findings. Shared starting assets and purchasing caps do not imply equal realized inventory capital; [the report](examples/ablation-v2/report.html) shows the service/capital trade-off and complete development grid. The five primary fill contrasts use 99% marginal percentile-bootstrap intervals as an approximate Bonferroni nominal 95% family; other contrasts are descriptive. See [exact reproduction and freeze checks](docs/ablation_v2.md).

## Start with the decision, not the demo

**The preserved v1 held-out result is “do not deploy the base configuration.”** Separate 20-seed policy selection found no policy meeting the predeclared gate (95% fill in at least 90% of seeds). The frozen decision was evaluated against 30 new seeds and 12 predefined sensitivity scenarios. Seasonal buffering averages 95.92% base fill but reaches 95% in only 70% of held-out seeds.

A $24,000 procurement allowance or a 3-day review schedule is a promising **predefined sensitivity finding**, not a new independently validated deployment choice. The real UCI-sales replay also challenges transferability: the gross replay reaches 85.98%, and an audit-driven exact-cancellation diagnostic reaches 86.06%; neither supports deployment. The large canceled training order makes the gross replay a data-quality challenge, not external validation.

### Reviewer routes

- **3 minutes:** start with [v2 ablation results](examples/ablation-v2/RESULTS.md), then read the preserved v1 [competition brief](docs/competition_brief.md), open [held-out report](examples/robustness/report.html), then inspect [gross UCI replay](examples/uci-replay/report.html) alongside the [matched-cancellation diagnostic](examples/uci-matched/report.html).
- **15 minutes:** run the tests, inspect [experiment plan](examples/robustness/experiment_plan.json), [frozen selection](examples/robustness/frozen_selection.json), [paired comparison CSV](examples/robustness/paired_comparisons.csv), and [methodology](docs/methodology.md).
- **Deep reproduction:** rerun the 20+30-seed experiment and official-workbook replay using the commands below. Compare configuration, source and CSV hashes. No paid service or API key is needed.

GitHub displays HTML source. Download/open reports locally, or use the public HTTPS demo if linked by the repository maintainer. Browser-control checks in this repository are DOM-stub tests, not a claim of browser visual acceptance.

## Held-out experiment

```sh
python -m inventory_lab.experiments --output output/robustness
```

This runs 20 independent selection seeds and 30 held-out seeds × 12 scenarios × 3 policies, with 2,000 paired bootstrap resamples for each candidate-minus-fixed comparison. It writes the declared plan before execution and freezes the selection before evaluation. All intervals describe Monte Carlo variation under the synthetic model; they do not establish real-world uncertainty or significance across multiple comparisons.

Read [full results](examples/robustness/RESULTS.md). The five-seed examples below are a quick walkthrough, not the deployment decision.

## Actual public-data replay

The official [UCI Online Retail](https://archive.ics.uci.edu/dataset/352/online+retail) workbook has been downloaded, SHA-256 checked, and parsed: **541,909 source rows**. The committed aggregate [replay evidence](examples/uci-replay/) uses 24 training-selected SKUs and a held-out date window. No customer identifiers are exported. The diagnostic identified 336 complete same-day cancellation pairs (82,657 positive units), then fully retrained the catalog and assumptions. It is explicitly post-hoc, preserves the original gross baseline, and does not claim causal savings.

```sh
# Download the official ZIP from UCI and extract Online Retail.xlsx into data/.
# Verify the hashes documented in docs/real_data.md, then run:
python -m inventory_lab.replay --input "data/Online Retail.xlsx" --output output/uci
python -m inventory_lab.replay --input "data/Online Retail.xlsx" \
  --cancellation-policy same_day_exact --output output/uci-matched

# Small self-authored schema fixture, clearly labeled as NOT actual UCI data:
python -m inventory_lab.replay --input tests/fixtures/retail.csv \
  --start-date 2020-01-01 --skus 2 --warmup 28 --days 4 --fixture \
  --output output/fixture
```

Recorded positive sales are not latent demand. Inventory, supplier terms, acquisition costs and shortage outcomes are hypothetical. Prices and replay outputs are GBP, not USD. One historical path is not duplicated into fake independent seeds. See [the data contract and licenses](docs/real_data.md).

## Try it in one minute

Requires Python **3.10+**, including the standard `sqlite3` module. Run from the repository root:

```sh
python -m unittest discover -s tests -v
python -m inventory_lab --output output/my-first-run
```

Open `output/my-first-run/report.html` in a browser. It works directly from disk without a server or internet connection. The report includes seed selection, service-target gating, a service/cost plot, daily inventory, CSV download, and an audit manifest.

You can also immediately open the committed [base report](examples/base/report.html), [stress report](examples/stress/report.html), or read the [base decision memo](examples/base/decision_memo.md). GitHub displays HTML source; download/open the file locally to use the interactive report.

The output folder must be empty or new; existing files are never overwritten.

## Actual example results

Generated by the committed code: 24 SKUs × 180 evaluation days × 5 seeds (`7,17,27,37,47`), with 56 preceding training days. Values below are means across independent synthetic seeds. Each policy sees identical demand within a seed.

| Scenario / policy | Unit fill | Modeled cost (USD) |
|---|---:|---:|
| Base · fixed periodic | 88.11% | $36,660.95 |
| Base · rolling mean | 92.33% | $24,542.01 |
| Base · seasonal + buffer | 97.76% | $9,193.37 |
| Stress · fixed periodic | 61.23% | $114,083.32 |
| Stress · rolling mean | 60.99% | $114,810.11 |
| Stress · seasonal + buffer | 62.21% | $111,299.41 |

Base assumptions: lead times 4–6 days, review every 7 days, daily procurement allowance $18,000. Stress: lead times 9–11 days and allowance $10,000. Both use a $9/unserved-unit penalty and $2.50/order fee. The allowance is reset daily; unused money does not roll over. Since orders occur only on review days, non-review-day allowances are unused.

**Walkthrough-only gate:** seasonal buffering meets 95% fill in each of these five base seeds, and none does in the stress seeds. The broader independent selection/evaluation study above does **not** support base deployment. This contrast is retained to show why a favorable small demo is insufficient.

These are not causal estimates, real-world savings, forecasts of retailer performance, or profit calculations. The generator contains weekly seasonality, so a seasonal policy has a deliberately favorable structural opportunity. The stress result demonstrates that better forecasting cannot remove a severe purchasing constraint.

## Policies

All policies order after observing demand on review days, use inventory position (closing stock + outstanding orders), and follow the same budget-allocation rule.

1. **Fixed periodic:** frozen training mean × (lead time + review period − 1), replenishing to that stock target.
2. **Rolling mean:** trailing 28-day observed-demand mean × the same protection period.
3. **Seasonal + buffer:** forecast each protection-period day using its weekday's observations from the past 28 days; add `1.28 × recent standard deviation × sqrt(protection days)`.

The third buffer is a heuristic, **not** a calibrated 90% or 95% service guarantee. The fixed baseline is a fixed *target*, not a fixed order quantity. No policy is an optimizer, and no hyperparameter is tuned against the evaluation period.

## Reproduce and stress-test

```sh
# Exact committed base configuration
python -m inventory_lab --output output/base

# Exact committed constraint stress
python -m inventory_lab --lead-days 9 --daily-budget 10000 --output output/stress

# Different business assumptions
python -m inventory_lab --seeds 101,102,103,104,105 --days 365 \
  --review-days 3 --daily-budget 8000 --shortage-penalty 3 \
  --service-target 0.98 --demand-scale 1.3 --output output/scenario

# All arguments
python -m inventory_lab --help
```

The CLI exposes horizon, seed, SKU count (1–50; recommended demo 20–50), warmup, demand scaling, lead time, review cadence, procurement allowance, shortage penalty, and service target. Acquisition costs are seeded synthetic catalog attributes. The Python `Config` also exposes daily holding basis points and order fees. Same interpreter, code, and configuration reproduce the committed CSV/report hashes; no timestamp or absolute path enters those artifacts. Python's standard RNG/float implementations are not a promise of bit-identical output on every future Python release. SQLite binary files are not hash-compared.

## Model contract

- **Event order:** receive prior orders at the start of day → observe and fulfill demand → record lost demand → update histories → review and order → charge end-of-day holding.
- **Protection period:** because ordering happens after today’s demand and receipts occur before demand, an order target covers tomorrow through the day before the following review’s receipt: `lead + review − 1` days. This boundary is covered by a deterministic test.
- Lead time is a positive whole number of days. An order on day `d` with lead `L` arrives before demand on day `d+L`.
- Initial stock is `ceil(training mean × (lead + review − 1))`, identical across policies. It is an endowed asset, not charged against the purchasing allowance. The 56-day warmup is training data, not an unreported policy burn-in.
- Ground-truth latent demand is observable, including lost demand. Real sales data generally does **not** satisfy that assumption.
- Unfulfilled demand is lost, not backordered. No substitutions, returns, perishability, sales-price/revenue model, supplier capacities, or minimum order quantities.
- A day's procurement budget includes acquisition spend **and order fees**. No borrowing and no cash carryover. This is a purchasing-cash constraint, not a full business cash-flow model.
- When constrained, allocate by lowest inventory-position coverage against frozen training rate; use SKU ID to break ties. This is transparent and identical across policies, not globally optimal or starvation-proof.
- Ending on-hand stock and outstanding orders remain assets; they receive no terminal salvage credit. Purchases are reported separately and excluded from the modeled operating-cost objective. Compare equal horizons and review the horizon-boundary limitation.
- Demand generator: SKU-specific random base rate, weekly pattern, mild upward trend, rounded/clipped Gaussian count noise, intermittent zeros on every sixth SKU. It is an illustrative generator, not a fitted retail demand distribution.

## Metrics and SQL

The executed SQL lives in [sql/policy_comparison.sql](sql/policy_comparison.sql), not hidden in a notebook.

| Metric | Definition |
|---|---|
| Unit fill rate | Sum fulfilled / sum demand; undefined (`NULL`) when demand is zero |
| Stockout SKU-days | Number of SKU/day rows with positive lost demand |
| Mean units per SKU | Mean end-of-day on-hand units over SKU-days |
| Order count | Positive SKU replenishments; not warehouse purchase-order batches |
| Modeled operating cost | End-of-day holding + order fees + assumed lost-demand penalty |
| Acquisition spend | Ordered units × unit cost; disclosed separately |
| Constrained SKU reviews | Requested quantity exceeds budget-allowed ordered quantity |

Money calculations use integer cents for procurement/cash. Fractional-cent holding accrual is retained as float and rounded only for presentation. Default holding charge is 5 basis points of acquisition value per day, approximately 18.25% per 365 days before compounding.

### Tables and grain

- `dim_sku`: one seed/SKU; acquisition cost and known lead time
- `demand`: one seed/SKU/absolute simulation day, including training
- `policy_day`: one seed/policy/evaluation day/SKU; opening, arrivals, demand, fulfilled, lost, closing, requests, orders, costs, pipeline and remaining daily cash
- Policy comparison: one seed/policy, derived with SQL

`demand.day = policy_day.day + warmup` for evaluation observations. Integer day indices avoid pretending these generated observations have actual calendar dates. The report's weekday pattern is relative to day zero.

The daily cash-remaining column repeats the warehouse's end-of-day balance on every SKU row; **do not sum it across SKUs**. `requested` and `target` are zero on non-review days. `pipeline_units` is measured after today's order.

## Architecture and artifacts

```text
Seed + Config → synthetic catalog/demand → validated input contract
                                ↓
             3 independent policy states, shared demand
                                ↓
                 SQLite fact ledger + SQL metrics
                                ↓
       CSV evidence + hash manifest + offline report + memo
```

- `inventory_lab/core.py`: generator, validation, policies and simulator
- `inventory_lab/__main__.py`: CLI, SQLite persistence, exports, audit and memo
- `inventory_lab/report.py`: standalone HTML/JS view of precomputed results
- `tests/test_inventory.py`: invariants, edge cases, no-future-leakage and artifact tests
- `examples/{base,stress}/`: generated evidence, HTML and decision memo

SQLite replaces the earlier exploratory DuckDB/dbt idea intentionally: the implementation uses no third-party dependencies, and standard SQL is sufficient at this scale. Add larger tools only when their benefits justify them.

Every run exports `experiment.sqlite`, `catalog.csv`, `demand.csv`, `daily_ledger.csv`, `policy_comparison.csv`, `manifest.json`, `decision_memo.md`, and `report.html`. SQLite files are excluded from version control but are generated by the one-command run. The manifest hashes the configuration + inputs and each CSV. It also records zero/nonzero accounting, budget and foreign-key error counts; errors stop report generation.

## Validation and limitations

Run `python -m unittest discover -s tests -v`. Optional report-control smoke test, if Node is available: `node tests/report_smoke.js`. No Node package installation is needed; this tests JavaScript control behavior with a DOM stub, not browser visual layout.

The Python suite checks inventory/pipeline conservation, affordability with fees, exact receipt timing, identical initial states and demand paths, deterministic regeneration, SQL metrics, zero demand, zero budget, malformed/orphan/duplicate data, and unchanged earlier decisions after future demand is perturbed.

The five-seed walkthrough is supplemented by separate selection/evaluation seeds, paired conditional bootstrap intervals, and 12 predefined sensitivity regimes. These quantify synthetic Monte Carlo variation, not real-world uncertainty. The historical-sales adapter is implemented and executed against the official UCI workbook, but sales censoring and missing inventory/supplier data remain fundamental limitations. Full procurement financing, uncertain lead times, and minimum-order constraints are future work.

The report is an interactive **viewer**, not an in-browser simulator. Change operational assumptions through the CLI, then open the new report. No ordering, messaging, login, tracking, or network requests occur.

## Responsible portfolio description

A defensible resume bullet:

> Built a dependency-free Python/SQLite inventory decision lab comparing three policies across 24 synthetic SKUs, independent selection/evaluation seeds, 12 operating regimes, and an explicitly hypothetical public-sales replay; implemented accounting and no-future-leakage tests plus an auditable offline decision report.

If quoting a metric, say **“simulated under documented assumptions”** and name the baseline/scenario. Do not say “saved a retailer money.”

## Related work and attribution

This implementation, generator, report, and tests are original; no third-party source or dataset was copied or vendored.

- [Stockpyl](https://github.com/LarrySnyder/stockpyl): established inventory models and simulation; useful next-stage validation reference.
- [StatsForecast](https://github.com/Nixtla/statsforecast): forecasting baselines and temporal-evaluation patterns; not a dependency.
- [frePPLe](https://github.com/frePPLe/frepple): broader supply-chain planning context; this project deliberately targets a much smaller problem.
- [UCI Online Retail](https://archive.ics.uci.edu/dataset/352/online+retail): a CC BY 4.0 recorded-sales source. It does not provide latent demand, stock availability, purchase costs, or supplier lead times. Only aggregate derived evidence is committed; the raw workbook is excluded.

## License

Original code and documentation: [MIT](LICENSE). Self-authored generated toy data: [CC0 1.0](DATA_LICENSE.md). No private data is included. UCI-derived aggregate outputs retain CC BY 4.0 attribution; raw source files and customer identifiers are excluded.
