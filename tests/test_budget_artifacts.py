"""Read-only regression checks for the published v3 evidence, no simulation reruns."""
import csv
import hashlib
import json
from pathlib import Path
import statistics
import unittest

ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'examples/minimum-budget-v3'

class BudgetArtifactTests(unittest.TestCase):
    def test_stored_confirmation_metric_integrity_and_gate(self):
        manifest=json.loads((OUT/'manifest.json').read_text())
        for name,digest in manifest['csv_sha256'].items():
            self.assertEqual(hashlib.sha256((OUT/name).read_bytes()).hexdigest(),digest)
        self.assertEqual(hashlib.sha256((OUT/'minimum_budget_plan_v3.json').read_bytes()).hexdigest(),manifest['plan_sha256'])
        with (OUT/'confirmation_metrics.csv').open() as stream:rows=list(csv.DictReader(stream))
        with (OUT/'confirmation_summary.csv').open() as stream:summary=list(csv.DictReader(stream))
        self.assertEqual(len(rows),120);self.assertEqual(len(summary),4)
        selected=[]
        for r in summary:
            values=[float(v['fill_rate']) for v in rows if v['cohort']==r['cohort'] and v['policy']==r['policy']]
            self.assertEqual(len(values),30)
            count=sum(v>=.95 for v in values)
            self.assertEqual(count,int(r['passing_count']))
            self.assertAlmostEqual(statistics.mean(values),float(r['mean_fill']))
            if r['policy']=='selected_budget':selected.append(count)
        self.assertEqual(selected,[29,27]);self.assertTrue(manifest['confirmation_gate_passed'])
        self.assertEqual(manifest['selected_budget_cents'],1940000)

    def test_report_links_and_scoped_claims(self):
        import re
        text=(OUT/'report.html').read_text()
        self.assertIn('changed-budget experiment',text)
        self.assertIn('not a same-budget algorithmic improvement',text)
        self.assertIn('not a global', (OUT/'DEVELOPMENT.md').read_text())
        for link in re.findall(r'href="([^"]+)"',text):
            if '://' not in link:self.assertTrue((OUT/link).is_file(),link)
        self.assertTrue((ROOT/'docs/minimum_budget_plan_v3.json').is_file())

if __name__=='__main__':unittest.main()
