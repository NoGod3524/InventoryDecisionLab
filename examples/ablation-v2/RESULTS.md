# Strong baselines and component ablation: v2

30 development seeds; 60 separate held-out seeds; seven fixed policy specifications. The common empirical gate is fill ≥95% in ≥90% of seeds. The 2×2 holds the buffer at either 0 or 1.28 while changing only rolling versus weekday forecasts. The two calibrated arms receive the same development grid and selection opportunity. No held-out winner is selected.

## Decision status

- rolling_mean: no development candidate passed the frozen gate; z=3.29 is only an infeasible diagnostic fallback.
- weekday: no development candidate passed the frozen gate; z=3.29 is only an infeasible diagnostic fallback.
- Calibrated Base Stock: 45/60 evaluation seeds passed, below the frozen empirical requirement of 54/60.
- Calibrated Seasonal: 45/60 evaluation seeds passed, below the frozen empirical requirement of 54/60.

## Main results

- weekday_without_buffer: mean fill difference +0.329 percentage points; 99% interval [+0.264, +0.394] excludes zero under the declared approximate conditional procedure.
- weekday_with_buffer: mean fill difference +0.110 percentage points; 99% interval [+0.047, +0.168] excludes zero under the declared approximate conditional procedure.
- buffer_with_rolling: mean fill difference +4.664 percentage points; 99% interval [+4.000, +5.269] excludes zero under the declared approximate conditional procedure.
- buffer_with_weekday: mean fill difference +4.445 percentage points; 99% interval [+3.765, +5.072] excludes zero under the declared approximate conditional procedure.
- calibrated_forecast_comparison: mean fill difference +0.012 percentage points; 99% interval [-0.049, +0.073] contains zero. This does not establish equivalence.

## Frozen calibration

| Family | Frozen z | Development status |
|---|---|---|
| rolling_mean | 3.29 | INFEASIBLE: diagnostic fallback only |
| weekday | 3.29 | INFEASIBLE: diagnostic fallback only |

## Held-out service and cost

| Policy | z | Mean fill | Fill range | Passes | 95% Wilson interval | Mean modeled cost | Mean capital |
|---|---|---|---|---|---|---|---|
| Fixed Periodic | 0.00 | 87.80% | 78.69% – 89.74% | 0/60 | 0.00% – 6.02% | $37,281.05 | $17,976.94 |
| Rolling No Buffer | 0.00 | 91.08% | 78.49% – 92.87% | 0/60 | 0.00% – 6.02% | $28,041.25 | $19,916.05 |
| Rolling Buffer | 1.28 | 95.74% | 79.60% – 98.70% | 41/60 | 55.77% – 78.69% | $15,189.95 | $24,183.75 |
| Seasonal No Buffer | 0.00 | 91.41% | 78.55% – 93.27% | 0/60 | 0.00% – 6.02% | $27,111.70 | $20,117.85 |
| Seasonal Buffer | 1.28 | 95.85% | 79.63% – 98.80% | 41/60 | 55.77% – 78.69% | $14,890.10 | $24,379.41 |
| Calibrated Base Stock | 3.29 | 97.26% | 80.31% – 100.00% | 45/60 | 62.77% – 84.22% | $11,352.67 | $31,024.28 |
| Calibrated Seasonal | 3.29 | 97.27% | 79.93% – 100.00% | 45/60 | 62.77% – 84.22% | $11,339.81 | $31,234.71 |

## Primary paired fill contrasts

| Primary fill contrast (candidate − baseline) | Mean Δ (pp) | 95% interval (pp) | 99% family interval (pp) | Valid / undefined |
|---|---|---|---|---|
| Seasonal No Buffer − Rolling No Buffer | 0.329 | 0.280 to 0.379 | 0.264 to 0.394 | 60 / 0 |
| Seasonal Buffer − Rolling Buffer | 0.110 | 0.063 to 0.154 | 0.047 to 0.168 | 60 / 0 |
| Rolling Buffer − Rolling No Buffer | 4.664 | 4.173 to 5.131 | 4.000 to 5.269 | 60 / 0 |
| Seasonal Buffer − Seasonal No Buffer | 4.445 | 3.941 to 4.918 | 3.765 to 5.072 | 60 / 0 |
| Calibrated Seasonal − Calibrated Base Stock | 0.012 | -0.034 to 0.059 | -0.049 to 0.073 | 60 / 0 |

