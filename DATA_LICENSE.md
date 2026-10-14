# Generated data license

Self-authored synthetic data produced by this project's generator, specifically the CSV files under examples/base, examples/stress, examples/robustness, examples/ablation-v2-development, examples/ablation-v2, examples/feasibility-v2, examples/minimum-budget-v3-development, and examples/minimum-budget-v3, is dedicated to the public domain under [CC0 1.0 Universal](https://creativecommons.org/publicdomain/zero/1.0/). The [CC0 legal code](https://creativecommons.org/publicdomain/zero/1.0/legalcode) applies to those generated data files.

Those synthetic files contain no real records. Code and documentation use MIT. The raw upstream workbook is not distributed; the separately attributed public-data derivatives below have their own license.

## Public recorded-sales derivatives

`examples/uci-replay/`, `examples/uci-matched/`, and `examples/uci-quality-comparison.csv` contain aggregates derived from **Chen, D. (2015), Online Retail, UCI Machine Learning Repository, DOI 10.24432/C5BW33**, licensed [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Source: https://archive.ics.uci.edu/dataset/352/online+retail.

Changes include country/date filtering, training-only SKU selection, cancellation separation, daily aggregation and hypothetical policy replay. The source data's inventory availability, latent demand, purchasing costs and lead times are unknown; simulated operating fields are our assumptions. The raw workbook and customer identifiers are not distributed. These derivatives retain CC BY 4.0 attribution and are **not covered by the synthetic CC0 dedication**.

The hand-authored CSV test fixture under `tests/fixtures/` is original test code/data under MIT and is explicitly not an extract from UCI.
