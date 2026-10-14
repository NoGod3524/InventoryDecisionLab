"""Offline v3 budget-search reporting with explicit changed-budget attribution."""
from html import escape
import json
from .ablation_report import table,md_table,money,percentage,number


def development_markdown(plan,frozen,summary):
    selected=frozen['selected_policy'];budget=frozen['selected_budget_cents']
    if selected:
        status=f'Selected {selected} at {money(budget/100)} per review day. This is the first qualifying point in the declared grid and fixed two-policy class, not a global minimum.'
    else:status='No policy qualified within the complete declared grid. No confirmation paths may be generated.'
    header=['Budget','Policy','Cohort','Passes','Mean fill','Modeled cost','Mean capital']
    rows=[[money(r['budget_cents']/100),r['policy'],r['cohort'],f"{r['passing_count']}/{r['n_seeds']}",
           percentage(r['mean_fill']),money(r['mean_modeled_cost_dollars']),money(r['mean_mean_inventory_position_value_dollars'])] for r in summary]
    return '# V3 development budget search\n\n'+status+'\n\nAll development paths were observed previously. They are not fresh validation. Both fixed strategies were fully evaluated at every visited budget, without skipping lower grid points or relying on monotonicity.\n\n'+md_table(header,rows)+'\n\nOriginal v2 failure evidence and its operating configuration are preserved. Confirmation requires a separately published selected-budget/policy freeze.\n'


