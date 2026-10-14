"""Run hypothetical inventory policies against recorded sales, without claiming lost demand."""
import argparse
from dataclasses import asdict
from html import escape
import json
from pathlib import Path

from .core import Config,POLICIES,simulate
from .retail import load_retail
from .experiments import summarize,write_csv


def run_replay(path,output,config,start_date,country='United Kingdom',duplicate_policy='keep',cost_ratio='0.5',fixture=False,cancellation_policy='gross'):
    output=Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError('Use a new empty output directory')
    replay=load_retail(path,config,start_date,country,duplicate_policy,cost_ratio,cancellation_policy=cancellation_policy)
    output.mkdir(parents=True,exist_ok=True)
    records=[]
    for policy in POLICIES:records.extend(simulate(config,replay.catalog,replay.demands,policy))
    summaries=summarize(records)
    # SQL's legacy _dollars names denote currency units; export explicit GBP names here.
    summaries=[{k.replace('_dollars','_gbp'):v for k,v in r.items()} for r in summaries]
    metadata=dict(replay.metadata)
    lineage=metadata.pop('lineage')
    metadata.update(config=asdict(config),fixture=fixture,
        interpretation='SELF-AUTHORED TEST FIXTURE, not UCI observations' if fixture else 'Single historical gross-sales path; hypothetical policy replay, not a randomized trial',
        source_license='MIT self-authored test fixture' if fixture else metadata['source_license'])
    write_csv(output/'policy_comparison.csv',summaries)
    write_csv(output/'daily_ledger.csv',records)
    write_csv(output/'catalog.csv',replay.catalog)
    write_csv(output/'recorded_sales.csv',[dict(sku=sku,day=day,gross_units=value) for sku,series in replay.demands.items() for day,value in enumerate(series)])
    # JSON preserves original strings safely; avoid spreadsheet formula interpretation.
    (output/'lineage.json').write_text(json.dumps(lineage,indent=2)+'\n',encoding='utf-8')
    (output/'adjustments.json').write_text(json.dumps(replay.adjustments,indent=2)+'\n',encoding='utf-8')
    (output/'manifest.json').write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf-8')
    rows=''.join('<tr><td>'+escape(r['policy'])+'</td><td>'+('N/A' if r['fill_rate'] is None else f"{r['fill_rate']:.2%}")+'</td><td>'+f"£{r['modeled_cost_gbp']:,.2f}"+'</td><td>'+f"£{r['purchase_gbp']:,.2f}"+'</td></tr>' for r in summaries)
    quality_note=('Post-hoc data-quality diagnostic: same-day exact cancellations are matched one-to-one before aggregation and training. This analysis was added after discovering a canceled training outlier; it is not independent external validation.' if cancellation_policy=='same_day_exact' else 'Gross positive sales retain positive orders even when separate cancellation records exist. A completely canceled large training order can distort product selection and initial inventory; inspect the matched-cancellation diagnostic before interpreting results.')
    label='Self-authored fixture demonstration' if fixture else 'Historical recorded-sales replay'
    overview=f"{config.skus} training-selected SKUs · {config.warmup} training days ({metadata['start_date']}–{metadata['training_end']}) · {config.days} evaluation days ({metadata['evaluation_start']}–{metadata['end_date']}) · £{config.daily_budget_cents/100:,.0f} daily purchasing allowance · {config.lead_days}-day lead · {config.review_days}-day review."
    feasible=any(r['fill_rate'] is not None and r['fill_rate']>=config.service_target for r in summaries)
    verdict=f'No policy reaches the {config.service_target*100:g}% recorded-sales fulfillment gate under these assumptions.' if not feasible else 'At least one policy meets the illustrative recorded-sales gate; this is not deployment approval.'
    report='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Inventory Decision Lab · Sales replay</title><style>body{font:16px/1.6 system-ui;color:#17363f;background:#eef3f0;margin:0}main{max-width:1050px;margin:auto;padding:36px 24px}h1{font-size:40px;line-height:1.15}section{background:white;padding:24px;border-radius:12px;margin:22px 0;border:1px solid #d5e3dc}.notice{background:#fff0c0;border-left:5px solid #b88215;padding:18px}table{width:100%;border-collapse:collapse}td,th{padding:13px 8px;border-bottom:1px solid #d5e3dc;text-align:right}td:first-child,th:first-child{text-align:left}.scroll{overflow:auto}pre{white-space:pre-wrap;font-size:12px;max-height:400px;overflow:auto}a{color:#167b73}</style><main><p>INVENTORY DECISION LAB / EXTERNAL DATA CONTRACT</p><h1>'''+label+'''</h1><p>'''+escape(overview)+'''</p><p><strong>'''+verdict+'''</strong></p><div class="notice">Recorded sales are not unconstrained demand. This replay tests hypothetical fulfillment of recorded positive sales; it cannot estimate true historical lost sales or realized savings. '''+('This page uses invented fixture rows, not actual UCI data.' if fixture else 'Public source: UCI Online Retail (Chen, 2015), CC BY 4.0.')+'''</div><section><h2>Conditional policy comparison</h2><div class="scroll"><table><thead><tr><th>Policy</th><th>Recorded-sales fulfillment</th><th>Modeled cost (GBP)</th><th>Procurement (GBP)</th></tr></thead><tbody>'''+rows+'''</tbody></table></div><p>'''+escape(quality_note)+'''</p><p>One historical path is not multiplied into artificial independent seeds. No statistical interval is presented for this deterministic replay.</p></section><section><h2>What is observed vs assumed?</h2><ul><li>Observed input fields: invoices, product codes, timestamps, gross quantities, selling prices, and country.</li><li>Training-only SKU selection and assumed acquisition cost: quantity-weighted training selling price × '''+escape(str(cost_ratio))+'''. No supplier purchase prices are observed.</li><li>Hypothetical inputs: starting stock, supplier lead time, purchasing allowance, holding charge, order fee, shortage penalty and replenishment policies.</li><li>Cancellations and negative quantities are exported separately, not silently netted into demand.</li><li>Absent product-day records are zero-filled. Closures, missing logs and historical stockouts cannot be distinguished.</li><li>Selection favors high-volume training products; this is not representative of the full catalog.</li></ul></section><section><h2>Provenance and reproducibility</h2><p>Source file SHA-256, exact window, duplicate policy, training-selected SKUs, all parameter assumptions and row counts appear below. Original selected row lineage is exported separately as JSON; customer identifiers are never exported.</p><p><a href="https://archive.ics.uci.edu/dataset/352/online+retail">UCI source and license</a> · <a href="https://doi.org/10.24432/C5BW33">Dataset DOI</a></p><details><summary>Full manifest</summary><pre>'''+escape(json.dumps(metadata,indent=2))+'''</pre></details></section></main></html>'''
    (output/'report.html').write_text(report,encoding='utf-8')
    print(f'{label}: {len(replay.catalog)} training-selected SKUs; report {output / "report.html"}')
    return summaries,metadata


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--input',required=True)
    p.add_argument('--output',default='output/retail-replay')
    p.add_argument('--start-date',default='2010-12-01')
    p.add_argument('--skus',type=int,default=24)
    p.add_argument('--days',type=int,default=180)
    p.add_argument('--warmup',type=int,default=56)
    p.add_argument('--lead-days',type=int,default=4)
    p.add_argument('--review-days',type=int,default=7)
    p.add_argument('--daily-budget-gbp',type=int,default=18000)
    p.add_argument('--shortage-penalty-gbp',type=int,default=9)
    p.add_argument('--cost-ratio',default='0.5')
    p.add_argument('--country',default='United Kingdom')
    p.add_argument('--duplicates',choices=['keep','drop_exact','error'],default='keep')
    p.add_argument('--cancellation-policy',choices=['gross','same_day_exact'],default='gross')
    p.add_argument('--fixture',action='store_true',help='Label input as a self-authored test fixture, not actual UCI observations')
    a=p.parse_args()
    config=Config(skus=a.skus,days=a.days,warmup=a.warmup,lead_days=a.lead_days,review_days=a.review_days,daily_budget_cents=a.daily_budget_gbp*100,shortage_cents=a.shortage_penalty_gbp*100)
    try:run_replay(a.input,a.output,config,a.start_date,a.country,a.duplicates,a.cost_ratio,a.fixture,a.cancellation_policy)
    except (ValueError,OSError) as e:p.error(str(e))

if __name__=='__main__':main()
