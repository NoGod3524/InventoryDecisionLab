# Why the original 30-path gate cannot exceed 26/30 under unchanged constraints

This is a post-hoc diagnosis of already-observed v2 data. No fresh seeds were generated; no frozen v2 code, configuration or results were changed.

## Result

At least four of the original development paths cannot reach 95% unit fill under the original purchasing allowance, review calendar, deterministic lead times, initial endowment and 180-day horizon. Therefore **27/30 is infeasible for this particular sample under unchanged operating constraints**, even with perfect future-demand information and an optimal allocator. This does not claim that every future sample must fail.

| Seed | V2 rolling diagnostic fill | Exact optimistic upper bound | Minimum units needed for 95% | Maximum units even in the favorable relaxation |
|---|---:|---:|---:|---:|
| 20001 | 89.390% | 94.8059% | 33,362 | 33,293 |
| 20007 | 86.908% | 93.6465% | 29,143 | 28,727 |
| 20016 | 87.376% | 94.0778% | 31,826 | 31,517 |
| 20023 | 86.624% | 92.8242% | 31,059 | 30,347 |

## Exact-integer upper-bound argument

1. Reviews occur on days 0, 7, ..., 175. The first 25 purchasing allowances total $450,000. We allow all of that money to be spent at the beginning, ignore all transportation delays, and waive every order fee. These changes can only improve service.
2. The last review is day 175. With the original SKU lead times 4–6, only lead-4 SKUs can receive the last order before the evaluation ends, on day 179. Lead-5 and lead-6 orders arrive outside the horizon.
3. Instead of limiting the final review to its actual $18,000 allowance, give each SKU **all demand that can be served after its final-review receipt for free**. This is at least as favorable as any feasible final order. For this configuration, it is all last-day demand of lead-4 SKUs and zero for other SKUs.
4. Also credit the original endowed stock for free. Cap free units at each SKU's total demand so free initial and last-day gifts cannot create fictitious demand.
5. For the remaining demand, use the first $450,000 to buy the cheapest units first, with known SKU acquisition costs and no timing restrictions. Under a total-unit-fill objective, this exactly maximizes the count of purchased units in this relaxed integer problem.
6. Every feasible real policy maps into this more favorable problem. Thus its maximum fulfilled-unit count is an upper bound on any real policy's service. For all four paths the bound is below `ceil(95 × demand / 100)`.

Implementation: [`inventory_lab/feasibility.py`](../inventory_lab/feasibility.py). Full bounds and SKU-level integer certificates: [`examples/feasibility-v2/`](../examples/feasibility-v2/). The count threshold is calculated with integer arithmetic. This proof does not rely on a forecast, z setting, optimization package, or numerical LP tolerances.

## Independent time-indexed oracle cross-check

A separate SciPy/HiGHS linear program preserved each actual review-day cash cap, SKU lead time, daily demand bound and original initial stock, but granted perfect future knowledge, removed all fixed order fees, and allowed fractional units. Its maxima were 94.8061%, 93.6491%, 94.0780% and 92.8260% for the four paths. Primal/dual objective gaps were at most 7.3e-12 units; worst constraint residuals were about 3.6e-12. It independently agrees that all four are infeasible. Fractional service makes its bounds slightly higher than the integer count relaxation.

The optional LP result is retained in [`optional_lp_crosscheck.json`](../examples/feasibility-v2/optional_lp_crosscheck.json). The exact integer certificate above is independently sufficient and requires no LP solver. SciPy is used only for this optional diagnostic; the project's simulation and reproduction remain standard-library-only.

## What can and cannot improve

There is a substantial gap between actual v2 service and these oracle bounds. Forecast-aware marginal expected fulfilled units per purchasing dollar, with explicit fixed-fee activation and terminal-horizon effects, is a substantive allocator improvement worth exploring. The original allocator prioritizes frozen-rate inventory coverage and does not optimize the aggregate unit-fill objective per dollar. Simply raising z locks more capital into inventory and cannot defeat the capacity bound.

However, no allocator or forecast can cross 27/30 on these exact paths under all unchanged constraints. An operational change is necessary: a higher review-day cash allowance, more accessible review opportunities, shorter lead times, or a different initial endowment. Such a change must be stated openly and prospectively evaluated; it cannot be disguised as an algorithmic win under the old budget.

## Necessary budget lower bounds, not sufficiency claims

Keeping the calendar and initial endowment fixed, the same favorable relaxation gives the following necessary per-review-day allowances. These lower bounds still waive fees and grant the last demand for free; a real implementable policy can require more.

| Seed | Minimum first-25-review procurement for 95% | Necessary uniform review-day allowance |
|---|---:|---:|
| 20001 | $451,561.74 | $18,062.47 |
| 20007 | $460,328.74 | $18,413.15 |
| 20016 | $457,630.46 | $18,305.22 |
| 20023 | $466,952.23 | $18,678.09 |

To reach 27/30 on this sample, at least one of these four paths must be rescued. Therefore a uniform allowance below $18,062.47 is still impossible in this favorable bound; **$18,062.47 is not a guarantee or a recommended operational budget**.

A future v3 should treat all observed v1/v2 paths as development history, freeze any changed operating constraints, algorithm candidates, tuning rule and fresh seed split before new evaluation, preserve all failures, and separately report per-SKU service so aggregate fill cannot hide systematic sacrifice of expensive products.


## Reproduce the sufficient standard-library proof

From the repository root:

```sh
python -m inventory_lab.feasibility --plan ablation_plan_v2.json --output output/feasibility-v2
python -m unittest discover -s tests -p 'test_feasibility.py' -v
```

The command reads only the already-observed original development seeds. It never chooses replacement seeds, changes operating assumptions, or overwrites an existing result directory. Its manifest records source hashes, input fingerprints and CSV hashes. `capacity_bounds.csv` contains all 30 paths, including those not ruled out; `sku_certificate.csv` contains each product's costs, initial endowment, free late-demand credit and residual demand. The tests compare the greedy integer allocation with exhaustive enumeration, verify receipt-boundary gifts, and check that actual policies never exceed the bound on old public seed fixtures.

This diagnosis does not itself authorize a new budget or constitute a successful operating policy. Any relaxed-budget study is a separate, clearly labeled prospective experiment; original v2 evidence remains unchanged.
