"""Prospective v3 search for a qualifying budget in a declared grid/policy class.

Development uses only the declared already-observed cohorts. Fresh confirmation
requires a separately published budget/policy freeze. The original v2 source,
parameters, reports and failed evidence are never rewritten.
"""
import argparse
from concurrent.futures import ProcessPoolExecutor
from dataclasses import replace
import csv
import json
from pathlib import Path
import statistics

from .core import Config,StrategySpec,generate,fingerprint
from .ablation import (file_sha256,source_hashes,write_json,write_csv,empty_output,
                       require_commit,score_strategy,paired_contrast,wilson)

ROOT=Path(__file__).resolve().parent.parent


def computation_hashes():
    return dict(source_hashes(),**{name:file_sha256(ROOT/name) for name in
                ('inventory_lab/budget_search.py','inventory_lab/budget_report.py')})


def load_plan(path):
    plan=json.loads(Path(path).read_text())
    if plan.get('schema_version')!='inventory-minimum-budget-plan/3.0':
        raise ValueError('Unsupported budget-study plan')
    Config(**plan['config']).validate()
    original=json.loads((ROOT/'examples/ablation-v2-development/frozen_calibration.json').read_text())
    if source_hashes()!=original['source_code_sha256']:
        raise ValueError('Original frozen v2 calculation sources changed')
    grid=plan['budget_search']
    if any(type(grid[k]) is not int for k in ('start_cents','stop_cents_inclusive','step_cents')):
        raise ValueError('Budget grid must use integer cents')
    if grid['start_cents']<0 or grid['step_cents']<=0 or grid['stop_cents_inclusive']<grid['start_cents']:
        raise ValueError('Invalid budget grid')
    if (grid['stop_cents_inclusive']-grid['start_cents'])%grid['step_cents']:
        raise ValueError('Budget endpoint must lie on the declared grid')
    if plan['selection']['fill_target']!=plan['config']['service_target']:
        raise ValueError('Selection must retain the declared unit-service target')
    ids=[p['id'] for p in plan['policies']]
    if len(ids)!=2 or len(set(ids))!=2:raise ValueError('Version 3 requires two distinct fixed policies')
    for p in plan['policies']:StrategySpec(p['predictor'],p['z']).validate()
    all_seeds=[];cohort_ids=[]
    for key,rule in [('development_cohorts',plan['selection']),('confirmation_cohorts',plan['confirmation'])]:
        if not plan[key]:raise ValueError('Need declared cohorts')
        for cohort in plan[key]:
            seeds=cohort['seeds'];cohort_ids.append(cohort['id'])
            if len(seeds)!=rule['required_seeds_per_cohort'] or any(type(s) is not int for s in seeds):
                raise ValueError('Cohort size or seed type differs from declared rule')
            all_seeds.extend(seeds)
        if not 1<=rule['required_passes_per_cohort']<=rule['required_seeds_per_cohort']:
            raise ValueError('Invalid cohort passing requirement')
    if len(all_seeds)!=len(set(all_seeds)) or len(cohort_ids)!=len(set(cohort_ids)):
        raise ValueError('Seed overlap or duplicate cohort identifiers')
    if plan['confirmation']['baseline_budget_cents']!=plan['config']['daily_budget_cents']:
        raise ValueError('Baseline budget must retain original operating configuration')
    return plan


def cohort_summary(rows,target,required):
    result=[]
    groups=sorted({(r['budget_cents'],r['cohort'],r['policy']) for r in rows})
    for budget,cohort,policy in groups:
        rr=[r for r in rows if (r['budget_cents'],r['cohort'],r['policy'])==(budget,cohort,policy)]
        fills=[r['fill_rate'] for r in rr if r['fill_rate'] is not None]
        passing=sum(f>=target for f in fills);lo,hi=wilson(passing,len(rr))
        r=dict(budget_cents=budget,cohort=cohort,policy=policy,n_seeds=len(rr),
               n_valid_fill=len(fills),n_undefined_fill=len(rr)-len(fills),
               passing_count=passing,required_passing_count=required,qualified=passing>=required,
               passing_fraction=passing/len(rr),wilson_lower=lo,wilson_upper=hi,
               mean_fill=statistics.mean(fills) if fills else None,
               min_fill=min(fills) if fills else None,max_fill=max(fills) if fills else None)
        for field in ('modeled_cost_dollars','purchase_dollars','holding_dollars','order_dollars','shortage_dollars',
                      'initial_inventory_value_dollars','mean_inventory_position_value_dollars',
                      'peak_inventory_position_value_dollars','terminal_inventory_value_dollars','terminal_pipeline_value_dollars'):
            r['mean_'+field]=statistics.mean(x[field] for x in rr)
        result.append(r)
    return result


