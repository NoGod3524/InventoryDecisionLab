"""Version 2: separately frozen development calibration and paired held-out ablation.

Use the develop and evaluate subcommands in order. Evaluation requires the
published plan and published calibration commit IDs; publishing is a separate,
explicit workflow. Existing v1 experiments and artifacts are never rewritten.
"""
import argparse
import csv
from dataclasses import asdict, replace
import hashlib
import json
import math
from pathlib import Path
import random
import re
import statistics

from .core import Config, StrategySpec, generate, simulate, fingerprint
from .experiments import summarize

ROOT = Path(__file__).resolve().parent.parent


def file_sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def source_hashes():
    """All modules used in the calculation; freeze these before evaluation."""
    paths = ['inventory_lab/core.py', 'inventory_lab/experiments.py',
             'inventory_lab/ablation.py', 'inventory_lab/ablation_report.py', 'sql/policy_comparison.sql']
    return {name: file_sha256(ROOT/name) for name in paths}


def write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False)+'\n', encoding='utf-8')


def write_csv(path, rows):
    if not rows:
        raise ValueError('Cannot write an empty data table')
    with Path(path).open('w', newline='', encoding='utf-8') as stream:
        writer=csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)


def empty_output(path):
    output=Path(path)
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        raise ValueError('Use a new empty output directory; frozen artifacts are never overwritten')
    output.mkdir(parents=True, exist_ok=True)
    return output


def require_commit(value, name):
    if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{40}', value):
        raise ValueError(name+' must be a full published 40-character Git commit ID')


def capital_metrics(records, catalog):
    """Paid acquisition-value assets, including endowed stock and paid pipeline.

    This measures realized inventory capital, not a second financing constraint.
    Initial endowed inventory is reported separately and identical across arms.
    """
    costs={r['sku']:r['unit_cost_cents'] for r in catalog}
    days={}
    for row in records:
        days.setdefault(row['day'], []).append(row)
    first=days[min(days)]; last=days[max(days)]
    capital=[sum((r['closing']+r['pipeline_units'])*costs[r['sku']] for r in rr)/100
             for rr in days.values()]
    return dict(initial_inventory_value_dollars=sum(r['opening']*costs[r['sku']] for r in first)/100,
                mean_inventory_position_value_dollars=statistics.mean(capital),
                peak_inventory_position_value_dollars=max(capital),
                terminal_inventory_value_dollars=sum(r['closing']*costs[r['sku']] for r in last)/100,
                terminal_pipeline_value_dollars=sum(r['pipeline_units']*costs[r['sku']] for r in last)/100)


def score_strategy(config, catalog, demands, policy, predictor, z, audit_samples=None):
    rows=simulate(config, catalog, demands, policy, StrategySpec(predictor, z))
    validate_ledger(config, catalog, demands, rows)
    if audit_samples is not None:
        audit_samples.extend(dict(r) for r in rows if r['day']<7)
    result=summarize(rows)[0]
    result.update(capital_metrics(rows, catalog))
    result['lost_units']=sum(r['lost'] for r in rows)
    return result


def summarize_candidates(rows, target=.95):
    candidates=[]
    for z in sorted({row['z'] for row in rows}):
        rr=[r for r in rows if r['z']==z]
        valid=[r['fill_rate'] for r in rr if r['fill_rate'] is not None]
        candidates.append(dict(z=z, n_seeds=len(rr), n_valid_fill=len(valid),
            n_undefined_fill=len(rr)-len(valid),
            share_meeting_target=sum(f>=target for f in valid)/len(rr),
            mean_fill=statistics.mean(valid) if valid else None,
            mean_cost=statistics.mean(r['modeled_cost_dollars'] for r in rr),
            mean_capital=statistics.mean(r['mean_inventory_position_value_dollars'] for r in rr)))
    return candidates


def select_calibration(rows, target=.95, required_share=.9):
    """Feasibility first; explicit diagnostic fallback is never deployment approval."""
    candidates=summarize_candidates(rows, target)
    feasible=[r for r in candidates if r['share_meeting_target']>=required_share]
    if feasible:
        selected=min(feasible, key=lambda r:(r['mean_cost'],r['mean_capital'],r['z']))
        chosen=selected['z']; status='feasible_on_development'
    else:
        selected=min(candidates,key=lambda r:(-r['share_meeting_target'],
                     -(r['mean_fill'] if r['mean_fill'] is not None else -1),r['mean_cost'],r['z']))
        chosen=None; status='diagnostic_fallback_not_feasible'
    return dict(chosen_for_deployment=chosen, diagnostic_z=selected['z'],
                evaluation_z=selected['z'], status=status, candidates=candidates)


