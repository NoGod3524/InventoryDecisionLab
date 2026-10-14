"""Predeclared paired experiments: selection seeds, untouched evaluation seeds, OAT stress."""
import argparse
import csv
from dataclasses import asdict, replace
import hashlib
import json
import math
from pathlib import Path
import random
import sqlite3
import statistics

from .core import Config, POLICIES, generate, simulate, fingerprint
from .report import render_experiments

ROOT = Path(__file__).resolve().parent.parent
EXPERIMENT_VERSION = '1.0'


def interval(values, seed=913, draws=2000):
    """Percentile bootstrap of a mean. Conditional Monte Carlo interval, not real-world CI."""
    if not values:
        return None, None
    rng=random.Random(seed)
    n=len(values)
    means=sorted(sum(values[rng.randrange(n)] for _ in range(n))/n for _ in range(draws))
    return means[int(.025*(draws-1))],means[int(.975*(draws-1))]


def paired_interval(rows, candidate, baseline, metric, draws=2000):
    lookup={(r['seed'],r['policy']):r for r in rows}
    seeds=sorted({r['seed'] for r in rows})
    diffs=[lookup[s,candidate][metric]-lookup[s,baseline][metric] for s in seeds
           if lookup[s,candidate][metric] is not None and lookup[s,baseline][metric] is not None]
    lo,hi=interval(diffs,draws=draws)
    return dict(candidate=candidate,baseline=baseline,metric=metric,n_pairs=len(diffs),
                n_undefined_pairs=len(seeds)-len(diffs),
                mean_difference=statistics.mean(diffs) if diffs else None,bootstrap_lower=lo,bootstrap_upper=hi,
                minimum_difference=min(diffs) if diffs else None,maximum_difference=max(diffs) if diffs else None)


def summarize(records):
    """Use the exact same versioned SQL mart as the default experiment."""
    keys=list(records[0])
    with sqlite3.connect(':memory:') as db:
        columns=', '.join(k+' '+('TEXT' if k in ('policy','sku') else 'REAL' if k=='holding_cents' else 'INTEGER') for k in keys)
        db.execute('CREATE TABLE policy_day('+columns+')')
        db.executemany('INSERT INTO policy_day VALUES('+','.join('?' for _ in keys)+')',
                       [tuple(r[k] for k in keys) for r in records])
        db.row_factory=sqlite3.Row
        return [dict(r) for r in db.execute((ROOT/'sql/policy_comparison.sql').read_text())]


def scenario_definitions(base):
    """Declared before evaluation; single-factor changes isolate assumption sensitivity."""
    return [
        ('base',base),
        ('budget_low',replace(base,daily_budget_cents=1200000)),
        ('budget_high',replace(base,daily_budget_cents=2400000)),
        ('lead_long',replace(base,lead_days=9)),
        ('lead_short',replace(base,lead_days=1)),
        ('demand_low',replace(base,demand_scale=.8)),
        ('demand_high',replace(base,demand_scale=1.2)),
        ('penalty_low',replace(base,shortage_cents=300)),
        ('penalty_high',replace(base,shortage_cents=1800)),
        ('review_frequent',replace(base,review_days=3)),
        ('review_slow',replace(base,review_days=14)),
        ('joint_stress',replace(base,lead_days=9,daily_budget_cents=1000000,demand_scale=1.2)),
    ]


def choose_policy(rows,target=.95,required_share=.9):
    eligible=[]
    for p in POLICIES:
        r=[x for x in rows if x['policy']==p]
        share=sum(x['fill_rate'] is not None and x['fill_rate']>=target for x in r)/len(r)
        if share>=required_share:
            eligible.append((statistics.mean(x['modeled_cost_dollars'] for x in r),p))
    return min(eligible)[1] if eligible else None


def evaluate(config, seeds):
    rows=[]
    hashes=[]
    for seed in seeds:
        c=replace(config,seed=seed)
        catalog,demands=generate(c)
        records=[]
        for policy in POLICIES:
            records.extend(simulate(c,catalog,demands,policy))
        rows.extend(summarize(records))
        hashes.append(dict(seed=seed,input_sha256=fingerprint(c,catalog,demands)))
    return rows,hashes


def write_csv(path,rows):
    with path.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)


