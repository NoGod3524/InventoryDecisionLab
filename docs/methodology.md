# Methodology and validity boundaries

## Timeline and accounting

Every evaluation day: receive previously ordered units; observe demand and fulfill from available stock; record lost units; update observations; optionally review and order; charge closing-stock holding cost.

A post-demand order on day d arrives before demand on d+L. The following review order arrives on d+R+L, so current inventory position must cover demand from d+1 through d+R+L−1: **L+R−1 days**. Initial stock uses the training mean times that period. An earlier development version used L+R and was corrected during independent audit; all committed outputs were regenerated. This was an accounting correction, not outcome-based tuning.

Inventory position includes all outstanding orders. No unit is sold before arriving. Purchases and order fees cannot exceed the day's cash allocation. Allocation priority uses inventory-position coverage against a frozen training demand rate and a deterministic SKU tie-break, identically for all policies.

## Selection, evaluation and sensitivity

The predeclared synthetic plan uses seeds 100–119 to select among fixed-target, rolling-mean and seasonal-buffer rules. Selection requires at least 95% unit fill in at least 90% of those seeds and then chooses minimum mean modeled cost. If nothing qualifies, selection abstains. The chosen policy or abstention is saved before evaluation.

Seeds 1000–1029 are held out for evaluation. Twelve scenarios were defined before their results were inspected: base, lower/higher budget, shorter/longer lead time, lower/higher demand, lower/higher penalty, frequent/slow review, and joint stress. The same seeds are paired for policy comparisons within each scenario. Individual sensitivity findings are diagnostic, not retroactive replacement selections. Further tuning would require a new development/validation protocol and fresh unseen evaluation evidence.

For a candidate-minus-fixed mean cost or fill difference, resample seed indices with replacement and preserve the candidate/baseline pair. Report percentile 2.5%/97.5% limits across 2,000 deterministic resamples. Also retain raw per-seed metrics. This interval is conditional Monte Carlo uncertainty, not a real-world causal interval, robustness to distribution misspecification, or a multiplicity-adjusted significance test.

Zero-demand fill is undefined, not 0% or 100%. Mean fill and paired fill comparisons exclude undefined observations and disclose their valid/undefined counts. Undefined seeds never pass a service requirement. Monetary metrics remain defined. Unit tests cover both all-undefined and mixed samples.

## What the objective means

Modeled operating cost is holding accrual + order fees + an assumed per-unit lost-demand penalty. Acquisition spend is separately disclosed. Initial stock is an endowed asset; final stock and paid pipeline remain assets with no salvage credit. This is not accounting profit, revenue, economic welfare or real savings.

A daily procurement allowance resets without carryover, and fees consume it. It is not a cash-flow balance sheet. Review-cadence changes also change how often that allowance can be accessed. That interaction must be considered when interpreting review-frequency sensitivity.

## Real-data contract

The UCI replay ranks products and estimates its hypothetical acquisition-cost proxy exclusively from the training window. It preserves source hash and row provenance, explicitly manages exact duplicate rows, separates cancellations/returns from positive sales, and zero-fills the selected products' calendar-day grid. Customer identifiers never leave the reader.

Recorded sales are censored by unknown historical stock availability and customer behavior. There is no observed opening stock, order pipeline, supplier cost or lead time. Those are assumptions. The replay measures hypothetical fulfillment of recorded gross positive units; it does not reconstruct latent historical demand or actual lost sales. A single historical path yields one deterministic replay per policy; no pseudo-replicated confidence interval is constructed.

## Reproducibility and tests

Configuration, input hashes, CSV hashes, exact SQL, per-seed results and a frozen selection are committed. SQLite binary files, raw UCI data and locally regenerated outputs are excluded. The default workflow uses only Python's standard library. Node is optional locally and used by CI for executable report-control smoke tests.

The test suite checks stock and pipeline balance, cash including fees, exact lead timing, protection-period boundaries, equal demand and initial stock, future-demand perturbation invariance, data contracts, source-format fixtures, train-only product selection, undefined metrics, paired bootstrap direction, output preservation and deterministic artifacts. DOM-stub tests verify report controls and missing-data semantics; they are not visual-browser acceptance tests.
