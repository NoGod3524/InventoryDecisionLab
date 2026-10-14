"""Oracle bounds tested on exhaustive tiny instances and old public seeds only."""
from dataclasses import replace
from itertools import product
import json
from pathlib import Path
import tempfile
import unittest
from inventory_lab.core import Config, POLICIES, generate, simulate
from inventory_lab.feasibility import greedy_max_units,cheapest_cost,late_review_bound,run

class FeasibilityTests(unittest.TestCase):
    def test_integer_greedy_matches_exhaustive_unit_knapsack(self):
        for costs in product((1,2,5),repeat=3):
            items=list(zip(costs,(2,3,2)))
            for budget in range(20):
                feasible=[sum(q) for q in product(range(3),range(4),range(3)) if sum(q[i]*costs[i] for i in range(3))<=budget]
                self.assertEqual(greedy_max_units(items,budget),max(feasible))
            for need in range(8):
                possible=[sum(q[i]*costs[i] for i in range(3)) for q in product(range(3),range(4),range(3)) if sum(q)==need]
                self.assertEqual(cheapest_cost(items,need),min(possible))

    def test_final_review_gifts_respect_receipt_boundary(self):
        c=Config(skus=3,days=8,warmup=28,review_days=7)
        cat=[dict(sku=str(l),unit_cost_cents=100,lead_days=l) for l in (1,2,3)]
        demand={str(l):[2]*36 for l in (1,2,3)}
        bound,certificate=late_review_bound(c,cat,demand)
        self.assertEqual(bound['final_review_day'],7)
        self.assertTrue(all(r['free_late_demand_units']==0 for r in certificate))
        c=replace(c,days=9);demand={str(l):[2]*37 for l in (1,2,3)}
        _,certificate=late_review_bound(c,cat,demand)
        self.assertEqual([r['free_late_demand_units'] for r in certificate],[2,0,0])

    def test_free_credit_never_exceeds_demand(self):
        c=Config(skus=1,days=1,warmup=28)
        cat=[dict(sku='A',unit_cost_cents=100,lead_days=1)]
        result,cert=late_review_bound(c,cat,{'A':[100]*28+[1]})
        self.assertEqual(result['optimistic_maximum_fulfilled_units'],1)
        self.assertEqual(cert[0]['residual_demand_units'],0)

    def test_zero_demand_is_undefined_not_certified_failure(self):
        c=Config(skus=1,days=1,warmup=28)
        cat=[dict(sku='A',unit_cost_cents=100,lead_days=1)]
        result,_=late_review_bound(c,cat,{'A':[0]*29})
        self.assertTrue(result['undefined_service']);self.assertFalse(result['certified_infeasible'])
        self.assertIsNone(result['optimistic_fill_ceiling'])

    def test_real_policies_cannot_exceed_oracle(self):
        for seed,budget in product((7,17),(0,1000,100000)):
            c=Config(seed=seed,skus=3,days=35,warmup=28,daily_budget_cents=budget)
            catalog,demand=generate(c);bound,_=late_review_bound(c,catalog,demand)
            for policy in POLICIES:
                fulfilled=sum(r['fulfilled'] for r in simulate(c,catalog,demand,policy))
                self.assertLessEqual(fulfilled,bound['optimistic_maximum_fulfilled_units'])

    def test_reproducible_fixture_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp);plan=tmp/'plan.json'
            plan.write_text(json.dumps(dict(config=dict(skus=2,days=8,warmup=28),development_seeds=[7,17],calibration=dict(required_passing_count=2))))
            a=run(plan,tmp/'a');b=run(plan,tmp/'b');self.assertEqual(a,b)
            for p in (tmp/'a').iterdir():self.assertEqual(p.read_bytes(),(tmp/'b'/p.name).read_bytes())
            with self.assertRaises(ValueError):run(plan,tmp/'a')

if __name__=='__main__':unittest.main()
