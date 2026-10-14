from dataclasses import replace
import unittest
import tempfile
from contextlib import redirect_stdout
from io import StringIO

from inventory_lab.core import Config,POLICIES,generate,simulate
from inventory_lab.experiments import choose_policy,interval,paired_interval,scenario_definitions,summarize,run_experiments

class ExperimentTests(unittest.TestCase):
    def test_zero_demand_mixed_seed_experiment(self):
        with tempfile.TemporaryDirectory() as tmp,redirect_stdout(StringIO()):
            summary,_=run_experiments(tmp,2,3,1,1,100)
            self.assertTrue(any(r['n_undefined_fill']>0 for r in summary))
            self.assertTrue(all(r['n_valid_fill']+r['n_undefined_fill']==3 for r in summary))

    def test_undefined_pairs_are_counted(self):
        rows=[dict(seed=1,policy='a',fill=None),dict(seed=1,policy='b',fill=None)]
        result=paired_interval(rows,'a','b','fill',100)
        self.assertEqual(result['n_pairs'],0)
        self.assertEqual(result['n_undefined_pairs'],1)
        self.assertIsNone(result['mean_difference'])

    def test_bootstrap_constant(self):
        self.assertEqual(interval([5]*30),(5,5))
        self.assertEqual(interval([1,2,3],draws=200),interval([1,2,3],draws=200))

    def test_paired_preserves_seed_match_and_direction(self):
        rows=[]
        for s in range(20):
            rows.extend([dict(seed=s,policy='a',cost=s*100+10),dict(seed=s,policy='b',cost=s*100+7)])
        result=paired_interval(list(reversed(rows)),'b','a','cost',200)
        self.assertEqual(result['mean_difference'],-3)
        self.assertEqual(result['bootstrap_lower'],-3)
        self.assertEqual(result['bootstrap_upper'],-3)

    def test_infeasible_selection_abstains(self):
        rows=[dict(seed=s,policy=p,fill_rate=.5,modeled_cost_dollars=1) for s in range(10) for p in POLICIES]
        self.assertIsNone(choose_policy(rows))

    def test_selection_uses_feasibility_before_cost(self):
        rows=[dict(seed=s,policy=p,fill_rate=.99 if p==POLICIES[1] else .5,modeled_cost_dollars=100 if p==POLICIES[1] else 1) for s in range(10) for p in POLICIES]
        self.assertEqual(choose_policy(rows),POLICIES[1])

    def test_penalty_scenarios_do_not_change_decisions(self):
        c=Config(skus=2,days=20)
        catalog,demand=generate(c)
        for policy in POLICIES:
            a=simulate(c,catalog,demand,policy)
            b=simulate(replace(c,shortage_cents=1),catalog,demand,policy)
            self.assertEqual([r['ordered'] for r in a],[r['ordered'] for r in b])

    def test_scenarios_keep_demand_common_when_not_stressed(self):
        c=Config(skus=2,days=20)
        _,demand=generate(c)
        for name,config in scenario_definitions(c):
            if name not in ('demand_low','demand_high','joint_stress'):
                self.assertEqual(generate(config)[1],demand)

    def test_sql_summary_retains_policy_comparison(self):
        c=Config(skus=2,days=20)
        catalog,demand=generate(c)
        rows=[]
        for p in POLICIES:rows.extend(simulate(c,catalog,demand,p))
        result=summarize(rows)
        self.assertEqual(len(result),3)
        self.assertEqual(len({r['demand_units'] for r in result}),1)

if __name__=='__main__':unittest.main()