def choose_policy(rows,plan):
    """One policy must pass every development cohort; no pooling rescues failures."""
    rule=plan['selection'];candidates=[]
    for p in plan['policies']:
        rr=[r for r in rows if r['policy']==p['id']]
        counts={cohort['id']:sum(r['fill_rate'] is not None and r['fill_rate']>=rule['fill_target']
                                 for r in rr if r['cohort']==cohort['id'])
                for cohort in plan['development_cohorts']}
        for cohort in plan['development_cohorts']:
            if len([r for r in rr if r['cohort']==cohort['id']])!=len(cohort['seeds']):
                raise ValueError('Selection requires every declared policy/cohort/seed row')
        if all(v>=rule['required_passes_per_cohort'] for v in counts.values()):
            candidates.append((statistics.mean(r['modeled_cost_dollars'] for r in rr),
                               statistics.mean(r['mean_inventory_position_value_dollars'] for r in rr),p['id']))
    return min(candidates)[2] if candidates else None


def _score_task(task):
    c,catalog,demands,policy,cohort,role=task
    row=score_strategy(c,catalog,demands,role or policy['id'],policy['predictor'],policy['z'])
    return dict(budget_cents=c.daily_budget_cents,cohort=cohort,strategy_id=policy['id'],**row)


def _map_tasks(tasks,executor):
    return list(executor.map(_score_task,tasks,chunksize=1)) if executor else [_score_task(t) for t in tasks]


def _observed_inputs(plan):
    base=Config(**plan['config']);inputs={}
    for cohort in plan['development_cohorts']:
        for seed in cohort['seeds']:
            c=replace(base,seed=seed);inputs[seed]=generate(c)
    return inputs


def run_development(plan_path,output,remote_plan_commit,workers=4):
    require_commit(remote_plan_commit,'remote_plan_commit')
    if type(workers) is not int or not 1<=workers<=8:raise ValueError('Use 1–8 workers')
    plan=load_plan(plan_path);output=empty_output(output)
    inputs=_observed_inputs(plan);base=Config(**plan['config']);grid=plan['budget_search']
    records=[];summaries=[];hashes=[];visited=[];selected=None;selected_budget=None
    executor=ProcessPoolExecutor(max_workers=workers) if workers>1 else None
    try:
        for budget in range(grid['start_cents'],grid['stop_cents_inclusive']+1,grid['step_cents']):
            tasks=[]
            for cohort in plan['development_cohorts']:
                for seed in cohort['seeds']:
                    c=replace(base,seed=seed,daily_budget_cents=budget);catalog,demands=inputs[seed]
                    hashes.append(dict(seed=seed,budget_cents=budget,input_sha256=fingerprint(c,catalog,demands)))
                    for policy in plan['policies']:tasks.append((c,catalog,demands,policy,cohort['id'],None))
            rows=_map_tasks(tasks,executor);records.extend(rows);visited.append(budget)
            block=cohort_summary(rows,plan['selection']['fill_target'],plan['selection']['required_passes_per_cohort'])
            summaries.extend(block);selected=choose_policy(rows,plan)
            write_json(output/'search_checkpoint.json',dict(completed_budgets_cents=visited,
                latest_budget_cents=budget,latest_cohort_passes=[{k:r[k] for k in ('cohort','policy','passing_count')} for r in block],
                selected_policy=selected,confirmation_paths_generated=0))
            print(f'Completed ${budget/100:,.0f}: '+', '.join(f"{r['cohort']}/{r['policy']} {r['passing_count']}/{r['n_seeds']}" for r in block),flush=True)
            if selected is not None:selected_budget=budget;break
    finally:
        if executor:executor.shutdown()
    write_csv(output/'development_metrics.csv',records);write_csv(output/'development_summary.csv',summaries)
    frozen=dict(schema_version='inventory-minimum-budget-freeze/3.0',
        plan_sha256=file_sha256(plan_path),remote_plan_commit=remote_plan_commit,
        source_code_sha256=computation_hashes(),selected_policy=selected,selected_budget_cents=selected_budget,
        visited_budgets_cents=visited,development_cohorts=plan['development_cohorts'],policies=plan['policies'],
        minimum_claim_scope=grid['minimum_claim_scope'],selected_budget_cohort_summary=block,
        input_sha256_by_seed_and_budget=hashes,
        csv_sha256={name:file_sha256(output/name) for name in ('development_metrics.csv','development_summary.csv')},
        validation_results=dict(accounting_audits_passed=len(records),all_declared_lower_grid_points_completed=True,
            both_policies_and_all_development_cohorts_completed_at_each_level=True,
            confirmation_paths_generated=0),previous_v2_results_reference='../ablation-v2/RESULTS.md')
    write_json(output/'frozen_budget_selection.json',frozen)
    from .budget_report import development_markdown
    (output/'DEVELOPMENT.md').write_text(development_markdown(plan,frozen,summaries),encoding='utf-8')
    return frozen


