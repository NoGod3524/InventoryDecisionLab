# Simulated decision memo

All results below are synthetic, conditional on manifest.json assumptions.

- fixed_periodic: mean fill 88.11%; mean modeled cost $36,660.95.
- rolling_mean: mean fill 92.33%; mean modeled cost $24,542.01.
- seasonal_buffer: mean fill 97.76%; mean modeled cost $9,193.37.

Decision gate: 95% unit fill in every seed. Illustrative lowest-cost candidate: seasonal_buffer under these assumptions; consult independent held-out evidence before deployment.

Modeled cost = end-of-day holding + order fees + lost-demand penalty. Acquisition spend is separate; ending and in-transit stock has no salvage credit. No real-world savings or profit claim is supported.

Next: validate lost demand and supplier variability; stress the budget and lead-time assumptions; pilot prospectively.
