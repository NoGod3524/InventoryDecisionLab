# Minimum qualifying budget within the frozen grid and policy class

The frozen policy is seasonal_base_stock_z329. Its review-day purchasing allowance increased from $18,000.00 to $19,400.00 (+7.78%). Demand, starting assets, SKU lead times, review dates, forecasting and buffer parameters, allocator and unit-service target are unchanged. This is a changed-budget experiment, not a same-budget algorithmic improvement.

## Confirmation status

Both fresh confirmation cohorts met the declared empirical gate. confirmation_A: 29/30 passed (required 27/30); confirmation_B: 27/30 passed (required 27/30).

## Search scope

The search visited 15 consecutive budgets from $18,000.00 through $19,400.00, in $100.00 increments. A single policy had to meet the gate in every one of three previously observed development cohorts. The first qualifying grid budget was selected; cost, capital and policy ID broke within-budget ties. The minimum claim applies only to the declared grid, two fixed z=3.29 strategies, and development qualification rule. It does not establish the continuous-budget, all-algorithm or real-world minimum.

## Fresh confirmation

| Cohort | Arm | Budget | Passes | 95% Wilson | Mean fill | Fill range | Mean modeled cost | Mean procurement | Mean capital |
|---|---|---|---|---|---|---|---|---|---|
| confirmation_A | original_budget | $18,000.00 | 24/30 | 62.69% – 90.49% | 97.71% | 88.87% – 100.00% | $10,053.21 | $430,036.22 | $31,117.40 |
| confirmation_B | original_budget | $18,000.00 | 22/30 | 55.55% – 85.82% | 96.58% | 82.61% – 99.98% | $13,494.85 | $419,932.32 | $30,483.88 |
| confirmation_A | selected_budget | $19,400.00 | 29/30 | 83.33% – 99.41% | 99.32% | 94.96% – 100.00% | $5,398.60 | $439,733.04 | $32,340.72 |
| confirmation_B | selected_budget | $19,400.00 | 27/30 | 74.38% – 96.54% | 98.48% | 88.35% – 100.00% | $7,870.93 | $430,741.33 | $31,606.72 |

## Paired budget effects

| Metric | Selected minus original budget | 95% descriptive interval | Paired valid / undefined |
|---|---|---|---|
| fill_rate | 1.751 pp | 1.171 pp to 2.365 pp | 60 / 0 |
| modeled_cost_dollars | -5,139.264 USD | -6,982.270 USD to -3,394.603 USD | 60 / 0 |
| purchase_dollars | 10,252.920 USD | 7,140.713 USD to 13,548.992 USD | 60 / 0 |
| mean_inventory_position_value_dollars | 1,173.075 USD | 843.594 USD to 1,516.556 USD | 60 / 0 |

## Development at the frozen budget

| Policy | Development cohort | Passes | Mean fill | Mean modeled cost | Mean capital |
|---|---|---|---|---|---|
| rolling_base_stock_z329 | former_v2_evaluation_A | 30/30 | 99.44% | $4,936.13 | $32,420.75 |
| seasonal_base_stock_z329 | former_v2_evaluation_A | 30/30 | 99.45% | $4,951.21 | $32,641.13 |
| rolling_base_stock_z329 | former_v2_evaluation_B | 28/30 | 98.64% | $7,427.71 | $32,152.10 |
| seasonal_base_stock_z329 | former_v2_evaluation_B | 28/30 | 98.67% | $7,361.31 | $32,377.72 |
| rolling_base_stock_z329 | original_v2_development | 27/30 | 99.10% | $5,849.09 | $31,111.99 |
| seasonal_base_stock_z329 | original_v2_development | 27/30 | 99.13% | $5,775.65 | $31,284.77 |

Full visited-grid results are in DEVELOPMENT.md and development_summary.csv.

## Interpretation

The original $18,000 configuration remains a failed case, and the original development sample has an independently certified ceiling of 26/30 passing paths. The higher allowance is explicitly a new operating assumption. Both new cohorts were run under the frozen choice regardless of the first outcome. Passing 27/30 is an empirical simulation criterion, not a lower-confidence-bound rule or a real-world reliability guarantee. Wilson intervals do not change the frozen decision rule. Paired percentile-bootstrap intervals are descriptive and not multiplicity-adjusted. All previously observed v1/v2 data are development history, and this extension does not erase cumulative testing or earlier failures. Inventory capital and procurement can rise when a cash constraint is relaxed. Modeled cost excludes revenue, acquisition expenditure and terminal salvage; it is not profit or realized savings. No deployment approval, global minimum-budget claim or competition outcome is supported.

## Freeze references

Plan commit: e0428a808e52bcdd9827e0ebea9653b39ef2b428
Budget freeze commit: f16b825ece320108359121af563b59264df45c5b
Plan SHA-256: 71118d5601e14fd32fd457d8a8b41384e9bad48e8db7e1ed6322df69dc3a98b6
Selection SHA-256: 8392acb68d0ff731cd6fb0aae71ad3c41101e9a099430ee06933b713ebce7a97