def run_experiments(output,selection_count=20,evaluation_count=30,days=180,skus=24,draws=2000):
    if selection_count<2 or evaluation_count<2 or draws<100:
        raise ValueError('At least 2 seeds per split and 100 bootstrap draws are required')
    output=Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError('Use a new empty output directory')
    output.mkdir(parents=True,exist_ok=True)
    base=Config(days=days,skus=skus)
    selection_seeds=list(range(100,100+selection_count))
    evaluation_seeds=list(range(1000,1000+evaluation_count))
    if set(selection_seeds)&set(evaluation_seeds):
        raise ValueError('Selection and evaluation seeds overlap')
    # Persist the declared plan before running any evaluation.
    plan=dict(version=EXPERIMENT_VERSION,selection_seeds=selection_seeds,evaluation_seeds=evaluation_seeds,
              scenarios=[dict(name=n,config=asdict(c)) for n,c in scenario_definitions(base)],
              selection_rule='Lowest mean modeled cost meeting 95% fill in at least 90% of selection seeds; freeze before evaluation.',
              bootstrap=dict(draws=draws,seed=913,method='paired percentile bootstrap of mean differences',level=.95),
              interpretation='Conditional uncertainty over synthetic demand seeds only; not uncertainty about real-world assumptions.')
    (output/'experiment_plan.json').write_text(json.dumps(plan,indent=2)+'\n')
    selection,selection_hashes=evaluate(base,selection_seeds)
    selected=choose_policy(selection)
    write_csv(output/'selection_metrics.csv',selection)
    (output/'frozen_selection.json').write_text(json.dumps(dict(selected_policy=selected,rule=plan['selection_rule'],input_hashes=selection_hashes),indent=2)+'\n')
    allrows,pairs,summary,hashes=[],[],[],{}
    for name,config in scenario_definitions(base):
        rows,scenario_hashes=evaluate(config,evaluation_seeds)
        hashes[name]=scenario_hashes
        allrows.extend([dict(scenario=name,**r) for r in rows])
        for policy in POLICIES:
            rr=[r for r in rows if r['policy']==policy]
            costs=[r['modeled_cost_dollars'] for r in rr]
            fills=[r['fill_rate'] for r in rr if r['fill_rate'] is not None]
            lo,hi=interval(costs,draws=draws)
            flo,fhi=interval(fills,draws=draws)
            summary.append(dict(scenario=name,policy=policy,n_seeds=len(rr),mean_cost=statistics.mean(costs),
                                cost_lower=lo,cost_upper=hi,mean_fill=statistics.mean(fills) if fills else None,fill_lower=flo,
                                fill_upper=fhi,min_fill=min(fills) if fills else None,max_fill=max(fills) if fills else None,
                                n_valid_fill=len(fills),n_undefined_fill=len(rr)-len(fills),
                                share_meeting_95=sum(f>=.95 for f in fills)/len(rr),
                                mean_inventory=statistics.mean(r['mean_units_per_sku'] for r in rr),
                                mean_procurement=statistics.mean(r['purchase_dollars'] for r in rr)))
        for candidate in POLICIES[1:]:
            for metric in ('modeled_cost_dollars','fill_rate'):
                pairs.append(dict(scenario=name,**paired_interval(rows,candidate,POLICIES[0],metric,draws)))
        print(f'{name}: {len(evaluation_seeds)} paired seeds finished',flush=True)
    write_csv(output/'evaluation_metrics.csv',allrows)
    write_csv(output/'scenario_summary.csv',summary)
    write_csv(output/'paired_comparisons.csv',pairs)
    manifest=dict(plan_sha256=hashlib.sha256((output/'experiment_plan.json').read_bytes()).hexdigest(),
                  frozen_policy=selected,input_hashes=hashes,artifact_sha256={})
    for p in sorted(output.glob('*.csv')):
        manifest['artifact_sha256'][p.name]=hashlib.sha256(p.read_bytes()).hexdigest()
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    lines=['# Held-out synthetic experiment results','','Policy selection used separate demand seeds before evaluation. This is a reproducible design, not a registered study or a claim of real-world savings.','',f'Frozen base-scenario selection: **{selected or "No feasible policy"}**.','',f'{selection_count} selection seeds; {evaluation_count} held-out seeds per scenario; 12 predefined scenarios; {draws} bootstrap resamples per interval.','','| Scenario | Policy | Mean fill | Seeds meeting 95% | Mean modeled cost | 95% bootstrap interval for mean cost |','|---|---|---:|---:|---:|---:|']
    for r in summary:
        fill_label=f"{r['mean_fill']:.2%}" if r['mean_fill'] is not None else 'undefined'
        lines.append(f"| {r['scenario']} | {r['policy']} | {fill_label} | {r['share_meeting_95']:.0%} | ${r['mean_cost']:,.0f} | ${r['cost_lower']:,.0f}–${r['cost_upper']:,.0f} |")
    lines+=['','## Interpretation','','Intervals quantify only Monte Carlo uncertainty conditional on the generator and operating assumptions. They do not address distribution misspecification, parameter uncertainty, or real-world effects. Many intervals are reported without multiplicity correction; do not use them as a battery of significance tests. The same seeds are paired within every policy comparison.','', 'Selection is frozen once on the base selection sample. Scenario tables are sensitivity analyses; they are not permission to retrospectively reselect a winner using held-out results. Service feasibility is an empirical proportion, not a guarantee. Changing review cadence changes how often the daily cash allowance can be used, so the review-cadence scenarios include that operational interaction.','','Raw per-seed results and paired candidate-minus-fixed differences are in the CSV files. Negative cost differences favor the candidate; positive fill differences favor the candidate.']
    (output/'RESULTS.md').write_text('\n'.join(lines)+'\n')
    (output/'report.html').write_text(render_experiments(summary,selected,plan),encoding='utf-8')
    return summary,manifest


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output',default='output/robustness')
    p.add_argument('--selection-seeds',type=int,default=20)
    p.add_argument('--evaluation-seeds',type=int,default=30)
    p.add_argument('--days',type=int,default=180)
    p.add_argument('--skus',type=int,default=24)
    p.add_argument('--bootstrap-draws',type=int,default=2000)
    a=p.parse_args()
    try:run_experiments(a.output,a.selection_seeds,a.evaluation_seeds,a.days,a.skus,a.bootstrap_draws)
    except ValueError as e:p.error(str(e))

if __name__=='__main__':main()
