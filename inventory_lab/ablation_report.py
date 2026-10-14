"""Data-driven offline v2 report; seven policies are read from the frozen registry."""
import csv
from html import escape
import json
import math


def label(policy):
    return policy.replace('_',' ').title()


def number(value,digits=2):
    return 'undefined' if value is None else f'{value:,.{digits}f}'


def percentage(value):
    return 'undefined' if value is None else f'{value:.2%}'


def money(value):
    return '$'+number(value)


def table(headers,rows):
    return '<div class="scroll"><table><thead><tr>'+''.join('<th>'+escape(str(h))+'</th>' for h in headers)+'</tr></thead><tbody>'+''.join('<tr>'+''.join('<td>'+escape(str(v))+'</td>' for v in row)+'</tr>' for row in rows)+'</tbody></table></div>'


def md_table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join('---' for _ in headers)+'|']+['| '+' | '.join(str(v) for v in row)+' |' for row in rows])


def render_results(plan,frozen,summary,comparisons,manifest):
    target=plan['config']['service_target'];required=plan['calibration']['required_passing_fraction']
    n=len(plan['evaluation_seeds']);required_n=math.ceil(required*n)
    registry={p['id']:p for p in manifest['policies']}
    by_policy={r['policy']:r for r in summary}
    primary=[r for r in comparisons if r['status']=='primary_fill_family_of_five']
    calibration_rows=[];notices=[]
    for family,choice in frozen['families'].items():
        calibration_rows.append([family,number(choice['evaluation_z']),
            'Feasible on development' if choice['chosen_for_deployment'] is not None else 'INFEASIBLE: diagnostic fallback only'])
        if choice['chosen_for_deployment'] is None:
            notices.append(f'{family}: no development candidate passed the frozen gate; z={choice["evaluation_z"]} is only an infeasible diagnostic fallback.')
    for policy in ('calibrated_base_stock','calibrated_seasonal'):
        r=by_policy[policy]
        if r['passing_count']<required_n:
            notices.append(f'{label(policy)}: {r["passing_count"]}/{n} evaluation seeds passed, below the frozen empirical requirement of {required_n}/{n}.')
    if not notices:
        notices.append('Both development-frozen calibrated policies also meet the empirical evaluation gate. This is conditional simulation evidence, not deployment approval.')
    service_headers=['Policy','z','Mean fill','Fill range','Passes','95% Wilson interval','Mean modeled cost','Mean capital']
    service_rows=[]
    for r in summary:
        service_rows.append([label(r['policy']),number(r['z']),percentage(r['mean_fill']),
            percentage(r['min_fill'])+' – '+percentage(r['max_fill']),
            f'{r["passing_count"]}/{r["n_seeds"]}',
            percentage(r['passing_wilson_lower'])+' – '+percentage(r['passing_wilson_upper']),
            money(r['mean_modeled_cost_dollars']),money(r['mean_mean_inventory_position_value_dollars'])])
    contrast_headers=['Primary fill contrast (candidate − baseline)','Mean Δ (pp)','95% interval (pp)','99% family interval (pp)','Valid / undefined']
    contrast_rows=[]
    for r in primary:
        pp=lambda v:number(None if v is None else v*100,3)
        contrast_rows.append([label(r['candidate'])+' − '+label(r['baseline']),pp(r['mean_difference']),
            pp(r['lower_95'])+' to '+pp(r['upper_95']),pp(r['lower_99'])+' to '+pp(r['upper_99']),
            f'{r["n_pairs"]} / {r["n_undefined_pairs"]}'])
    capital_headers=['Policy','Initial stock','Mean capital','Mean peak capital','Terminal on hand','Terminal pipeline','Procurement','Holding','Order fees','Shortage']
    capital_keys=['initial_inventory_value_dollars','mean_inventory_position_value_dollars','peak_inventory_position_value_dollars',
                  'terminal_inventory_value_dollars','terminal_pipeline_value_dollars','purchase_dollars','holding_dollars','order_dollars','shortage_dollars']
    capital_rows=[[label(r['policy'])]+[money(r['mean_'+key]) for key in capital_keys] for r in summary]
    development_headers=['Family','z','Dev passes','Mean fill','Mean modeled cost','Mean capital']
    development_rows=[]
    for family,choice in frozen['families'].items():
        for r in choice['candidates']:
            development_rows.append([family,number(r['z']),f'{round(r["share_meeting_target"]*r["n_seeds"])}/{r["n_seeds"]}',
                percentage(r['mean_fill']),money(r['mean_cost']),money(r['mean_capital'])])
    secondary_headers=['Contrast','Metric','Mean Δ','95% interval','Pairs']
    secondary_rows=[[r['contrast_id'],r['metric'],number(r['mean_difference'],4),
                     number(r['lower_95'],4)+' to '+number(r['upper_95'],4),r['n_pairs']]
                    for r in comparisons if r['status']=='secondary_descriptive']
    finding=[]
    for r in primary:
        if r['mean_difference'] is None:
            finding.append(f'{r["contrast_id"]}: undefined because no paired fill observations are available.')
        else:
            includes=r['lower_99']<=0<=r['upper_99']
            finding.append(f'{r["contrast_id"]}: mean fill difference {r["mean_difference"]*100:+.3f} percentage points; '
                           f'99% interval [{r["lower_99"]*100:+.3f}, {r["upper_99"]*100:+.3f}]'+
                           (' contains zero. This does not establish equivalence.' if includes else ' excludes zero under the declared approximate conditional procedure.'))
    introduction=(f'{len(plan["development_seeds"])} development seeds; {n} separate held-out seeds; seven fixed policy specifications. '
        f'The common empirical gate is fill ≥{target:.0%} in ≥{required:.0%} of seeds. '
        'The 2×2 holds the buffer at either 0 or 1.28 while changing only rolling versus weekday forecasts. '
        'The two calibrated arms receive the same development grid and selection opportunity. No held-out winner is selected.')
    limitations=('The experiment is a prospective extension of an already-explored synthetic model, not an original preregistration. '
        'All inference is conditional on this generator, deterministic lead times, full latent-demand visibility, endowed initial stock and the stated cash allocator. '
        'Raw-demand dispersion is a shared heuristic, not calibrated forecast-error uncertainty. '
        'Same starting assets and cash caps do not mean equal realized capital or equal achieved service; compare the capital and service columns together. '
        'Modeled operating cost is holding + fees + assumed shortage penalty, excluding acquisition spend, revenue and terminal salvage. '
        'Five 99% marginal percentile-bootstrap intervals form an approximate Bonferroni nominal 95% primary family; coverage is not guaranteed. '
        'Secondary contrasts are descriptive, with no multiplicity adjustment. A confidence interval containing zero does not prove equivalence. '
        'Wilson intervals describe passing fractions and do not replace the prespecified empirical gate. '
        'Undefined fill never passes; paired undefined metrics are excluded only from that contrast and counted. '
        'No real-world savings, causal business effect, competition ranking, or deployment approval is established.')
    chronology=(f'Plan commit: {manifest["remote_plan_commit"]}\nCalibration commit: {manifest["remote_calibration_commit"]}\n'
                f'Plan SHA-256: {manifest["plan_sha256"]}\nCalibration SHA-256: {manifest["frozen_calibration_sha256"]}')
    sections=[('Frozen calibration', ['Family','Frozen z','Development status'],calibration_rows),
              ('Held-out service and cost',service_headers,service_rows),
              ('Primary paired fill contrasts',contrast_headers,contrast_rows),
              ('Inventory capital and cost components',capital_headers,capital_rows),
              ('Complete development grid',development_headers,development_rows),
              ('Secondary descriptive contrasts',secondary_headers,secondary_rows)]
    markdown='# Strong baselines and component ablation: v2\n\n'+introduction+'\n\n## Decision status\n\n'+'\n'.join('- '+x for x in notices)+'\n\n## Main results\n\n'+'\n'.join('- '+x for x in finding)+'\n\n'
    for heading,headers,rr in sections:markdown+='## '+heading+'\n\n'+md_table(headers,rr)+'\n\n'
    markdown+='## Scope and interpretation\n\n'+limitations+'\n\n## Freeze chronology\n\n'+chronology+'\n\nSee manifest.json for calculation-source hashes, input fingerprints, CSV hashes and accounting checks. Exact commands are in docs/ablation_v2.md.\n'
    # Directly plot the reported capital/service pairs. No fitted curves or equal-capital claims.
    capitals=[r['mean_mean_inventory_position_value_dollars'] for r in summary]
    xmax=max(capitals+[1])*1.15
    palette=['#708090','#247c9b','#bd7a1d','#7553a8','#147d60','#b44c55','#3b546b']
    points=''
    for i,r in enumerate(summary):
        if r['mean_fill'] is None:continue
        x=80+r['mean_mean_inventory_position_value_dollars']/xmax*720;y=315-r['mean_fill']*270
        points+=f'<circle cx="{x:.2f}" cy="{y:.2f}" r="6" fill="{palette[i%len(palette)]}"><title>{escape(label(r["policy"]))}: {percentage(r["mean_fill"])}; {money(r["mean_mean_inventory_position_value_dollars"])}</title></circle><text x="{x+9:.2f}" y="{y-8+(i%2)*18:.2f}" font-size="11">{i+1}</text>'
    chart=f'<svg viewBox="0 0 900 365" role="img" aria-label="Mean fill versus mean inventory position value"><path d="M80 35V315H830" fill="none" stroke="#82939a"/><path d="M80 {315-target*270:.2f}H830" stroke="#b08030" stroke-dasharray="5 4"/><text x="18" y="50">100%</text><text x="38" y="320">0%</text><text x="80" y="346">$0</text><text x="710" y="346">{money(xmax)}</text>{points}</svg>'
    legend='<ol class="legend">'+''.join('<li>'+escape(label(r['policy']))+'</li>' for r in summary)+'</ol>'
    html='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Inventory Decision Lab · Baselines and ablation v2</title><style>