## Inventory capital and cost components

| Policy | Initial stock | Mean capital | Mean peak capital | Terminal on hand | Terminal pipeline | Procurement | Holding | Order fees | Shortage |
|---|---|---|---|---|---|---|---|---|---|
| Fixed Periodic | $24,420.93 | $17,976.94 | $24,420.93 | $5,025.73 | $10,916.92 | $376,308.84 | $666.33 | $1,541.12 | $35,073.60 |
| Rolling No Buffer | $24,420.93 | $19,916.05 | $28,544.88 | $7,432.92 | $11,624.51 | $393,157.93 | $797.59 | $1,499.17 | $25,744.50 |
| Rolling Buffer | $24,420.93 | $24,183.75 | $33,334.67 | $10,861.58 | $12,035.11 | $416,732.32 | $1,122.96 | $1,435.33 | $12,631.65 |
| Seasonal No Buffer | $24,420.93 | $20,117.85 | $28,781.61 | $7,485.56 | $11,787.70 | $394,720.69 | $809.52 | $1,499.83 | $24,802.35 |
| Seasonal Buffer | $24,420.93 | $24,379.41 | $33,545.55 | $11,012.12 | $12,130.41 | $417,435.85 | $1,137.75 | $1,434.79 | $12,317.55 |
| Calibrated Base Stock | $24,420.93 | $31,024.28 | $40,855.84 | $17,064.46 | $11,983.89 | $429,413.28 | $1,705.76 | $1,339.46 | $8,307.45 |
| Calibrated Seasonal | $24,420.93 | $31,234.71 | $41,064.18 | $17,143.89 | $12,088.26 | $429,678.60 | $1,723.75 | $1,336.96 | $8,279.10 |

## Complete development grid

| Family | z | Dev passes | Mean fill | Mean modeled cost | Mean capital |
|---|---|---|---|---|---|
| rolling_mean | 0.00 | 0/30 | 91.23% | $26,958.10 | $19,158.69 |
| rolling_mean | 0.64 | 22/30 | 94.42% | $18,274.00 | $21,252.13 |
| rolling_mean | 1.28 | 25/30 | 96.27% | $13,300.49 | $23,381.00 |
| rolling_mean | 1.96 | 26/30 | 97.21% | $10,872.16 | $25,718.07 |
| rolling_mean | 2.58 | 26/30 | 97.60% | $9,953.83 | $27,858.66 |
| rolling_mean | 3.29 | 26/30 | 97.88% | $9,338.84 | $30,319.75 |
| weekday | 0.00 | 0/30 | 91.45% | $26,355.95 | $19,307.11 |
| weekday | 0.64 | 22/30 | 94.57% | $17,866.68 | $21,404.03 |
| weekday | 1.28 | 25/30 | 96.35% | $13,109.11 | $23,539.64 |
| weekday | 1.96 | 26/30 | 97.29% | $10,643.27 | $25,873.29 |
| weekday | 2.58 | 26/30 | 97.65% | $9,825.45 | $28,016.51 |
| weekday | 3.29 | 26/30 | 97.90% | $9,300.34 | $30,484.95 |

## Secondary descriptive contrasts