def bootstrap_paired(values, draws=10000, seed=913):
    """Paired-seed percentile intervals; 99% is Bonferroni marginal for five contrasts."""
    if not values:
        return dict(n_pairs=0, mean_difference=None, lower_95=None, upper_95=None,
                    lower_99=None, upper_99=None)
    rng=random.Random(seed); n=len(values)
    boot=sorted(sum(values[rng.randrange(n)] for _ in range(n))/n for _ in range(draws))
    return dict(n_pairs=n, mean_difference=statistics.mean(values),
                lower_95=boot[int(.025*(draws-1))], upper_95=boot[int(.975*(draws-1))],
                lower_99=boot[int(.005*(draws-1))], upper_99=boot[int(.995*(draws-1))])


def paired_contrast(rows, candidate, baseline, metric, draws=10000, seed=913):
    lookup={(r['seed'],r['policy']):r for r in rows}
    seeds=sorted({r['seed'] for r in rows})
    values=[]
    for s in seeds:
        a=lookup[s,candidate][metric]; b=lookup[s,baseline][metric]
        if a is not None and b is not None:values.append(a-b)
    return dict(candidate=candidate, baseline=baseline, metric=metric,
                n_undefined_pairs=len(seeds)-len(values), **bootstrap_paired(values,draws,seed))


def interaction_contrast(rows, metric, draws=10000, seed=913):
    lookup={(r['seed'],r['policy']):r for r in rows}
    seeds=sorted({r['seed'] for r in rows}); values=[]
    for s in seeds:
        a,b,c,d=[lookup[s,p][metric] for p in
                 ('seasonal_buffer','rolling_buffer','seasonal_no_buffer','rolling_no_buffer')]
        if all(v is not None for v in (a,b,c,d)):values.append((a-b)-(c-d))
    return dict(contrast='interaction_(seasonal_buffer-rolling_buffer)-(seasonal_none-rolling_none)',
                metric=metric, n_undefined_pairs=len(seeds)-len(values),
                **bootstrap_paired(values,draws,seed))


def validate_ledger(config, catalog, demands, rows):
    """Independent accounting identities; fail before any result can be published."""
    costs={r['sku']:r['unit_cost_cents'] for r in catalog}
    leads={r['sku']:r['lead_days'] for r in catalog}
    lookup={(r['day'],r['sku']):r for r in rows}
    initials={sku:math.ceil(statistics.mean(demands[sku][:config.warmup])*(leads[sku]+config.review_days-1)) for sku in costs}
    if len(lookup)!=config.days*config.skus or len(rows)!=len(lookup):
        raise ValueError('Ledger has missing or duplicate SKU-days')
    for day in range(config.days):
        daily=[lookup[day,sku] for sku in costs]
        spend=sum(r['purchase_cents']+r['fee_cents'] for r in daily)
        if spend>config.daily_budget_cents:
            raise ValueError('Budget exceeded')
        for r in daily:
            sku=r['sku']; prev=lookup.get((day-1,sku)); due=lookup.get((day-leads[sku],sku))
            initial=initials[sku]
            checks=[r['demand']==demands[sku][config.warmup+day],
                    r['opening']==(prev['closing'] if prev else initial),
                    r['receipts']==(due['ordered'] if due else 0),
                    r['fulfilled']==min(r['demand'],r['opening']+r['receipts']),
                    r['closing']==r['opening']+r['receipts']-r['fulfilled'],
                    r['lost']==r['demand']-r['fulfilled'],
                    r['purchase_cents']==r['ordered']*costs[sku],
                    r['fee_cents']==(config.order_fee_cents if r['ordered'] else 0),
                    r['holding_cents']==r['closing']*costs[sku]*config.holding_bps/10000,
                    r['shortage_cents']==r['lost']*config.shortage_cents,
                    r['pipeline_units']==(prev['pipeline_units'] if prev else 0)+r['ordered']-r['receipts'],
                    r['daily_cash_remaining_cents']==config.daily_budget_cents-spend,
                    r['ordered']>=0, r['closing']>=0]
            if not all(checks):
                raise ValueError(f'Accounting audit failed: day {day}, SKU {sku}')


