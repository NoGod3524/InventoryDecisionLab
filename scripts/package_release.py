"""Package only project deliverables; exclude raw data, databases and row-level invoices."""
from pathlib import Path
import hashlib
import json
from zipfile import ZipFile,ZipInfo,ZIP_DEFLATED

root=Path(__file__).resolve().parent.parent
allowed_roots={'.github','inventory_lab','sql','tests','docs','examples','scripts'}
allowed_files={'README.md','CONTRIBUTING.md','DATA_LICENSE.md','LICENSE','VERSION','requirements.txt','.gitignore','index.html'}
files=[]
for p in root.rglob('*'):
    if not p.is_file():continue
    rel=p.relative_to(root)
    if rel.parts[0] not in allowed_roots and str(rel) not in allowed_files:continue
    if '__pycache__' in rel.parts or p.suffix in ('.pyc','.sqlite'):continue
    if p.name in ('lineage.json','adjustments.json'):continue
    files.append(p)
files.sort(key=lambda p:p.relative_to(root).as_posix())
manifest={'version':(root/'VERSION').read_text().strip(),'files':[
    {'path':p.relative_to(root).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]}
dist=root/'dist';dist.mkdir(exist_ok=True)
manifest_text=json.dumps(manifest,indent=2)+'\n'
(dist/'release-file-manifest.json').write_text(manifest_text)
with ZipFile(dist/'inventory-decision-lab.zip','w',ZIP_DEFLATED) as z:
    for p in files:
        info=ZipInfo('inventory-decision-lab/'+p.relative_to(root).as_posix(),(2020,1,1,0,0,0))
        info.compress_type=ZIP_DEFLATED
        info.external_attr=0o644 << 16
        z.writestr(info,p.read_bytes())
    info=ZipInfo('inventory-decision-lab/RELEASE_MANIFEST.json',(2020,1,1,0,0,0));info.compress_type=ZIP_DEFLATED
    z.writestr(info,manifest_text)
archive=dist/'inventory-decision-lab.zip'
print(f'{len(files)} project files; {archive.stat().st_size:,} archive bytes')
print('ZIP SHA256:',hashlib.sha256(archive.read_bytes()).hexdigest())
