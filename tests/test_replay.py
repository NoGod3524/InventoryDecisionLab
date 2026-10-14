from pathlib import Path
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO

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

    def test_replay_preserves_existing_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            f=Path(tmp)/'report.html';f.write_text('keep me')
            with self.assertRaises(ValueError):run_replay('tests/fixtures/retail.csv',tmp,Config(skus=2,warmup=28,days=4),'2020-01-01',fixture=True)
            self.assertEqual(f.read_text(),'keep me')

if __name__=='__main__':unittest.main()