def load_plan(path):
    plan=json.loads(Path(path).read_text(encoding='utf-8'))
    if plan.get('schema_version')!='inventory-ablation-plan/2.0':
        raise ValueError('Unsupported ablation plan version')
    Config(**plan['config']).validate()
    dev,ev=plan['development_seeds'],plan['evaluation_seeds']
    for seeds in (dev,ev):
        if len(seeds)<2 or any(type(s) is not int for s in seeds) or len(set(seeds))!=len(seeds):
            raise ValueError('Each seed split needs at least two distinct integer seeds')
    if set(dev)&set(ev):raise ValueError('Development and evaluation seeds overlap')
    ids=[p['id'] for p in plan['policies']]
    if len(ids)!=len(set(ids)):raise ValueError('Duplicate policy identifiers')
    if len(plan['primary_fill_contrasts'])!=plan['uncertainty']['primary_family_size']:
        raise ValueError('Primary contrast family size mismatch')
    if plan['uncertainty']['primary_family_size']!=5:
        raise ValueError('Version 2 requires the declared five-contrast family')
    for contrast in plan['primary_fill_contrasts']:
        if contrast['candidate'] not in ids or contrast['baseline'] not in ids:
            raise ValueError('Contrast names a missing policy')
    calibration=plan['calibration']
    for family in calibration['families']:
        for z in calibration['z_grid']:StrategySpec(family,z).validate()
    if len(set(calibration['z_grid']))!=len(calibration['z_grid']):
        raise ValueError('Duplicate calibration multipliers')
    expected=math.ceil(calibration['required_passing_fraction']*len(dev))
    if calibration['required_passing_count']!=expected:
        raise ValueError('Development count and fraction gate disagree')
    for policy in plan['policies']:
        z=policy['z']
        if z=='development_frozen':
            if policy['predictor'] not in calibration['families']:
                raise ValueError('Calibrated family missing from grid')
        else:StrategySpec(policy['predictor'],z).validate()
    return plan


def run_development(plan_path, output, remote_plan_commit):
    require_commit(remote_plan_commit,'remote_plan_commit')
    plan=load_plan(plan_path)
    output=empty_output(output)
    config=Config(**plan['config']); cal=plan['calibration']
    rows=[]; inputs=[]
    for seed in plan['development_seeds']:
        c=replace(config,seed=seed); catalog,demands=generate(c)
        inputs.append(dict(seed=seed,input_sha256=fingerprint(c,catalog,demands)))
        for family in cal['families']:
            for z in cal['z_grid']:
                row=score_strategy(c,catalog,demands,family,family,z)
                rows.append(dict(family=family,z=z,**row))
        print(f'Development seed {seed} completed',flush=True)
    choices={family:select_calibration([r for r in rows if r['family']==family],
                                      cal['service_fill_target'],cal['required_passing_fraction'])
             for family in cal['families']}
    summary=[dict(family=family,**r) for family in cal['families'] for r in choices[family]['candidates']]
    write_csv(output/'development_metrics.csv',rows)
    write_csv(output/'development_summary.csv',summary)
    frozen=dict(schema_version='inventory-ablation-calibration/2.0',
        plan_sha256=file_sha256(plan_path),remote_plan_commit=remote_plan_commit,
        source_code_sha256=source_hashes(),config=plan['config'],
        development_seeds=plan['development_seeds'],families=choices,
        input_sha256_by_seed=inputs,
        csv_sha256={name:file_sha256(output/name) for name in ('development_metrics.csv','development_summary.csv')},
        validation_results=dict(accounting_audits_passed=len(rows),
                                evaluations_generated=0,
                                shared_initial_state_and_demand_checked=True))
    write_json(output/'frozen_calibration.json',frozen)
    return frozen


