"""Release packaging guard without new prospective simulation paths."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parent.parent

class AblationPackageTests(unittest.TestCase):
    def test_root_plan_and_v2_artifacts_survive_deterministic_packaging(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'scripts').mkdir();(root/'examples/ablation-v2').mkdir(parents=True)
            shutil.copy(ROOT/'scripts/package_release.py',root/'scripts/package_release.py')
            (root/'VERSION').write_text('test\n');(root/'ablation_plan_v2.json').write_text('{"fixture":true}\n')
            (root/'examples/ablation-v2/manifest.json').write_text('{"test_only":true}\n')
            (root/'data').mkdir();(root/'data/private.csv').write_text('excluded')
            subprocess.run([sys.executable,str(root/'scripts/package_release.py')],check=True,capture_output=True)
            archive=root/'dist/inventory-decision-lab.zip';first=archive.read_bytes()
            subprocess.run([sys.executable,str(root/'scripts/package_release.py')],check=True,capture_output=True)
            self.assertEqual(first,archive.read_bytes())
            with ZipFile(archive) as z:
                self.assertIn('inventory-decision-lab/ablation_plan_v2.json',z.namelist())
                self.assertIn('inventory-decision-lab/examples/ablation-v2/manifest.json',z.namelist())
                self.assertFalse(any('/data/' in name for name in z.namelist()))
                manifest=json.loads(z.read('inventory-decision-lab/RELEASE_MANIFEST.json'))
                for row in manifest['files']:
                    self.assertEqual(hashlib.sha256(z.read('inventory-decision-lab/'+row['path'])).hexdigest(),row['sha256'])

if __name__=='__main__':unittest.main()
