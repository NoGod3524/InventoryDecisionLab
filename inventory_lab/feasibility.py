"""Exact-integer optimistic unit-service upper bound for already-observed paths.

This is an oracle diagnostic, not an implementable forecast or inventory policy.
It grants early cash, zero fees, zero early lead times and free final-arrival
suffix demand. If even this favorable relaxation misses the target, the original
policy problem is infeasible for that path. No optimization package is needed.
"""
import argparse
import csv
from dataclasses import asdict, replace
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path
import statistics

from .core import Config, generate, validate_data, fingerprint

ROOT=Path(__file__).resolve().parent.parent


def sha256(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def greedy_max_units(items, budget):
    """Exact bounded integer unit-count knapsack when every unit has value one."""
    count=0
    for cost,quantity in sorted(items):
        bought=min(quantity,budget//cost)
        count+=bought;budget-=bought*cost
    return count


def cheapest_cost(items, units):
    total=0
    for cost,quantity in sorted(items):
        bought=min(quantity,units)
        total+=bought*cost;units-=bought
    if units:raise ValueError('Requested units exceed available demand')
    return total


def late_review_bound(config,catalog,demands):
    """A certificate whose feasible set contains every original policy outcome.

    Preserve the simulator's initial endowment. Permit all but the final review's
    cash at time zero with no fees/lead constraints. Replace final-review buying
    by free satisfaction of every SKU's demand from its final receipt day onward.
    Per-SKU free credits are capped at that SKU's total evaluation demand.
    """
    validate_data(config,catalog,demands)
    review_days=list(range(0,config.days,config.review_days))
    final_review=review_days[-1];early_reviews=len(review_days)-1
    total_demand=free_units=0;items=[];certificate=[]
    for row in catalog:
        sku=row['sku'];history=demands[sku][:config.warmup];evaluation=demands[sku][config.warmup:]
        demand=sum(evaluation)
        initial=math.ceil(statistics.mean(history)*(row['lead_days']+config.review_days-1))
        arrival=final_review+row['lead_days']
        late_gift=sum(evaluation[min(arrival,config.days):])
        credited=min(demand,initial+late_gift)
        remaining=demand-credited
        items.append((row['unit_cost_cents'],remaining))
        total_demand+=demand;free_units+=credited
        certificate.append(dict(seed=config.seed,sku=sku,unit_cost_cents=row['unit_cost_cents'],
            lead_days=row['lead_days'],total_demand=demand,initial_units=initial,
            final_order_arrival_day=arrival,free_late_demand_units=late_gift,
            total_free_credited_units=credited,residual_demand_units=remaining))
    target=Fraction(str(config.service_target))
    required=(target.numerator*total_demand+target.denominator-1)//target.denominator
    budget=early_reviews*config.daily_budget_cents
    maximum=free_units+greedy_max_units(items,budget)
    minimum=cheapest_cost(items,max(0,required-free_units))
    necessary=((minimum+early_reviews-1)//early_reviews if early_reviews else
               0 if minimum==0 else None)
    result=dict(seed=config.seed,total_demand=total_demand,service_target=config.service_target,
        early_review_count=early_reviews,final_review_day=final_review,
        early_procurement_allowance_cents=budget,free_credited_units=free_units,
        optimistic_maximum_fulfilled_units=maximum,
        optimistic_fill_ceiling=maximum/total_demand if total_demand else None,
        required_fulfilled_units=required,
        minimum_early_purchase_cents_for_target=minimum,
        necessary_uniform_allowance_cents=necessary,
        certified_infeasible=maximum<required,
        undefined_service=total_demand==0)
    return result,certificate


def write_csv(path,rows):
    with Path(path).open('w',newline='',encoding='utf-8') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def run(plan_path,output):
    """Diagnose the plan's development sample only; never select replacement seeds."""
    plan=json.loads(Path(plan_path).read_text());config=Config(**plan['config']);config.validate()
    seeds=plan['development_seeds']
    if not seeds or len(seeds)!=len(set(seeds)):raise ValueError('Need distinct declared development seeds')
    output=Path(output)
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ValueError('Use a new empty output directory')
    output.mkdir(parents=True,exist_ok=True)
    rows=[];certificates=[];inputs=[]
    for seed in seeds:
        c=replace(config,seed=seed);catalog,demands=generate(c)
        row,cert=late_review_bound(c,catalog,demands)
        rows.append(row);certificates.extend(cert)
        inputs.append(dict(seed=seed,input_sha256=fingerprint(c,catalog,demands)))
    write_csv(output/'capacity_bounds.csv',rows)
    write_csv(output/'sku_certificate.csv',certificates)
    failed=[r for r in rows if r['certified_infeasible']]
    required=plan['calibration']['required_passing_count']
    maximum_passing=len(rows)-len(failed)
    manifest=dict(schema_version='inventory-capacity-certificate/1.0',
        interpretation='Post-hoc oracle diagnosis of already-observed development paths; not fresh validation or a deployable policy.',
        plan_sha256=sha256(plan_path),source_sha256={name:sha256(ROOT/name) for name in ('inventory_lab/core.py','inventory_lab/feasibility.py')},
        input_sha256_by_seed=inputs,config=asdict(config),development_seeds=seeds,
        certified_infeasible_seeds=[r['seed'] for r in failed],
        upper_bound_on_passing_seed_count=maximum_passing,required_passing_seed_count=required,
        declared_gate_certified_impossible=maximum_passing<required,
        csv_sha256={name:sha256(output/name) for name in ('capacity_bounds.csv','sku_certificate.csv')},
        limitations='All bounds are optimistic. Removing a certificate by increasing cash is necessary, not sufficient for a feasible real policy. Initial state, generator and original v2 results are unchanged.')
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2,sort_keys=True)+'\n')
    lines=['# Original-constraint feasibility certificate','','This is a post-hoc diagnosis, not fresh evidence.','',
        f'At least {len(failed)} of {len(rows)} declared development paths are impossible even in an optimistic oracle relaxation. Thus the original sample can pass at most {maximum_passing}/{len(rows)}, below the requested {required}/{len(rows)}.' if maximum_passing<required else 'The capacity bound does not rule out the declared sample gate; it does not establish feasibility.','',
        '| Seed | Demand | Maximum optimistic fulfilled units | Fill upper bound | Required units | Necessary uniform allowance |',
        '|---|---:|---:|---:|---:|---:|']
    for r in failed:
        lower='undefined' if r['necessary_uniform_allowance_cents'] is None else f"${r['necessary_uniform_allowance_cents']/100:,.2f}"
        lines.append(f"| {r['seed']} | {r['total_demand']} | {r['optimistic_maximum_fulfilled_units']} | {r['optimistic_fill_ceiling']:.4%} | {r['required_fulfilled_units']} | {lower} |")
    lines += ['','The allowance column is a necessary lower bound only, not a sufficient budget or recommendation. See ../../docs/feasibility_v2.md for the proof and reproduction instructions. No old artifact or operating constraint was changed.']
    (output/'RESULTS.md').write_text('\n'.join(lines)+'\n')
    return manifest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',default='ablation_plan_v2.json')
    parser.add_argument('--output',default='output/feasibility-v2')
    args=parser.parse_args()
    try:
        result=run(args.plan,args.output)
        print(f"Certified maximum passing count: {result['upper_bound_on_passing_seed_count']}/{len(result['development_seeds'])}")
    except (ValueError,KeyError,OSError) as exc:parser.error(str(exc))

if __name__=='__main__':main()