def validate_freeze(plan_path, calibration_path, remote_plan_commit):
    frozen=json.loads(Path(calibration_path).read_text(encoding='utf-8'))
    plan=load_plan(plan_path)
    if frozen.get('schema_version')!='inventory-ablation-calibration/2.0':
        raise ValueError('Unsupported calibration version')
    if frozen['plan_sha256']!=file_sha256(plan_path) or frozen['remote_plan_commit']!=remote_plan_commit:
        raise ValueError('Plan hash or plan commit differs from frozen development')
    if frozen['source_code_sha256']!=source_hashes():
        raise ValueError('Calculation source changed after calibration; preserve and refreeze before evaluation')
    if frozen['config']!=plan['config'] or frozen['development_seeds']!=plan['development_seeds']:
        raise ValueError('Frozen configuration or development split differs')
    for name,expected in frozen['csv_sha256'].items():
        if file_sha256(Path(calibration_path).parent/name)!=expected:
            raise ValueError('Development artifact differs from calibration freeze: '+name)
    for family in plan['calibration']['families']:
        choice=frozen['families'][family]
        if choice['evaluation_z'] not in plan['calibration']['z_grid']:
            raise ValueError('Frozen multiplier is outside the declared grid')
    return plan,frozen


def wilson(successes,n):
    if n==0:return None,None
    z=1.959963984540054; p=successes/n; denom=1+z*z/n
    mid=(p+z*z/(2*n))/denom
    half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/denom
    return (0.0 if successes==0 else max(0,mid-half)), (1.0 if successes==n else min(1,mid+half))


def summarize_evaluation(rows, policies, target):
    result=[]
    monetary=['modeled_cost_dollars','purchase_dollars','holding_dollars','order_dollars','shortage_dollars',
              'initial_inventory_value_dollars','mean_inventory_position_value_dollars',
              'peak_inventory_position_value_dollars','terminal_inventory_value_dollars',
              'terminal_pipeline_value_dollars']
    for spec in policies:
        rr=[r for r in rows if r['policy']==spec['id']]
        fills=[r['fill_rate'] for r in rr if r['fill_rate'] is not None]
        passing=sum(f>=target for f in fills); lo,hi=wilson(passing,len(rr))
        summary=dict(policy=spec['id'],predictor=spec['predictor'],z=spec['z'],role=spec['role'],
            calibration_status=spec.get('calibration_status','not_calibrated'),
            n_seeds=len(rr),n_valid_fill=len(fills),n_undefined_fill=len(rr)-len(fills),
            mean_fill=statistics.mean(fills) if fills else None,
            min_fill=min(fills) if fills else None,max_fill=max(fills) if fills else None,
            stdev_fill=statistics.stdev(fills) if len(fills)>1 else None,
            passing_count=passing,passing_fraction=passing/len(rr),
            passing_wilson_lower=lo,passing_wilson_upper=hi)
        for metric in monetary:
            values=[r[metric] for r in rr]
            summary['mean_'+metric]=statistics.mean(values)
            summary['min_'+metric]=min(values)
            summary['max_'+metric]=max(values)
        result.append(summary)
    return result


