"""v3 search/confirmation tests use only tiny fixtures and old public seeds."""
from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from inventory_lab.budget_search import (choose_policy,load_plan,run_development,
                                         run_confirmation,validate_freeze)


def fixture_plan():
    return dict(schema_version='inventory-minimum-budget-plan/3.0',
        config=dict(skus=2,days=8,warmup=28,daily_budget_cents=100,service_target=0),
        policies=[dict(id='rolling',predictor='rolling_mean',z=3.29),dict(id='weekday',predictor='weekday',z=3.29)],
        development_cohorts=[dict(id='old_development',seeds=[7,17])],
        confirmation_cohorts=[dict(id='test_confirmation_A',seeds=[27,37]),dict(id='test_confirmation_B',seeds=[47,19])],
        budget_search=dict(start_cents=100,stop_cents_inclusive=300,step_cents=100,minimum_claim_scope='unit-test fixture only'),
        selection=dict(fill_target=0,required_passes_per_cohort=2,required_seeds_per_cohort=2),
        confirmation=dict(required_passes_per_cohort=2,required_seeds_per_cohort=2,baseline_budget_cents=100),
        uncertainty=dict(paired_metrics=['fill_rate','modeled_cost_dollars','purchase_dollars','mean_inventory_position_value_dollars'],bootstrap_draws=100,bootstrap_rng_seed=913))


def fake_row(policy,cohort,seed,fill,cost=10,capital=100,budget=100):
    row=dict(policy=policy,cohort=cohort,seed=seed,fill_rate=fill,budget_cents=budget,
             modeled_cost_dollars=cost,mean_inventory_position_value_dollars=capital)
    for key in ('purchase_dollars','holding_dollars','order_dollars','shortage_dollars','initial_inventory_value_dollars',
                'peak_inventory_position_value_dollars','terminal_inventory_value_dollars','terminal_pipeline_value_dollars'):row[key]=1.
    return row


class BudgetSearchTests(unittest.TestCase):
    def test_cannot_pool_away_failed_cohort_or_mix_policies(self):
        plan=fixture_plan();plan['selection']['fill_target']=.95
        plan['development_cohorts']=[dict(id=c,seeds=[1,2]) for c in ('A','B')]
        rows=[fake_row(p,c,s,.99 if ((p=='rolling' and c=='A') or (p=='weekday' and c=='B')) else .5)
              for p in ('rolling','weekday') for c in ('A','B') for s in (1,2)]
        self.assertIsNone(choose_policy(rows,plan))

    def test_cost_then_capital_then_policy_ties(self):
        plan=fixture_plan();rows=[fake_row(p,'old_development',s,1,cost=10,capital=200 if p=='rolling' else 100)
                                  for p in ('rolling','weekday') for s in (7,17)]
        self.assertEqual(choose_policy(rows,plan),'weekday')
        for r in rows:r['mean_inventory_position_value_dollars']=100
        self.assertEqual(choose_policy(rows,plan),'rolling')

    def test_undefined_fill_does_not_pass_zero_target(self):
        plan=fixture_plan();rows=[fake_row(p,'old_development',s,None) for p in ('rolling','weekday') for s in (7,17)]
        self.assertIsNone(choose_policy(rows,plan))

    def test_search_visits_all_lower_levels_and_stops_first_qualifying(self):
        plan=fixture_plan();plan['config']['service_target']=.95;plan['selection']['fill_target']=.95
        visited=[]
        def score(task):
            c,_,_,policy,cohort,role=task;visited.append(c.daily_budget_cents)
            fill=.96 if c.daily_budget_cents==200 else .2  # deliberately non-monotone
            return fake_row(policy['id'],cohort,c.seed,fill,cost=10 if policy['id']=='rolling' else 11,budget=c.daily_budget_cents)
        with tempfile.TemporaryDirectory() as tmp,redirect_stdout(StringIO()),patch('inventory_lab.budget_search._score_task',side_effect=score):
            p=Path(tmp)/'plan.json';p.write_text(json.dumps(plan))
            frozen=run_development(p,Path(tmp)/'dev','a'*40,workers=1)
            self.assertEqual(frozen['visited_budgets_cents'],[100,200]);self.assertNotIn(300,visited)
            self.assertEqual(frozen['selected_policy'],'rolling');self.assertEqual(frozen['selected_budget_cents'],200)
            validate_freeze(p,Path(tmp)/'dev/frozen_budget_selection.json','a'*40)

    def test_infeasible_exhaustion_never_generates_confirmation(self):
        plan=fixture_plan();plan['config']['service_target']=1;plan['selection']['fill_target']=1
        def score(task):
            c,_,_,policy,cohort,role=task
            return fake_row(policy['id'],cohort,c.seed,.1,budget=c.daily_budget_cents)
        with tempfile.TemporaryDirectory() as tmp,redirect_stdout(StringIO()),patch('inventory_lab.budget_search._score_task',side_effect=score):
            p=Path(tmp)/'plan.json';p.write_text(json.dumps(plan));f=Path(tmp)/'dev/frozen_budget_selection.json'
            frozen=run_development(p,f.parent,'a'*40,workers=1)
            self.assertEqual(frozen['visited_budgets_cents'],[100,200,300]);self.assertIsNone(frozen['selected_policy'])
            with patch('inventory_lab.budget_search.generate') as generator:
                with self.assertRaisesRegex(ValueError,'No feasible development choice'):
                    run_confirmation(p,f,Path(tmp)/'confirmation','a'*40,'b'*40,workers=1)
                generator.assert_not_called()

    def test_fixture_phases_isolation_both_blocks_reproduce_and_source_guard(self):
        from inventory_lab.core import generate
        generated=[]
        def track(c):generated.append(c.seed);return generate(c)
        with tempfile.TemporaryDirectory() as tmp,redirect_stdout(StringIO()):
            tmp=Path(tmp);p=tmp/'plan.json';p.write_text(json.dumps(fixture_plan()))
            with patch('inventory_lab.budget_search.generate',side_effect=track):
                frozen=run_development(p,tmp/'dev','a'*40,workers=1)
            self.assertEqual(generated,[7,17]);self.assertEqual(frozen['validation_results']['confirmation_paths_generated'],0)
            f=tmp/'dev/frozen_budget_selection.json'
            with patch('inventory_lab.budget_search.generate',side_effect=track):
                summary,pairs,manifest=run_confirmation(p,f,tmp/'confirm','a'*40,'b'*40,workers=1)
            self.assertEqual(generated,[7,17,27,37,47,19]);self.assertEqual(len(summary),4);self.assertEqual(len(pairs),4)
            run_confirmation(p,f,tmp/'repeat','a'*40,'b'*40,workers=2)
            for output in (tmp/'confirm').iterdir():self.assertEqual(output.read_bytes(),(tmp/'repeat'/output.name).read_bytes())
            self.assertTrue(manifest['validation_results']['both_confirmation_cohorts_completed'])
            with patch('inventory_lab.budget_search.computation_hashes',return_value={}):
                with self.assertRaisesRegex(ValueError,'source changed'):validate_freeze(p,f,'a'*40)
            with self.assertRaisesRegex(ValueError,'empty output'):run_confirmation(p,f,tmp/'confirm','a'*40,'b'*40,workers=1)

    def test_overlap_and_missing_grid_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'plan.json';plan=fixture_plan();plan['confirmation_cohorts'][0]['seeds']=[7,27]
            p.write_text(json.dumps(plan))
            with self.assertRaisesRegex(ValueError,'overlap'):load_plan(p)

if __name__=='__main__':unittest.main()
