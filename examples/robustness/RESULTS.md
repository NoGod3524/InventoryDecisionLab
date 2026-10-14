# Held-out synthetic experiment results

Policy selection used separate demand seeds before evaluation. This is a reproducible design, not a registered study or a claim of real-world savings.

Frozen base-scenario selection: **No feasible policy**.

20 selection seeds; 30 held-out seeds per scenario; 12 predefined scenarios; 2000 bootstrap resamples per interval.

| Scenario | Policy | Mean fill | Seeds meeting 95% | Mean modeled cost | 95% bootstrap interval for mean cost |
|---|---|---:|---:|---:|---:|
| base | fixed_periodic | 87.76% | 0% | $36,751 | $34,952–$38,801 |
| base | rolling_mean | 91.08% | 0% | $27,598 | $25,071–$30,515 |
| base | seasonal_buffer | 95.92% | 70% | $14,446 | $10,388–$18,741 |
| budget_low | fixed_periodic | 72.05% | 0% | $81,691 | $72,074–$91,008 |
| budget_low | rolling_mean | 72.15% | 0% | $81,548 | $70,971–$91,476 |
| budget_low | seasonal_buffer | 73.33% | 7% | $78,371 | $67,193–$88,930 |
| budget_high | fixed_periodic | 88.08% | 0% | $35,795 | $34,626–$36,956 |
| budget_high | rolling_mean | 92.24% | 0% | $24,177 | $23,525–$24,794 |
| budget_high | seasonal_buffer | 98.55% | 100% | $6,791 | $6,553–$7,029 |
| lead_long | fixed_periodic | 89.13% | 0% | $32,946 | $30,954–$35,237 |
| lead_long | rolling_mean | 91.84% | 0% | $25,549 | $22,768–$28,669 |
| lead_long | seasonal_buffer | 95.67% | 70% | $15,182 | $11,345–$19,362 |
| lead_short | fixed_periodic | 89.29% | 0% | $32,398 | $30,508–$34,627 |
| lead_short | rolling_mean | 92.22% | 0% | $24,310 | $21,693–$27,292 |
| lead_short | seasonal_buffer | 96.24% | 73% | $13,445 | $9,455–$17,690 |
| demand_low | fixed_periodic | 87.74% | 0% | $29,775 | $28,802–$30,750 |
| demand_low | rolling_mean | 91.70% | 0% | $20,924 | $20,363–$21,454 |
| demand_low | seasonal_buffer | 98.32% | 100% | $6,280 | $6,021–$6,580 |
| demand_high | fixed_periodic | 83.86% | 0% | $57,475 | $50,000–$65,056 |
| demand_high | rolling_mean | 85.35% | 0% | $52,685 | $43,748–$61,839 |
| demand_high | seasonal_buffer | 87.59% | 27% | $45,594 | $34,969–$56,278 |
| penalty_low | fixed_periodic | 87.76% | 0% | $13,711 | $13,104–$14,396 |
| penalty_low | rolling_mean | 91.08% | 0% | $10,722 | $9,882–$11,691 |
| penalty_low | seasonal_buffer | 95.92% | 70% | $6,516 | $5,173–$7,932 |
| penalty_high | fixed_periodic | 87.76% | 0% | $71,310 | $67,702–$75,443 |
| penalty_high | rolling_mean | 91.08% | 0% | $52,912 | $47,856–$58,759 |
| penalty_high | seasonal_buffer | 95.92% | 70% | $26,341 | $18,195–$34,955 |
| review_frequent | fixed_periodic | 85.41% | 0% | $44,975 | $43,458–$46,512 |
| review_frequent | rolling_mean | 90.02% | 0% | $31,985 | $31,138–$32,842 |
| review_frequent | seasonal_buffer | 98.25% | 100% | $9,059 | $8,843–$9,280 |
| review_slow | fixed_periodic | 57.81% | 0% | $121,552 | $111,224–$131,394 |
| review_slow | rolling_mean | 57.44% | 0% | $122,638 | $112,265–$132,354 |
| review_slow | seasonal_buffer | 58.30% | 0% | $120,345 | $110,078–$129,960 |
| joint_stress | fixed_periodic | 53.07% | 0% | $161,350 | $148,900–$173,178 |
| joint_stress | rolling_mean | 52.82% | 0% | $162,193 | $149,832–$173,794 |
| joint_stress | seasonal_buffer | 53.60% | 0% | $159,654 | $147,436–$171,024 |

## Interpretation

Intervals quantify only Monte Carlo uncertainty conditional on the generator and operating assumptions. They do not address distribution misspecification, parameter uncertainty, or real-world effects. Many intervals are reported without multiplicity correction; do not use them as a battery of significance tests. The same seeds are paired within every policy comparison.

Selection is frozen once on the base selection sample. Scenario tables are sensitivity analyses; they are not permission to retrospectively reselect a winner using held-out results. Service feasibility is an empirical proportion, not a guarantee. Changing review cadence changes how often the daily cash allowance can be used, so the review-cadence scenarios include that operational interaction.

Raw per-seed results and paired candidate-minus-fixed differences are in the CSV files. Negative cost differences favor the candidate; positive fill differences favor the candidate.
