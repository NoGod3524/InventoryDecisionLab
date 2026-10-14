"""Ablation pipeline tests use only artificial fixtures and already-public old seeds."""
import copy
from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from inventory_lab.ablation import (bootstrap_paired,capital_metrics,load_plan,paired_contrast,
    interaction_contrast,run_development,run_evaluation,select_calibration,validate_freeze,wilson)

ROOT=Path(__file__).resolve().parent.parent


def fixture_plan():
    # Deliberately NOT the prospective v2 seed ranges. Never consume fresh seeds in tests.
    return dict(schema_version='inventory-ablation-plan/2.0',
        config=dict(skus=2,days=8,warmup=28,lead_days=1,review_days=2,service_target=.95),
        development_seeds=[7,17],evaluation_seeds=[27,37],
        policies=[dict(id='fixed_periodic',predictor='frozen_mean',z=0,role='legacy'),
                  dict(id='rolling_no_buffer',predictor='rolling_mean',z=0,role='factorial'),
                  dict(id='rolling_buffer',predictor='rolling_mean',z=1.28,role='factorial'),
                  dict(id='seasonal_no_buffer',predictor='weekday',z=0,role='factorial'),
                  dict(id='seasonal_buffer',predictor='weekday',z=1.28,role='factorial'),
                  dict(id='calibrated_base_stock',predictor='rolling_mean',z='development_frozen',role='strong_baseline'),
                  dict(id='calibrated_seasonal',predictor='weekday',z='development_frozen',role='candidate')],
        calibration=dict(z_grid=[0,1.28],families=['rolling_mean','weekday'],service_fill_target=.95,
                         required_passing_fraction=.9,required_passing_count=2),
        primary_fill_contrasts=[dict(id=i,candidate=a,baseline=b) for i,a,b in
            [('weekday_without_buffer','seasonal_no_buffer','rolling_no_buffer'),
             ('weekday_with_buffer','seasonal_buffer','rolling_buffer'),
             ('buffer_with_rolling','rolling_buffer','rolling_no_buffer'),
             ('buffer_with_weekday','seasonal_buffer','seasonal_no_buffer'),
             ('calibrated_forecast_comparison','calibrated_seasonal','calibrated_base_stock')]],
        secondary=dict(metrics_for_primary_policy_pairs=['modeled_cost_dollars','purchase_dollars',
            'mean_inventory_position_value_dollars','peak_inventory_position_value_dollars']),
        uncertainty=dict(primary_family_size=5,bootstrap_draws=100,bootstrap_rng_seed=913))


def candidates(fills,costs=None,capitals=None):
    result=[]
    for z,values in fills.items():
        for i,fill in enumerate(values):result.append(dict(z=z,seed=i,fill_rate=fill,
            modeled_cost_dollars=(costs or {}).get(z,100),
            mean_inventory_position_value_dollars=(capitals or {}).get(z,100)))
    return result