def run_evaluation(plan_path, calibration_path, output, remote_plan_commit, remote_calibration_commit):
    require_commit(remote_plan_commit,'remote_plan_commit')
    require_commit(remote_calibration_commit,'remote_calibration_commit')
    if remote_plan_commit==remote_calibration_commit:
        raise ValueError('Plan and calibration require distinct remote commits')
    plan,frozen=validate_freeze(plan_path,calibration_path,remote_plan_commit)
    output=empty_output(output)
    policies=[]
    for original in plan['policies']:
        spec=dict(original)
        if spec['z']=='development_frozen':
            selected=frozen['families'][spec['predictor']]
            spec['z']=selected['evaluation_z'];spec['calibration_status']=selected['status']
        policies.append(spec)
    config=Config(**plan['config']);rows=[];inputs=[];audit_samples=[]
    for seed in plan['evaluation_seeds']:
        c=replace(config,seed=seed);catalog,demands=generate(c)
        inputs.append(dict(seed=seed,input_sha256=fingerprint(c,catalog,demands)))
        cache={}
        for spec in policies:
            key=(spec['predictor'],spec['z'])
            if key not in cache:
                cache[key]=score_strategy(c,catalog,demands,spec['id'],*key,
                    audit_samples=audit_samples if seed==plan['evaluation_seeds'][0] else None)
            rows.append(dict(cache[key],policy=spec['id']))
        print(f'Evaluation seed {seed} completed',flush=True)
    summary=summarize_evaluation(rows,policies,config.service_target)
    uncertainty=plan['uncertainty'];draws=uncertainty['bootstrap_draws'];seed=uncertainty['bootstrap_rng_seed']
    comparisons=[]
    for contrast in plan['primary_fill_contrasts']:
        pair=dict(contrast_id=contrast['id'],status='primary_fill_family_of_five',
                  **paired_contrast(rows,contrast['candidate'],contrast['baseline'],'fill_rate',draws,seed))
        comparisons.append(pair)
        for metric in plan['secondary']['metrics_for_primary_policy_pairs']:
            pair=dict(contrast_id=contrast['id'],status='secondary_descriptive',
                      **paired_contrast(rows,contrast['candidate'],contrast['baseline'],metric,draws,seed))
            pair['lower_99']=None;pair['upper_99']=None
            comparisons.append(pair)
    interaction=interaction_contrast(rows,'fill_rate',draws,seed)
    comparisons.append(dict(contrast_id='factorial_interaction',status='secondary_descriptive',
        candidate='seasonal_buffer-seasonal_no_buffer',baseline='rolling_buffer-rolling_no_buffer',
        metric='fill_rate',n_undefined_pairs=interaction['n_undefined_pairs'],
        n_pairs=interaction['n_pairs'],mean_difference=interaction['mean_difference'],
        lower_95=interaction['lower_95'],upper_95=interaction['upper_95'],lower_99=None,upper_99=None))
    write_csv(output/'representative_ledger.csv',audit_samples)
    for name,rr in [('evaluation_metrics.csv',rows),('evaluation_summary.csv',summary),('paired_comparisons.csv',comparisons)]:
        write_csv(output/name,rr)
    for name in ('development_metrics.csv','development_summary.csv','frozen_calibration.json'):
        (output/name).write_bytes((Path(calibration_path).parent/name).read_bytes())
    (output/'ablation_plan_v2.json').write_bytes(Path(plan_path).read_bytes())
    manifest=dict(schema_version='inventory-ablation-results/2.0',plan_sha256=file_sha256(plan_path),
        remote_plan_commit=remote_plan_commit,remote_calibration_commit=remote_calibration_commit,
        source_code_sha256=source_hashes(),sql_sha256=file_sha256(ROOT/'sql/policy_comparison.sql'),
        frozen_calibration_sha256=file_sha256(calibration_path),policies=policies,
        input_sha256_by_seed=inputs,csv_sha256={p.name:file_sha256(p) for p in sorted(output.glob('*.csv'))},
        validation_results=dict(accounting_audits_passed=sum(len({(p['predictor'],p['z']) for p in policies}) for _ in plan['evaluation_seeds']),
            reported_policy_seed_rows=len(rows),representative_ledger_rows=len(audit_samples),
            checked_identities=['inventory_balance','demand_fulfillment_loss','initial_endowment','receipt_timing','pipeline_conservation','purchases','fees','holding','shortage','daily_cash'],
            shared_initial_state_and_demand_checked=True,
            plan_and_calibration_hashes_verified=True,calculation_source_unchanged_since_development=True),
        provenance_note='Remote references are supplied after external GitHub verification; offline runner verifies local frozen hashes, not remote chronology.')
    write_json(output/'manifest.json',manifest)
    from .ablation_report import render_results
    markdown,html=render_results(plan,frozen,summary,comparisons,manifest)
    (output/'RESULTS.md').write_text(markdown,encoding='utf-8')
    (output/'report.html').write_text(html,encoding='utf-8')
    return summary,comparisons,manifest


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='phase',required=True)
    for phase in ('develop','evaluate'):
        command=sub.add_parser(phase)
        command.add_argument('--plan',required=True)
        command.add_argument('--output',required=True)
        command.add_argument('--plan-commit',required=True)
        if phase=='evaluate':
            command.add_argument('--calibration',required=True)
            command.add_argument('--calibration-commit',required=True)
    args=parser.parse_args()
    try:
        if args.phase=='develop':run_development(args.plan,args.output,args.plan_commit)
        else:run_evaluation(args.plan,args.calibration,args.output,args.plan_commit,args.calibration_commit)
    except (ValueError,KeyError,OSError) as exc:parser.error(str(exc))

if __name__=='__main__':main()