| Contrast | Metric | Mean Δ | 95% interval | Pairs |
|---|---|---|---|---|
| weekday_without_buffer | modeled_cost_dollars | -929.5507 | -1,071.6827 to -785.9267 | 60 |
| weekday_without_buffer | purchase_dollars | 1,562.7608 | 1,344.5400 to 1,799.9960 | 60 |
| weekday_without_buffer | mean_inventory_position_value_dollars | 201.8049 | 176.6390 to 227.4404 | 60 |
| weekday_without_buffer | peak_inventory_position_value_dollars | 236.7343 | 172.4613 to 308.0093 | 60 |
| weekday_with_buffer | modeled_cost_dollars | -299.8513 | -429.4697 to -161.2463 | 60 |
| weekday_with_buffer | purchase_dollars | 703.5317 | 589.0665 to 818.7202 | 60 |
| weekday_with_buffer | mean_inventory_position_value_dollars | 195.6660 | 167.9308 to 224.1387 | 60 |
| weekday_with_buffer | peak_inventory_position_value_dollars | 210.8787 | 130.3918 to 287.0792 | 60 |
| buffer_with_rolling | modeled_cost_dollars | -12,851.3042 | -14,075.8362 to -11,566.5554 | 60 |
| buffer_with_rolling | purchase_dollars | 23,574.3840 | 21,645.0770 to 25,390.4843 | 60 |
| buffer_with_rolling | mean_inventory_position_value_dollars | 4,267.6972 | 4,165.3844 to 4,367.4285 | 60 |
| buffer_with_rolling | peak_inventory_position_value_dollars | 4,789.7968 | 4,625.7695 to 4,952.3802 | 60 |
| buffer_with_weekday | modeled_cost_dollars | -12,221.6048 | -13,469.2838 to -10,902.7366 | 60 |
| buffer_with_weekday | purchase_dollars | 22,715.1548 | 20,760.9600 to 24,547.0740 | 60 |
| buffer_with_weekday | mean_inventory_position_value_dollars | 4,261.5584 | 4,150.7496 to 4,369.4778 | 60 |
| buffer_with_weekday | peak_inventory_position_value_dollars | 4,763.9412 | 4,602.6810 to 4,922.4888 | 60 |
| calibrated_forecast_comparison | modeled_cost_dollars | -12.8583 | -153.4418 to 127.9838 | 60 |
| calibrated_forecast_comparison | purchase_dollars | 265.3157 | 211.2520 to 321.9717 | 60 |
| calibrated_forecast_comparison | mean_inventory_position_value_dollars | 210.4348 | 181.0096 to 239.9117 | 60 |
| calibrated_forecast_comparison | peak_inventory_position_value_dollars | 208.3392 | 152.2603 to 263.0145 | 60 |
| factorial_interaction | fill_rate | -0.0022 | -0.0028 to -0.0016 | 60 |

## Scope and interpretation

The experiment is a prospective extension of an already-explored synthetic model, not an original preregistration. All inference is conditional on this generator, deterministic lead times, full latent-demand visibility, endowed initial stock and the stated cash allocator. Raw-demand dispersion is a shared heuristic, not calibrated forecast-error uncertainty. Same starting assets and cash caps do not mean equal realized capital or equal achieved service; compare the capital and service columns together. Modeled operating cost is holding + fees + assumed shortage penalty, excluding acquisition spend, revenue and terminal salvage. Five 99% marginal percentile-bootstrap intervals form an approximate Bonferroni nominal 95% primary family; coverage is not guaranteed. Secondary contrasts are descriptive, with no multiplicity adjustment. A confidence interval containing zero does not prove equivalence. Wilson intervals describe passing fractions and do not replace the prespecified empirical gate. Undefined fill never passes; paired undefined metrics are excluded only from that contrast and counted. No real-world savings, causal business effect, competition ranking, or deployment approval is established.

## Freeze chronology

Plan commit: 72906cc5cd47fb2eb623660660b624af2a02cbe5
Calibration commit: 82f0e03937a5c9ccdbd50f37cd0648493154b80c
Plan SHA-256: d4d606b086f583264dc7adae630860a1583ace4fafa0aea9001badfb45489c0b
Calibration SHA-256: d99f7bd0de51c9f8d7fea142cd37a5e14828fa045b92dd4ae69dee22cb99bcf1

See manifest.json for calculation-source hashes, input fingerprints, CSV hashes and accounting checks. Exact commands are in docs/ablation_v2.md.
