# Simulated decision memo

All results below are synthetic, conditional on manifest.json assumptions.

- fixed_periodic: mean fill 61.23%; mean modeled cost $114,083.32.
- rolling_mean: mean fill 60.99%; mean modeled cost $114,810.11.
- seasonal_buffer: mean fill 62.21%; mean modeled cost $111,299.41.

Decision gate: 95% unit fill in every seed. No policy meets the target in every seed. Do not recommend one without revisiting constraints.

Modeled cost = end-of-day holding + order fees + lost-demand penalty. Acquisition spend is separate; ending and in-transit stock has no salvage credit. No real-world savings or profit claim is supported.

Next: validate lost demand and supplier variability; stress the budget and lead-time assumptions; pilot prospectively.
