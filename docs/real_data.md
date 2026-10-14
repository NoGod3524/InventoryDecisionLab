# Public historical-sales replay

## Source and license

The supported source is [UCI Online Retail](https://archive.ics.uci.edu/dataset/352/online+retail), credited as Chen, D. (2015). *Online Retail* [Dataset]. UCI Machine Learning Repository. [DOI: 10.24432/C5BW33](https://doi.org/10.24432/C5BW33).

The official source page, checked October 14, 2026, lists 541,909 transaction records, an `Online Retail.xlsx` download, and [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). It describes UK online-retailer transactions from December 1, 2010 to December 9, 2011. Prices are sterling; an invoice beginning with C indicates cancellation. Attribute UCI and the dataset creator when redistributing transformed data. The project's MIT/CC0 notices do not replace the source-data license.

Download the ZIP from the official dataset page and extract `Online Retail.xlsx` yourself. The adapter does not initiate network access. No original UCI workbook is committed. The adapter's unit tests use self-authored miniature fixtures; passing those tests is not a full-dataset benchmark. The official full workbook was subsequently downloaded and executed successfully; verified hashes, exact window and source-row count are recorded below. The fixture remains a separate format test, not the source of the real-data results.

## Python API

```python
from inventory_lab.core import Config, simulate
from inventory_lab.retail import load_retail

config = Config(skus=24, warmup=56, days=180, demand_scale=1)
replay = load_retail(
    'data/Online Retail.xlsx', config, '2010-12-01',
    country='United Kingdom', duplicate_policy='keep', cost_ratio='0.5',
    cancellation_policy='gross',
)
records = simulate(replay.config, replay.catalog, replay.demands, 'rolling_mean')
# Preserve replay.metadata and replay.adjustments alongside every result.
```

Use a window wholly inside the observed country's source date range. The start date is explicit, followed by exactly `warmup` training days and `days` evaluation days. The replay returns the supplied Config plus catalog/demands satisfying the simulator's normal validation contract. `demand_scale` must equal 1. The seed remains an artifact identifier: changing it does not resample historical observations or create independent evidence.

## Input contract and exclusions

- UTF-8 CSV (BOM allowed), or the first worksheet of a normal XLSX workbook. XLSX uses standard-library ZIP/XML readers and supports shared/inline strings and numeric Excel 1900-system dates. Formula, error and boolean cells, and 1904-date-system workbooks are rejected. This is a narrow ingestion adapter, not a general spreadsheet engine.
- Required unique columns: `InvoiceNo`, `StockCode`, `Quantity`, `InvoiceDate`, `UnitPrice`, `Country`. Other columns are allowed. CSV rows must match the header width.
- Dates: ISO dates/timestamps, explicitly US month/day/year CSV dates, or XLSX numeric serials. Ambiguous CSV dates are interpreted month/day, never guessed from other records. Time zones are unsupported. Transactions aggregate to their local calendar date.
- IDs and country cannot be blank. Quantities must be finite integral numbers; prices finite Decimal values. Invalid values fail the run with row context. Missing customer IDs/descriptions are permitted because they are not needed.
- C-prefixed invoices or negative quantities enter the separate adjustments ledger. Under the default `cancellation_policy='gross'`, they never subtract from gross positive sales. Under `same_day_exact`, the conservative whole-row matching below removes matched positive records. Neither mode replenishes simulated inventory from returns. A negative quantity without a C prefix is labeled `return_or_negative_quantity`, not asserted to be a confirmed customer return.
- Zero quantities, nonpositive prices, and stock codes that do not match five digits followed by optional letters enter the adjustments ledger. The code rule is a transparent product-code heuristic: it excludes service/administrative codes but does not establish true product identity. Review these exclusions for other datasets.
- The default duplicate policy is `keep`: repeated invoice/SKU rows can be legitimate. Exact matching of every normalized source field is tracked using SHA-256. `drop_exact` discards subsequent exact rows; `error` stops. Neither mode collapses different rows merely because they share an invoice or SKU. Leading/trailing string whitespace is normalized before comparison.

## Leakage prevention and accounting

SKU eligibility/ranking uses retained positive unit totals in training only, after the chosen cancellation policy is applied uniformly across the complete country/window. Ties use lexical StockCode ordering. Evaluation-only products cannot enter the catalog. Too few eligible training products causes a clear error rather than selecting from future records.

Each selected SKU receives a complete calendar-day grid, including zero-sales days. A zero means no eligible recorded transaction; the source cannot tell whether the store was closed, the input was incomplete, or stock was unavailable. Date-range coverage validation only checks observed country boundaries, not completeness of every day.

Prices stay Decimal through training-only quantity-weighted averaging. A hypothetical acquisition cost equals that mean selling price times `cost_ratio` (default 0.5), rounded half-up to the nearest penny with a 1p minimum. Acquisition costs are not observed supplier costs. Every Config field ending `_cents` is interpreted as GBP pence for this replay; no foreign-exchange conversion is performed. Lead time, budget, order fees, holding and shortage charges remain user-supplied operating assumptions.

Provenance includes source-file SHA-256, dates/split, country, duplicate policy, exclusion counts, selected SKUs, and selected-sale row lineage (physical row, invoice, date, SKU, quantity, exact decimal price, duplicate origin). Adjustments have the same non-customer lineage. Source counts span the full file; adjustments and eligible-sales counts are restricted to the selected country/window, before final SKU selection. Customer IDs and descriptions are not exported. Keep detailed lineage in an audit file rather than embedding it in a large HTML report.

## Interpretation boundary

Observed sales are a censored proxy for demand. This adapter does not recover demand lost to real stockouts, customer substitution, availability, or missing records. The simulator treats replay quantities as hypothetical requests, including its own unserved quantities, and may learn from those full replay values. Any resulting fill rate, shortage quantity, or operating cost belongs to that hypothetical operating experiment. It does not estimate the historical retailer's service level, profit, inventory, or savings.

Returns are audited but not modeled as usable supply. Same-day exact cancellation sensitivity can exclude paired positive sales; it does not reconstruct net latent demand. Costs/lead times are assumed. Do not pool a single historical path across multiple seed IDs and describe those copies as independent trials. Use explicit time windows and sensitivity analyses when studying robustness; do not choose a winning window after inspecting evaluation results.

## Checks

```sh
python -m unittest discover -s tests -p test_retail.py -v
```

Tests cover CSV/XLSX ingestion, decimal rounding, full daily grids, simulator compatibility, future-SKU/price leakage, adjustments, duplicate policies, invoice-row lineage, malformed values, training SKU sufficiency and date coverage.

### Committed fixture (not real UCI data)

`tests/fixtures/retail.csv` is an original, self-authored 32-day, two-product test fixture in the UCI column schema. Every description explicitly labels it as a test fixture. Invoice IDs are invented; CustomerID is blank. It contains 64 ordinary sales rows, two cancellation rows (including one positive-quantity cancellation), and one administrative-code adjustment. Do not describe results produced from this file as results on UCI data. It is licensed as the project's self-authored toy data, not as a UCI extract.

```python
replay = load_retail(
    'tests/fixtures/retail.csv', Config(skus=2, warmup=28, days=4),
    '2020-01-01',
)
```

## Verified full-workbook execution

The official ZIP was downloaded and verified on 2026-10-14. Both hashes below were computed from the downloaded files; ZIP integrity checking passed.

- ZIP SHA-256: `f5385cbb54bbebf7196389109c6b0621faab0c304e3702548165e71c84aede8b`
- `Online Retail.xlsx` SHA-256: `43465a06f2ccf7c8b5bd2892bc7defb52f97487934fe93b16ae4c3936424676d`
- Source rows parsed: 541,909
- Window: training 2010-12-01–2011-01-25; evaluation 2011-01-26–2011-07-24
- Scope: United Kingdom; 24 SKUs ranked on training-only positive quantities
- Exact duplicates detected globally: 5,268; default policy keeps them explicitly
- Evaluation gross positive sales of selected SKUs: 197,378 units

Run the adapter and complete replay:

```sh
python -m inventory_lab.replay --input "data/Online Retail.xlsx" --output output/uci
```

The raw workbook stays in ignored `data/`. Published examples contain aggregated quantities and simulated ledger/metrics; original row-level invoices in `lineage.json` and `adjustments.json` remain local, ignored audit outputs. No customer identifiers are exported. The UCI-derived aggregates remain CC BY 4.0; they are not relabeled as CC0 synthetic data.


## Post-hoc cancellation-quality sensitivity

`load_retail(..., cancellation_policy='same_day_exact')` is an optional, audit-driven sensitivity introduced after a large same-day positive/cancellation pair was noticed. It is **not an originally preregistered cleaning rule**, and it must be reported alongside the default gross-sales case rather than silently replacing it. The rule is general: it does not target a particular SKU or choose records based on which policy wins.

Matching is fixed before rerunning the comparison:

1. Apply the declared exact-duplicate policy first. Consider all eligible positive sale rows in the selected country/date window, not merely the eventually selected SKUs.
2. A cancellation must have a C-prefixed invoice and strictly negative quantity. Its full absolute quantity must equal one positive row. No partial subtraction or many-to-one aggregation is allowed.
3. Require identical calendar day, SKU, Decimal unit price, absolute quantity, country, and **nonempty identical CustomerID**. Missing customer IDs never match, even if other fields agree. Customer IDs are used only temporarily and never exported.
4. For repeated matching keys, consume positive rows FIFO by source row; process cancellations in source-row order. Each positive row can be consumed once. The input need not be sorted. This is same-calendar-day batch cleaning, not an assertion about intraday ordering.
5. Remove matched positives before creating training SKU rankings, training-only cost estimates and the full daily sales grid. Keep unmatched cancellations in adjustments. No cancellation on another day can change an earlier day's sales or training data.

The matching criteria cannot prove that a cancellation references a particular original invoice: the dataset does not supply that link. Same-day price/quantity/customer coincidence may still be ambiguous; preserve the gross comparison and audit the matches. This rule also intentionally misses partial cancellations, later-day returns, and rows without a customer ID.

`metadata.cancellation_matching` records `matched_pairs`, `matched_positive_units`, `matched_skus`, `negative_cancellation_rows`, and `unmatched_cancellation_rows` for the full country/window before final SKU selection. In gross mode the match counts are zero. `counts.eligible_sales_rows` is before matching; `counts.retained_sales_rows` is after matching. The adjustments ledger links each matched cancellation to its positive invoice/source row and includes a `same_day_exact_matched_positive` row with the reverse link. No CustomerID values appear in this ledger or sales lineage.

Tests exercise complete matching, exact Decimal price equivalence, refusal of partial/aggregate and cross-day matches, customer/country restrictions, repeated cancellation safeguards, deterministic FIFO, training-SKU reselection and cost recomputation, and invariance of training data to future-day cancellations.

### Actual diagnostic result

The same-day exact diagnostic matched 336 pairs / 82,657 positive units. Full training reselection removed SKU23166 and retained 24 SKUs. Seasonal-buffer recorded-sales fulfillment was 86.06% versus gross 85.98%; both fail 95%. Mean inventory per SKU changed from 3,807 to 920 and hypothetical procurement from £170,761 to £137,857. Catalogs and demand denominators differ, so this is not a causal cost-saving comparison. See [side-by-side CSV](../examples/uci-quality-comparison.csv) and [diagnostic report](../examples/uci-matched/report.html).

```sh
python -m inventory_lab.replay --input "data/Online Retail.xlsx" --cancellation-policy same_day_exact --output output/uci-matched
```