def _read_selection_metrics(path):
    rows=[]
    with Path(path).open() as stream:
        for r in csv.DictReader(stream):
            rows.append(dict(r,budget_cents=int(r['budget_cents']),seed=int(r['seed']),
                fill_rate=float(r['fill_rate']) if r['fill_rate'] else None,
                modeled_cost_dollars=float(r['modeled_cost_dollars']),
                mean_inventory_position_value_dollars=float(r['mean_inventory_position_value_dollars'])))
    return rows


def validate_freeze(plan_path,freeze_path,remote_plan_commit):
    plan=load_plan(plan_path);frozen=json.loads(Path(freeze_path).read_text())
    if frozen.get('schema_version')!='inventory-minimum-budget-freeze/3.0':raise ValueError('Unsupported budget freeze')
    if frozen['plan_sha256']!=file_sha256(plan_path) or frozen['remote_plan_commit']!=remote_plan_commit:
        raise ValueError('Plan bytes or reference differ from frozen search')
    if frozen['source_code_sha256']!=computation_hashes():raise ValueError('Calculation source changed after search freeze')
    for name,digest in frozen['csv_sha256'].items():
        if file_sha256(Path(freeze_path).parent/name)!=digest:raise ValueError('Searched grid artifact changed: '+name)
    rows=_read_selection_metrics(Path(freeze_path).parent/'development_metrics.csv')
    grid=plan['budget_search'];visited=frozen['visited_budgets_cents']
    if not visited or visited!=list(range(grid['start_cents'],visited[-1]+1,grid['step_cents'])):
        raise ValueError('Search skipped lower budget grid points')
    if visited[-1]>grid['stop_cents_inclusive']:raise ValueError('Search exceeded declared grid')
    selected=None
    for i,budget in enumerate(visited):
        selected=choose_policy([r for r in rows if r['budget_cents']==budget],plan)
        if selected is not None and i!=len(visited)-1:raise ValueError('Search continued beyond first qualifying budget')
    if selected!=frozen['selected_policy'] or frozen['selected_budget_cents']!=(visited[-1] if selected else None):
        raise ValueError('Selected budget/policy differs from independently reconstructed grid decision')
    if selected is None and visited[-1]!=grid['stop_cents_inclusive']:
        raise ValueError('Infeasible search did not exhaust declared grid')
    return plan,frozen


