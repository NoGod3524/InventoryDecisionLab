from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from unittest.mock import patch

from inventory_lab.core import Config
from inventory_lab.replay import run_replay

class ReplayTests(unittest.TestCase):
    def test_fixture_outputs_label_currency_and_provenance(self):
        with tempfile.TemporaryDirectory() as tmp,redirect_stdout(StringIO()):
            rows,metadata=run_replay('tests/fixtures/retail.csv',tmp,Config(skus=2,warmup=28,days=4),'2020-01-01',fixture=True)
            self.assertEqual(len(rows),3)
            self.assertTrue(metadata['fixture'])
            self.assertIn('modeled_cost_gbp',rows[0])
            self.assertNotIn('modeled_cost_dollars',rows[0])
            self.assertNotIn('lineage',metadata)
            report=(Path(tmp)/'report.html').read_text()
            self.assertIn('not actual UCI data',report)
            self.assertIn('2020-01-01',report)
            for filename in ('lineage.json','adjustments.json','manifest.json','daily_ledger.csv'):
                self.assertNotIn('"CustomerID":',(Path(tmp)/filename).read_text())

    def test_report_uses_configured_service_target(self):
        summary = [{'policy': 'rolling_mean', 'fill_rate': 0.95,
                    'modeled_cost_dollars': 1, 'purchase_dollars': 1}]
        with tempfile.TemporaryDirectory() as tmp, redirect_stdout(StringIO()), \
                patch('inventory_lab.replay.summarize', return_value=summary):
            run_replay('tests/fixtures/retail.csv', tmp,
                       Config(skus=2, warmup=28, days=4, service_target=1.0),
                       '2020-01-01', fixture=True)
            report = (Path(tmp) / 'report.html').read_text()
            self.assertIn('95.00%', report)
            self.assertIn('No policy reaches the 100% recorded-sales fulfillment gate', report)
            self.assertNotIn('No policy reaches the 95%', report)

    def test_replay_preserves_existing_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            f=Path(tmp)/'report.html';f.write_text('keep me')
            with self.assertRaises(ValueError):run_replay('tests/fixtures/retail.csv',tmp,Config(skus=2,warmup=28,days=4),'2020-01-01',fixture=True)
            self.assertEqual(f.read_text(),'keep me')

if __name__=='__main__':unittest.main()
