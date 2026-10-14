import argparse
import csv
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sqlite3
import statistics

from .core import Config, POLICIES, generate, simulate, fingerprint
from .report import render

ROOT = Path(__file__).resolve().parent.parent


def write_csv(path, rows):
    with path.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def run(configs, output):
    output = Path(output)
    if output.exists() and any(output.iterdir()):
        raise ValueError('Output directory is not empty; choose a new --output directory')
    output.mkdir(parents=True, exist_ok=True)
    # Refuse to overwrite a database that may contain a user's work.
    dbpath = output / 'experiment.sqlite'
    if dbpath.exists():
        raise ValueError('Output already contains experiment.sqlite; choose a new --output directory')
    for config in configs:
        config.validate()
    with sqlite3.connect(dbpath) as db:
        db.execute('PRAGMA foreign_keys=ON')
        db.execute('CREATE TABLE dim_sku(seed INTEGER, sku TEXT, unit_cost_cents INTEGER CHECK(unit_cost_cents>0), lead_days INTEGER CHECK(lead_days>0), PRIMARY KEY(seed,sku))')
        db.execute('CREATE TABLE demand(seed INTEGER, sku TEXT, day INTEGER CHECK(day>=0), units INTEGER CHECK(units>=0), PRIMARY KEY(seed,sku,day), FOREIGN KEY(seed,sku) REFERENCES dim_sku(seed,sku))')
        hashes=[]
        initialized=False
        for config in configs:
            catalog, demands=generate(config)
            hashes.append(dict(seed=config.seed, input_sha256=fingerprint(config,catalog,demands)))
            db.executemany('INSERT INTO dim_sku VALUES(?,?,?,?)',[(config.seed,r['sku'],r['unit_cost_cents'],r['lead_days']) for r in catalog])
            db.executemany('INSERT INTO demand VALUES(?,?,?,?)',[(config.seed,sku,day,value) for sku,values in demands.items() for day,value in enumerate(values)])
            for policy in POLICIES:
                rows=simulate(config,catalog,demands,policy)
                keys=list(rows[0])
                if not initialized:
                    columns=', '.join(k+' '+('TEXT' if k in ('policy','sku') else 'REAL' if k=='holding_cents' else 'INTEGER') for k in keys)
                    db.execute('CREATE TABLE policy_day('+columns+', PRIMARY KEY(seed,policy,day,sku), FOREIGN KEY(seed,sku) REFERENCES dim_sku(seed,sku), CHECK(closing=opening+receipts-fulfilled), CHECK(fulfilled<=demand), CHECK(closing>=0), CHECK(ordered>=0), CHECK(daily_cash_remaining_cents>=0))')
                    initialized=True
                db.executemany('INSERT INTO policy_day VALUES('+','.join('?' for _ in keys)+')',[tuple(r[k] for k in keys) for r in rows])
        db.row_factory=sqlite3.Row
        summaries=[dict(r) for r in db.execute((ROOT/'sql/policy_comparison.sql').read_text())]
        daily=[dict(r) for r in db.execute('SELECT seed,policy,day,SUM(closing) units FROM policy_day GROUP BY seed,policy,day ORDER BY seed,policy,day')]
        ledger=[dict(r) for r in db.execute('SELECT * FROM policy_day ORDER BY seed,policy,day,sku')]
        write_csv(output/'policy_comparison.csv',summaries)
        write_csv(output/'daily_ledger.csv',ledger)
        write_csv(output/'catalog.csv',[dict(r) for r in db.execute('SELECT * FROM dim_sku ORDER BY seed,sku')])
        write_csv(output/'demand.csv',[dict(r) for r in db.execute('SELECT * FROM demand ORDER BY seed,sku,day')])
        checks={
            'inventory_balance_errors':db.execute('SELECT COUNT(*) FROM policy_day WHERE closing<>opening+receipts-fulfilled').fetchone()[0],
            'negative_cash_rows':db.execute('SELECT COUNT(*) FROM policy_day WHERE daily_cash_remaining_cents<0').fetchone()[0],
            'budget_violation_days':sum(db.execute('SELECT COUNT(*) FROM (SELECT day,policy,SUM(purchase_cents+fee_cents) spend FROM policy_day WHERE seed=? GROUP BY day,policy HAVING spend>?)',(c.seed,c.daily_budget_cents)).fetchone()[0] for c in configs),
            'foreign_key_errors':len(db.execute('PRAGMA foreign_key_check').fetchall()),
        }
        if any(checks.values()):
            raise RuntimeError(f'Audit failed: {checks}')
    manifest=dict(version='1.0.0',data='self-authored synthetic; not observed business outcomes',configs=[asdict(c) for c in configs],inputs=hashes,audit=checks,artifacts={})
    for name in ('policy_comparison.csv','daily_ledger.csv','catalog.csv','demand.csv'):
        manifest['artifacts'][name]=hashlib.sha256((output/name).read_bytes()).hexdigest()
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    (output/'report.html').write_text(render(summaries,daily,manifest),encoding='utf-8')
    target=configs[0].service_target
    choices=[]
    lines=['# Simulated decision memo','','All results below are synthetic, conditional on manifest.json assumptions.','']
    for policy in POLICIES:
        rr=[r for r in summaries if r['policy']==policy]
        cost=statistics.mean(r['modeled_cost_dollars'] for r in rr)
        fills=[r['fill_rate'] for r in rr if r['fill_rate'] is not None]
        fill_text=f'{statistics.mean(fills):.2%}' if fills else 'undefined (zero demand)'
        lines.append(f'- {policy}: mean fill {fill_text}; mean modeled cost ${cost:,.2f}.')
        if len(fills)==len(rr) and min(fills)>=target:
            choices.append((cost,policy))
    decision=('Illustrative lowest-cost candidate: '+min(choices)[1]+' under these assumptions; consult independent held-out evidence before deployment.' if choices else 'No policy meets the target in every seed. Do not recommend one without revisiting constraints.')
    lines += ['',f'Decision gate: {target:.0%} unit fill in every seed. {decision}','','Modeled cost = end-of-day holding + order fees + lost-demand penalty. Acquisition spend is separate; ending and in-transit stock has no salvage credit. No real-world savings or profit claim is supported.','','Next: validate lost demand and supplier variability; stress the budget and lead-time assumptions; pilot prospectively.']
    (output/'decision_memo.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('\n'.join(lines[4:]))
    print(f'\nOffline report: {output / "report.html"}\nAudit: {checks}')
    return summaries,manifest


def main():
    p=argparse.ArgumentParser(description='Run a reproducible synthetic inventory-policy benchmark. No third-party dependencies.')
    p.add_argument('--output',default='output/demo')
    p.add_argument('--seeds',default='7,17,27,37,47')
    p.add_argument('--skus',type=int,default=24)
    p.add_argument('--days',type=int,default=180)
    p.add_argument('--warmup',type=int,default=56)
    p.add_argument('--lead-days',type=int,default=4)
    p.add_argument('--review-days',type=int,default=7)
    p.add_argument('--daily-budget',type=int,default=18000,help='Daily procurement allowance in whole USD, including order fees')
    p.add_argument('--shortage-penalty',type=int,default=9,help='Assumed USD per unserved unit')
    p.add_argument('--demand-scale',type=float,default=1)
    p.add_argument('--service-target',type=float,default=.95)
    args=p.parse_args()
    try:
        seeds=[int(x) for x in args.seeds.split(',')]
        if len(set(seeds))!=len(seeds): raise ValueError('Seeds must be unique')
        configs=[Config(seed=s,skus=args.skus,days=args.days,warmup=args.warmup,lead_days=args.lead_days,review_days=args.review_days,daily_budget_cents=args.daily_budget*100,shortage_cents=args.shortage_penalty*100,demand_scale=args.demand_scale,service_target=args.service_target) for s in seeds]
        run(configs,args.output)
    except (ValueError,KeyError) as error:
        p.error(str(error))

if __name__=='__main__':
    main()