class AblationTests(unittest.TestCase):
    def test_calibration_feasibility_then_cost_capital_z(self):
        rows=candidates({0:[.90]*10,1:[.96]*10,2:[.96]*10,3:[.96]*10},
                        {0:1,1:100,2:100,3:100},{1:200,2:100,3:100})
        self.assertEqual(select_calibration(rows)['chosen_for_deployment'],2)

    def test_infeasible_abstains_and_diagnostic_ties(self):
        result=select_calibration(candidates({0:[.5]*10,1:[.6]*10},{0:1,1:500}))
        self.assertIsNone(result['chosen_for_deployment'])
        self.assertEqual(result['evaluation_z'],1)
        self.assertEqual(result['status'],'diagnostic_fallback_not_feasible')

    def test_undefined_never_passes_and_fallback_is_explicit(self):
        result=select_calibration(candidates({0:[None,None],1:[None,None]},{0:5,1:10}))
        self.assertIsNone(result['chosen_for_deployment']);self.assertEqual(result['evaluation_z'],0)
        self.assertTrue(all(r['share_meeting_target']==0 for r in result['candidates']))

    def test_paired_sign_seed_alignment_and_undefined(self):
        rows=[dict(seed=s,policy=p,fill_rate=(s/10+delta)) for s in range(5)
              for p,delta in [('a',0),('b',.1)]]
        rows += [dict(seed=9,policy='a',fill_rate=None),dict(seed=9,policy='b',fill_rate=.5)]
        result=paired_contrast(list(reversed(rows)),'b','a','fill_rate',100)
        self.assertAlmostEqual(result['mean_difference'],.1);self.assertEqual(result['n_pairs'],5)
        self.assertEqual(result['n_undefined_pairs'],1)
        self.assertLessEqual(result['lower_99'],result['lower_95'])
        self.assertGreaterEqual(result['upper_99'],result['upper_95'])

    def test_interaction_direction(self):
        rows=[dict(seed=s,policy=p,fill_rate=v+s*.01) for s in range(3) for p,v in
              [('rolling_no_buffer',.4),('rolling_buffer',.7),('seasonal_no_buffer',.5),('seasonal_buffer',.9)]]
        self.assertAlmostEqual(interaction_contrast(rows,'fill_rate',100)['mean_difference'],.1)

    def test_wilson_finite_at_boundaries(self):
        for k in (0,30,60):
            lo,hi=wilson(k,60);self.assertLessEqual(lo,k/60);self.assertGreaterEqual(hi,k/60)
        self.assertLess(wilson(60,60)[0],1)

    def test_bootstrap_empty_and_constant(self):
        self.assertIsNone(bootstrap_paired([])['mean_difference'])
        result=bootstrap_paired([3]*10,100)
        self.assertEqual([result[k] for k in ('mean_difference','lower_95','upper_95','lower_99','upper_99')],[3]*5)

    def test_capital_counts_paid_pipeline(self):
        catalog=[dict(sku='A',unit_cost_cents=200)]
        rows=[dict(day=0,sku='A',opening=10,closing=5,pipeline_units=3),
              dict(day=1,sku='A',opening=5,closing=2,pipeline_units=8)]
        result=capital_metrics(rows,catalog)
        self.assertEqual(result['initial_inventory_value_dollars'],20)
        self.assertEqual(result['mean_inventory_position_value_dollars'],18)
        self.assertEqual(result['peak_inventory_position_value_dollars'],20)
        self.assertEqual(result['terminal_inventory_value_dollars'],4)
        self.assertEqual(result['terminal_pipeline_value_dollars'],16)

    def test_overlap_blocked(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'plan.json';plan=fixture_plan();plan['evaluation_seeds']=[7,27]
            p.write_text(json.dumps(plan))
            with self.assertRaisesRegex(ValueError,'overlap'):load_plan(p)

    def test_two_phase_old_seed_fixture_determinism_and_freeze_guards(self):
        from inventory_lab.core import generate
        generated=[]
        def tracked(c):generated.append(c.seed);return generate(c)
        with tempfile.TemporaryDirectory() as tmp,redirect_stdout(StringIO()):
            tmp=Path(tmp);p=tmp/'plan.json';p.write_text(json.dumps(fixture_plan()))
            with patch('inventory_lab.ablation.generate',side_effect=tracked):
                frozen=run_development(p,tmp/'dev','a'*40)
            self.assertEqual(generated,[7,17])
            self.assertEqual(frozen['validation_results']['evaluations_generated'],0)
            calibration=tmp/'dev/frozen_calibration.json'
            with self.assertRaisesRegex(ValueError,'distinct'):
                run_evaluation(p,calibration,tmp/'bad','a'*40,'a'*40)
            with patch('inventory_lab.ablation.generate',side_effect=tracked):
                summary,pairs,manifest=run_evaluation(p,calibration,tmp/'eval','a'*40,'b'*40)
                run_evaluation(p,calibration,tmp/'repeat','a'*40,'b'*40)
            self.assertEqual(generated,[7,17,27,37,27,37])
            self.assertEqual(len(summary),7);self.assertEqual(len(pairs),26)
            self.assertEqual(manifest['validation_results']['reported_policy_seed_rows'],14)
            for file in (tmp/'eval').iterdir():
                self.assertEqual(file.read_bytes(),(tmp/'repeat'/file.name).read_bytes())
            html=(tmp/'eval/report.html').read_text()
            for row in summary:self.assertIn(row['policy'].replace('_',' ').title(),html)
            self.assertIn('INFEASIBLE',html) if any(v['chosen_for_deployment'] is None for v in frozen['families'].values()) else None
            with self.assertRaisesRegex(ValueError,'empty output'):
                run_evaluation(p,calibration,tmp/'eval','a'*40,'b'*40)
            with patch('inventory_lab.ablation.source_hashes',return_value={}):
                with self.assertRaisesRegex(ValueError,'source changed'):validate_freeze(p,calibration,'a'*40)
            p.write_text(p.read_text()+' ')
            with self.assertRaisesRegex(ValueError,'Plan hash'):validate_freeze(p,calibration,'a'*40)

if __name__=='__main__':unittest.main()
