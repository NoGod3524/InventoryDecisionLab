import copy
from dataclasses import replace
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO

from inventory_lab.core import Config, POLICIES, generate, simulate, validate_data, fingerprint, estimate
from inventory_lab.__main__ import run


class SimulationTests(unittest.TestCase):
    def setUp(self):
        self.config = Config(skus=4, days=35)
        self.catalog, self.demands = generate(self.config)

    def test_reproducible(self):
        self.assertEqual((self.catalog,self.demands), generate(self.config))
        for p in POLICIES:
            self.assertEqual(simulate(self.config,self.catalog,self.demands,p),
                             simulate(self.config,self.catalog,self.demands,p))

    def test_accounting_properties_multiple_seeds_budgets_and_leads(self):
        for seed in range(6):
            c=replace(self.config, seed=seed, lead_days=1+seed, daily_budget_cents=(0,200,12000,900000)[seed%4])
            catalog,demand=generate(c)
            for p in POLICIES:
                rows=simulate(c,catalog,demand,p)
                for r in rows:
                    self.assertEqual(r['closing'],r['opening']+r['receipts']-r['fulfilled'])
                    self.assertGreaterEqual(r['closing'],0)
                    self.assertLessEqual(r['fulfilled'],r['demand'])
                    self.assertLessEqual(r['fulfilled'],r['opening']+r['receipts'])
                    self.assertEqual(r['lost'],r['demand']-r['fulfilled'])
                    self.assertGreaterEqual(r['daily_cash_remaining_cents'],0)
                for day in range(c.days):
                    daily=[r for r in rows if r['day']==day]
                    spend=sum(r['purchase_cents']+r['fee_cents'] for r in daily)
                    self.assertLessEqual(spend,c.daily_budget_cents)
                    self.assertEqual(daily[0]['daily_cash_remaining_cents'],c.daily_budget_cents-spend)

    def test_no_future_leakage(self):
        modified=copy.deepcopy(self.demands)
        cutoff=14
        for series in modified.values():
            series[self.config.warmup+cutoff:]=[999]* (self.config.days-cutoff)
        for p in POLICIES:
            a=simulate(self.config,self.catalog,self.demands,p)
            b=simulate(self.config,self.catalog,modified,p)
            self.assertEqual([r for r in a if r['day']<cutoff],[r for r in b if r['day']<cutoff])

    def test_common_demand_and_initial_stock(self):
        runs=[simulate(self.config,self.catalog,self.demands,p) for p in POLICIES]
        for rows in runs[1:]:
            self.assertEqual([r['demand'] for r in runs[0]],[r['demand'] for r in rows])
            self.assertEqual([r['opening'] for r in runs[0] if r['day']==0],
                             [r['opening'] for r in rows if r['day']==0])

    def test_arrivals_exact_lead_time(self):
        for policy in POLICIES:
            rows=simulate(self.config,self.catalog,self.demands,policy)
            lookup={(r['sku'],r['day']):r for r in rows}
            for sku in self.catalog:
                for day in range(self.config.days):
                    prior=lookup.get((sku['sku'],day-sku['lead_days']))
                    self.assertEqual(lookup[sku['sku'],day]['receipts'],prior['ordered'] if prior else 0)

    def test_zero_demand_and_budget(self):
        c=replace(self.config,demand_scale=0,daily_budget_cents=0)
        catalog,demand=generate(c)
        for p in POLICIES:
            rows=simulate(c,catalog,demand,p)
            self.assertTrue(all(r['ordered']==r['demand']==r['closing']==0 for r in rows))

    def test_no_budget_no_orders(self):
        c=replace(self.config,daily_budget_cents=0)
        for p in POLICIES:
            self.assertTrue(all(r['ordered']==0 for r in simulate(c,self.catalog,self.demands,p)))

    def test_fees_are_part_of_cash_cap(self):
        c=Config(skus=1,days=1,lead_days=1,review_days=2,daily_budget_cents=349,order_fee_cents=250)
        catalog=[dict(sku='A',unit_cost_cents=100,lead_days=1)]
        demands={'A':[2]*(c.warmup+c.days)}
        for policy in POLICIES:
            r=simulate(c,catalog,demands,policy)[0]
            self.assertEqual(r['requested'],2)
            self.assertEqual(r['ordered'],0)
            r=simulate(replace(c,daily_budget_cents=350),catalog,demands,policy)[0]
            self.assertEqual(r['ordered'],1)
            self.assertEqual(r['daily_cash_remaining_cents'],0)

    def test_end_of_day_order_covers_until_next_receipt(self):
        c=Config(skus=1,days=12,lead_days=1,review_days=2)
        catalog=[dict(sku='A',unit_cost_cents=100,lead_days=1)]
        demands={'A':[2]*(c.warmup+c.days)}
        rows=simulate(c,catalog,demands,'fixed_periodic')
        self.assertTrue(all(r['lost']==0 for r in rows))
        self.assertTrue(all(r['target']==4 for r in rows if r['day']%2==0))
        self.assertEqual(rows[0]['ordered'],2)
        self.assertEqual(rows[2]['ordered'],4)

    def test_nonempty_output_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            existing=Path(tmp)/'report.html';existing.write_text('user work')
            with self.assertRaises(ValueError):run([self.config],tmp)
            self.assertEqual(existing.read_text(),'user work')

    def test_constant_series_targets(self):
        self.assertEqual(estimate([3]*56,'rolling_mean',11),33)
        self.assertEqual(estimate([3]*56,'seasonal_buffer',11),33)

    def test_invalid_inputs_block(self):
        for changes in ({'days':0},{'lead_days':0},{'review_days':0},{'daily_budget_cents':-1},
                        {'skus':51},{'demand_scale':float('nan')},{'service_target':1.1},{'seed':True}):
            with self.assertRaises(ValueError): generate(replace(self.config,**changes))
        bad=copy.deepcopy(self.catalog);bad[1]['sku']=bad[0]['sku']
        with self.assertRaises(ValueError):validate_data(self.config,bad,self.demands)
        bad=copy.deepcopy(self.catalog);del bad[0]['lead_days']
        with self.assertRaises(ValueError):validate_data(self.config,bad,self.demands)
        for fault in ('orphan','missing_day','negative','fraction','boolean'):
            bad=copy.deepcopy(self.demands); key=next(iter(bad))
            if fault=='orphan':bad['unknown']=bad.pop(key)
            elif fault=='missing_day':bad[key].pop()
            else:bad[key][0]={'negative':-1,'fraction':1.1,'boolean':True}[fault]
            with self.assertRaises(ValueError):validate_data(self.config,self.catalog,bad)

    def test_fingerprint_changes_with_assumptions(self):
        self.assertNotEqual(fingerprint(self.config,self.catalog,self.demands),
            fingerprint(replace(self.config,shortage_cents=100),self.catalog,self.demands))

    def test_pipeline_conservation(self):
        for p in POLICIES:
            rows=simulate(self.config,self.catalog,self.demands,p)
            for sku in self.demands:
                a=[r for r in rows if r['sku']==sku]
                self.assertEqual(a[-1]['pipeline_units'],sum(r['ordered']-r['receipts'] for r in a))

    def test_sql_exports_and_reproducible_hashes(self):
        with tempfile.TemporaryDirectory() as tmp, redirect_stdout(StringIO()):
            a=Path(tmp)/'a';b=Path(tmp)/'b'
            summaries,ma=run([self.config],a)
            _,mb=run([self.config],b)
            self.assertEqual(ma,mb)
            self.assertEqual((a/'report.html').read_bytes(),(b/'report.html').read_bytes())
            self.assertTrue(all(v==0 for v in ma['audit'].values()))
            self.assertEqual(len(summaries),3)
            with sqlite3.connect(a/'experiment.sqlite') as db:
                rows=db.execute('SELECT SUM(fulfilled),SUM(demand) FROM policy_day WHERE policy=?',(POLICIES[0],)).fetchone()
            self.assertAlmostEqual(summaries[0]['fill_rate'],rows[0]/rows[1])
            with self.assertRaises(ValueError):run([self.config],a)

    def test_zero_demand_sql_fill_is_undefined(self):
        with tempfile.TemporaryDirectory() as tmp, redirect_stdout(StringIO()):
            rows,_=run([replace(self.config,demand_scale=0)],tmp)
            self.assertTrue(all(r['fill_rate'] is None for r in rows))

if __name__=='__main__':unittest.main()