*{box-sizing:border-box}body{margin:0;background:#eef3f2;color:#18333d;font:16px/1.55 system-ui}header{background:#18333d;color:#fff;padding:42px max(24px,calc((100vw - 1240px)/2))}h1{font-size:clamp(30px,4vw,48px);line-height:1.12;margin:12px 0}header p{max-width:980px;color:#d7e8e5}main{max-width:1320px;padding:24px;margin:auto}section{background:white;border:1px solid #d7e2df;border-radius:12px;padding:24px;margin:24px 0}h2{margin-top:0}a{color:#156d69}.notice{background:#fff0c7;border-left:4px solid #b78521;padding:20px}.scroll{overflow:auto}table{border-collapse:collapse;width:100%;font-size:13px}th,td{padding:11px 8px;border-bottom:1px solid #dce6e2;text-align:right;white-space:nowrap}th:first-child,td:first-child{text-align:left}th{background:#f3f7f5}pre{white-space:pre-wrap;overflow-wrap:anywhere;max-height:450px;overflow:auto;font-size:12px}svg{width:100%;height:auto}.legend{columns:2;font-size:13px}.sub{font-size:13px;color:#4e6870}summary{cursor:pointer}nav{display:flex;gap:15px;flex-wrap:wrap}@media(max-width:650px){main{padding:12px}section{padding:16px}.legend{columns:1}}</style>'''
    html+='<header><div>INVENTORY DECISION LAB / V2 EVIDENCE</div><h1>What does the buffer buy?</h1><p>'+escape(introduction)+'</p></header><main><div class="notice"><strong>Synthetic evidence. Frozen development choices.</strong><ul>'+''.join('<li>'+escape(x)+'</li>' for x in notices)+'</ul></div><section><h2>Main results</h2><ul>'+''.join('<li>'+escape(x)+'</li>' for x in finding)+'</ul></section>'
    html+='<section><h2>Service and realized inventory capital</h2>'+chart+legend+'<p class="sub">Points are means across the same held-out seeds. The dashed line is the service target. Shared cash caps are not matched realized capital; the plotted trade-off is descriptive.</p></section>'
    for heading,headers,rr in sections:html+='<section><h2>'+escape(heading)+'</h2>'+table(headers,rr)+'</section>'
    html+='<section><h2>Scope and interpretation</h2><p>'+escape(limitations)+'</p></section><section><h2>Provenance and reproducibility</h2><pre>'+escape(chronology)+'</pre><nav>'+''.join('<a href="'+name+'">'+escape(name)+'</a>' for name in ('evaluation_metrics.csv','evaluation_summary.csv','paired_comparisons.csv','development_metrics.csv','development_summary.csv','frozen_calibration.json','ablation_plan_v2.json','representative_ledger.csv','manifest.json','RESULTS.md'))+'</nav><details><summary>Full verified local manifest</summary><pre>'+escape(json.dumps(manifest,indent=2))+'</pre></details></section></main></html>'
    return markdown,html
