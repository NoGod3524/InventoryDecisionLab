# v1.0.0 — Auditable inventory decision experiments

## Included

- Original standard-library Python simulator with three replenishment policies, common demand paths, daily procurement-cash constraints and explicit accounting
- Versioned SQLite metrics, per-day CSV evidence, hashes, manifests and offline reports
- Separate 20-seed selection and 30-seed held-out evaluation across 12 predefined scenarios, with paired bootstrap intervals and a frozen deployment gate
- CSV/XLSX public-sales adapter with training-only selection, Decimal price handling, cancellation separation, duplicate policy, source provenance and no exported customer IDs
- Verified execution of all 541,909 rows in the official UCI workbook; aggregate replay evidence and CC BY 4.0 attribution
- Competition brief, methodology, reviewer routes, reproducibility instructions and an original MIT implementation

## Evidence that matters

The base configuration **does not qualify for deployment** under the predeclared selection rule. Seasonal buffering has 95.92% mean held-out base fill but only 70% of seeds reach 95%. Predefined higher-budget and more-frequent-review scenarios suggest possible pilot directions; they do not replace independent future validation.

The gross recorded-sales replay reaches 85.98%, and the audit-driven matched-cancellation diagnostic reaches 86.06%, under hypothetical inventory and supplier assumptions. The diagnostic matches 336 exact same-day cancellation pairs and fully retrains the selected catalog; both evidence modes remain visible. It does not estimate real lost demand or achieved savings.

## Verification

48 Python unit/integration tests cover conservation, cash including fees, receipt timing and L+R−1 protection boundaries, future-data perturbation, SQL parity, deterministic exports, malformed inputs, CSV/XLSX fixtures, train-only selection, zero-demand metrics and preservation of existing files. Node standard-library smoke checks exercise report controls and undefined-service rendering. The release CI runs both without installing Python packages.

A separate review reproduced committed synthetic CSV hashes and the held-out base scenario, and checked the full public-data source. DOM-stub testing is not browser visual acceptance; any deployment-specific browser verification is a separate release check.

## Boundaries

This is a competition-oriented research/decision product, not an ERP integration or live order system. Synthetic demand, deterministic supplier timing and heuristic buffers remain assumptions. UCI recorded sales do not reveal true demand, inventory or supplier costs. Model penalties are not profit. Statistical intervals cover synthetic seed variation only, and there is no promise of real-world service, financial savings or competition placement.