def render_results(plan,frozen,summary,pairs,manifest):
    budget=frozen['selected_budget_cents'];baseline=plan['confirmation']['baseline_budget_cents']
    passed=manifest['confirmation_gate_passed'];policy=frozen['selected_policy']
    n=plan['confirmation']['required_seeds_per_cohort'];k=plan['confirmation']['required_passes_per_cohort']
    title='Minimum qualifying budget within the frozen grid and policy class'
    intro=(f'The frozen policy is {policy}. Its review-day purchasing allowance increased from {money(baseline/100)} '
           f'to {money(budget/100)} ({(budget/baseline-1)*100:+.2f}%). '
           'Demand, starting assets, SKU lead times, review dates, forecasting and buffer parameters, allocator and unit-service target are unchanged. '
           'This is a changed-budget experiment, not a same-budget algorithmic improvement.')
    status=('Both fresh confirmation cohorts met the declared empirical gate.' if passed else
            'The frozen candidate failed the declared confirmation gate. Preserve the failure; do not tune on these paths.')
    chosen=[r for r in summary if r['policy']=='selected_budget']
    status+=' '+'; '.join(f"{r['cohort']}: {r['passing_count']}/{r['n_seeds']} passed (required {k}/{n})" for r in chosen)+'.'
    scope=(f"The search visited {len(frozen['visited_budgets_cents'])} consecutive budgets from {money(frozen['visited_budgets_cents'][0]/100)} "
           f"through {money(frozen['visited_budgets_cents'][-1]/100)}, in {money(plan['budget_search']['step_cents']/100)} increments. "
           'A single policy had to meet the gate in every one of three previously observed development cohorts. '
           'The first qualifying grid budget was selected; cost, capital and policy ID broke within-budget ties. '
           'The minimum claim applies only to the declared grid, two fixed z=3.29 strategies, and development qualification rule. '
           'It does not establish the continuous-budget, all-algorithm or real-world minimum.')
    headers=['Cohort','Arm','Budget','Passes','95% Wilson','Mean fill','Fill range','Mean modeled cost','Mean procurement','Mean capital']
    rows=[[r['cohort'],r['policy'],money(r['budget_cents']/100),f"{r['passing_count']}/{r['n_seeds']}",
        percentage(r['wilson_lower'])+' – '+percentage(r['wilson_upper']),percentage(r['mean_fill']),
        percentage(r['min_fill'])+' – '+percentage(r['max_fill']),money(r['mean_modeled_cost_dollars']),
        money(r['mean_purchase_dollars']),money(r['mean_mean_inventory_position_value_dollars'])] for r in summary]
    ph=['Metric','Selected minus original budget','95% descriptive interval','Paired valid / undefined']
    pr=[]
    for r in pairs:
        scale=100 if r['metric']=='fill_rate' else 1;unit=' pp' if scale==100 else ' USD'
        fmt=lambda value:('undefined' if value is None else number(value*scale,3)+unit)
        pr.append([r['metric'],fmt(r['mean_difference']),fmt(r['lower_95'])+' to '+fmt(r['upper_95']),f"{r['n_pairs']} / {r['n_undefined_pairs']}"])
    dh=['Policy','Development cohort','Passes','Mean fill','Mean modeled cost','Mean capital']
    dr=[[r['policy'],r['cohort'],f"{r['passing_count']}/{r['n_seeds']}",percentage(r['mean_fill']),
         money(r['mean_modeled_cost_dollars']),money(r['mean_mean_inventory_position_value_dollars'])] for r in frozen['selected_budget_cohort_summary']]
    limits=('The original $18,000 configuration remains a failed case, and the original development sample has an independently certified ceiling of 26/30 passing paths. '
            'The higher allowance is explicitly a new operating assumption. Both new cohorts were run under the frozen choice regardless of the first outcome. '
            'Passing 27/30 is an empirical simulation criterion, not a lower-confidence-bound rule or a real-world reliability guarantee. '
            'Wilson intervals do not change the frozen decision rule. Paired percentile-bootstrap intervals are descriptive and not multiplicity-adjusted. '
            'All previously observed v1/v2 data are development history, and this extension does not erase cumulative testing or earlier failures. '
            'Inventory capital and procurement can rise when a cash constraint is relaxed. Modeled cost excludes revenue, acquisition expenditure and terminal salvage; it is not profit or realized savings. '
            'No deployment approval, global minimum-budget claim or competition outcome is supported.')
    provenance=f"Plan commit: {manifest['remote_plan_commit']}\nBudget freeze commit: {manifest['remote_budget_freeze_commit']}\nPlan SHA-256: {manifest['plan_sha256']}\nSelection SHA-256: {manifest['frozen_budget_selection_sha256']}"
    markdown='# '+title+'\n\n'+intro+'\n\n## Confirmation status\n\n'+status+'\n\n## Search scope\n\n'+scope+'\n\n## Fresh confirmation\n\n'+md_table(headers,rows)+'\n\n## Paired budget effects\n\n'+md_table(ph,pr)+'\n\n## Development at the frozen budget\n\n'+md_table(dh,dr)+'\n\nFull visited-grid results are in DEVELOPMENT.md and development_summary.csv.\n\n## Interpretation\n\n'+limits+'\n\n## Freeze references\n\n'+provenance+'\n'
    html='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Inventory Decision Lab · Minimum budget v3</title><style>*{box-sizing:border-box}body{margin:0;background:#eef3f1;color:#18353d;font:16px/1.6 system-ui}header{background:#18353d;color:white;padding:42px max(24px,calc((100vw - 1200px)/2))}h1{font-size:clamp(30px,4vw,46px);line-height:1.15}header p{max-width:1050px}main{max-width:1300px;margin:auto;padding:24px}section{background:white;border:1px solid #d6e2dd;border-radius:12px;padding:24px;margin:22px 0}.notice{background:#fff0c7;border-left:5px solid #b9832c;padding:20px}.scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-size:13px}th,td{padding:12px 8px;border-bottom:1px solid #dce5e1;white-space:nowrap;text-align:right}td:first-child,th:first-child{text-align:left}th{background:#f1f6f3}pre{white-space:pre-wrap;overflow-wrap:anywhere;max-height:420px;overflow:auto;font-size:12px}a{color:#16766d}nav{display:flex;gap:15px;flex-wrap:wrap}@media(max-width:650px){main{padding:12px}section{padding:16px}}</style>'''
    html+='<header><div>INVENTORY DECISION LAB / V3 CHANGED-BUDGET EXPERIMENT</div><h1>'+escape(title)+'</h1><p>'+escape(intro)+'</p></header><main><div class="notice"><strong>'+escape(status)+'</strong></div><section><h2>What was minimized?</h2><p>'+escape(scope)+'</p></section><section><h2>Fresh confirmation</h2>'+table(headers,rows)+'</section><section><h2>Paired budget effects</h2>'+table(ph,pr)+'</section><section><h2>Development at the frozen budget</h2>'+table(dh,dr)+'<p><a href="DEVELOPMENT.md">Full searched grid</a> · <a href="development_summary.csv">Grid summary CSV</a></p></section><section><h2>Interpretation</h2><p>'+escape(limits)+'</p><p><a href="../ablation-v2/RESULTS.md">Preserved v2 failure evidence</a> · <a href="../feasibility-v2/RESULTS.md">Original-capacity certificate</a></p></section><section><h2>Reproducibility</h2><pre>'+escape(provenance)+'</pre><nav>'+''.join('<a href="'+name+'">'+name+'</a>' for name in ('confirmation_metrics.csv','confirmation_summary.csv','paired_comparisons.csv','development_metrics.csv','development_summary.csv','frozen_budget_selection.json','minimum_budget_plan_v3.json','manifest.json','RESULTS.md'))+'</nav><details><summary>Full manifest</summary><pre>'+escape(json.dumps(manifest,indent=2))+'</pre></details></section></main></html>'
    return markdown,html