def run_confirmation(plan_path,freeze_path,output,remote_plan_commit,remote_budget_freeze_commit,workers=4):
    require_commit(remote_plan_commit,'remote_plan_commit');require_commit(remote_budget_freeze_commit,'remote_budget_freeze_commit')
    if remote_budget_freeze_commit==remote_plan_commit:raise ValueError('Plan and budget freeze require separate commits')
    if type(workers) is not int or not 1<=workers<=8:raise ValueError('Use 1–8 workers')
    plan,frozen=validate_freeze(plan_path,freeze_path,remote_plan_commit)
    if frozen['selected_policy'] is None:raise ValueError('No feasible development choice: do not generate confirmation paths')
    output=empty_output(output);base=Config(**plan['config']);tasks=[];hashes=[]
    policy=next(p for p in plan['policies'] if p['id']==frozen['selected_policy'])
    for cohort in plan['confirmation_cohorts']:
        for seed in cohort['seeds']:
            catalog,demands=generate(replace(base,seed=seed))
            for role,budget in [('original_budget',plan['confirmation']['baseline_budget_cents']),('selected_budget',frozen['selected_budget_cents'])]:
                c=replace(base,seed=seed,daily_budget_cents=budget)
                hashes.append(dict(seed=seed,budget_cents=budget,input_sha256=fingerprint(c,catalog,demands)))
                tasks.append((c,catalog,demands,policy,cohort['id'],role))
    executor=ProcessPoolExecutor(max_workers=workers) if workers>1 else None
    try:rows=_map_tasks(tasks,executor)
    finally:
        if executor:executor.shutdown()
    summaries=cohort_summary(rows,plan['selection']['fill_target'],plan['confirmation']['required_passes_per_cohort'])
    pairs=[]
    for metric in plan['uncertainty']['paired_metrics']:
        pair=paired_contrast(rows,'selected_budget','original_budget',metric,
                            plan['uncertainty']['bootstrap_draws'],plan['uncertainty']['bootstrap_rng_seed'])
        pair.pop('lower_99');pair.pop('upper_99');pair['status']='secondary_descriptive_no_multiplicity_adjustment'
        pairs.append(pair)
    passed=all(r['qualified'] for r in summaries if r['policy']=='selected_budget')
    for name,data in [('confirmation_metrics.csv',rows),('confirmation_summary.csv',summaries),('paired_comparisons.csv',pairs)]:write_csv(output/name,data)
    for name in ('development_metrics.csv','development_summary.csv','frozen_budget_selection.json','DEVELOPMENT.md'):
        (output/name).write_bytes((Path(freeze_path).parent/name).read_bytes())
    (output/'minimum_budget_plan_v3.json').write_bytes(Path(plan_path).read_bytes())
    manifest=dict(schema_version='inventory-minimum-budget-results/3.0',plan_sha256=file_sha256(plan_path),
        remote_plan_commit=remote_plan_commit,remote_budget_freeze_commit=remote_budget_freeze_commit,
        source_code_sha256=computation_hashes(),sql_sha256=file_sha256(ROOT/'sql/policy_comparison.sql'),
        frozen_budget_selection_sha256=file_sha256(freeze_path),selected_policy=policy,
        selected_budget_cents=frozen['selected_budget_cents'],confirmation_gate_passed=passed,
        input_sha256_by_seed_and_budget=hashes,csv_sha256={p.name:file_sha256(p) for p in sorted(output.glob('*.csv'))},
        validation_results=dict(accounting_audits_passed=len(rows),
            both_confirmation_cohorts_completed=True,selected_budget_unchanged=True,
            original_model_sources_unchanged=True,all_search_lower_grid_points_verified=True),
        previous_v2_results_reference='../ablation-v2/RESULTS.md',
        interpretation='The purchasing allowance changed. Differences are conditional simulated budget effects for one frozen policy, not an algorithm improvement or real savings.')
    write_json(output/'manifest.json',manifest)
    from .budget_report import render_results
    markdown,html=render_results(plan,frozen,summaries,pairs,manifest)
    (output/'RESULTS.md').write_text(markdown,encoding='utf-8');(output/'report.html').write_text(html,encoding='utf-8')
    return summaries,pairs,manifest


def main():
    parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='phase',required=True)
    for phase in ('develop','confirm'):
        command=sub.add_parser(phase);command.add_argument('--plan',required=True)
        command.add_argument('--output',required=True);command.add_argument('--plan-commit',required=True)
        command.add_argument('--workers',type=int,default=4)
        if phase=='confirm':command.add_argument('--freeze',required=True);command.add_argument('--budget-freeze-commit',required=True)
    args=parser.parse_args()
    try:
        if args.phase=='develop':run_development(args.plan,args.output,args.plan_commit,args.workers)
        else:run_confirmation(args.plan,args.freeze,args.output,args.plan_commit,args.budget_freeze_commit,args.workers)
    except (ValueError,KeyError,OSError) as exc:parser.error(str(exc))

if __name__=='__main__':main()
