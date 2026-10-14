"""Independent mechanism checks; no v2 development or held-out seeds are consumed."""
import copy
from dataclasses import replace
import unittest
from inventory_lab.core import Config, StrategySpec, generate, simulate, strategy_target

class AblationCoreTests(unittest.TestCase):
    def setUp(self):
        self.config=Config(skus=3,days=35,seed=7,warmup=28)
        self.catalog,self.demands=generate(self.config)

    def test_legacy_equivalence(self):
        for policy,spec in [('fixed_periodic',StrategySpec('frozen_mean')),
                            ('rolling_mean',StrategySpec('rolling_mean')),
                            ('seasonal_buffer',StrategySpec('weekday',1.28))]:
            self.assertEqual(simulate(self.config,self.catalog,self.demands,policy),
                simulate(self.config,self.catalog,self.demands,policy,spec))

    def test_arbitrary_policy_identifier_retained(self):
        rows=simulate(self.config,self.catalog,self.demands,'new_strategy',StrategySpec('rolling_mean',1.96))
        self.assertTrue(all(r['policy']=='new_strategy' for r in rows))

    def test_no_future_leakage_all_specs(self):
        other=copy.deepcopy(self.demands)
        for values in other.values():values[self.config.warmup+14:]=[999]*21
        for predictor in ('frozen_mean','rolling_mean','weekday'):
            for z in (0,.64,1.28,3.29):
                spec=StrategySpec(predictor,z)
                a=simulate(self.config,self.catalog,self.demands,'arm',spec)
                b=simulate(self.config,self.catalog,other,'arm',spec)
                self.assertEqual([r for r in a if r['day']<14],[r for r in b if r['day']<14])

    def test_buffer_has_no_effect_on_constant_history(self):
        for predictor in ('frozen_mean','rolling_mean','weekday'):
            for z in (0,.64,1.28,3.29):
                self.assertEqual(strategy_target([3]*29,StrategySpec(predictor,z),11,3),33)

    def test_same_initial_stock_demand_and_cash_invariants(self):
        c=replace(self.config,daily_budget_cents=9999)
        reference=None
        for predictor in ('rolling_mean','weekday'):
            for z in (0,1.28,3.29):
                rows=simulate(c,self.catalog,self.demands,'arm',StrategySpec(predictor,z))
                initial=[r['opening'] for r in rows if r['day']==0]
                if reference is None:reference=initial
                self.assertEqual(initial,reference)
                for r in rows:
                    self.assertEqual(r['closing'],r['opening']+r['receipts']-r['fulfilled'])
                    self.assertGreaterEqual(r['daily_cash_remaining_cents'],0)
                for day in range(c.days):
                    today=[r for r in rows if r['day']==day]
                    spend=sum(r['purchase_cents']+r['fee_cents'] for r in today)
                    self.assertEqual(today[0]['daily_cash_remaining_cents'],c.daily_budget_cents-spend)

    def test_invalid_specs_rejected(self):
        for spec in (StrategySpec('unknown'),StrategySpec('weekday',-1),
                     StrategySpec('weekday',float('nan')),StrategySpec('weekday',True)):
            with self.assertRaises(ValueError):simulate(self.config,self.catalog,self.demands,'arm',spec)
        with self.assertRaises(ValueError):simulate(self.config,self.catalog,self.demands,'',StrategySpec('weekday'))
        with self.assertRaises(ValueError):simulate(self.config,self.catalog,self.demands,'unknown')

if __name__=='__main__':unittest.main()
