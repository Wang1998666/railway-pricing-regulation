import difflib,hashlib,json,importlib.metadata
from pathlib import Path
from model import ROOT,dump

paper=ROOT.parent
old=(paper/'TRA-20261014-V2.tex').read_text(encoding='utf-8').splitlines(keepends=True)
new=(paper/'TRA-20261014-V3.tex').read_text(encoding='utf-8').splitlines(keepends=True)
(ROOT/'V2_to_V3.diff').write_text(''.join(difflib.unified_diff(old,new,fromfile='TRA-20261014-V2.tex',tofile='TRA-20261014-V3.tex')),encoding='utf-8')
artifacts=[paper/'TRA-20261014-V3.tex',paper/'TRA-20261014-V3.pdf',paper/'TRA-v3-policy-references.bib',paper/'TRA-references.bib',*sorted((paper/'fig').glob('case_fig*.pdf')),*sorted((paper/'tables').glob('v3_*.tex')),*sorted((ROOT/'inputs').glob('*.json')),ROOT/'analysis.json',ROOT/'verification.json',ROOT/'local_audit.json',ROOT/'E1_partial.json',ROOT/'E3_confirmations.json',ROOT/'experiment_manifest.json',ROOT/'model.py',ROOT/'run_experiments.py',ROOT/'verify.py',ROOT/'MODEL_AND_CODE_AUDIT_CN.md',ROOT/'README_CN.md']
manifest={str(p.relative_to(paper)):dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in artifacts}
dump(ROOT/'deliverable_manifest.json',dict(artifacts=manifest,source_V2_sha256=hashlib.sha256((paper/'TRA-20261014-V2.tex').read_bytes()).hexdigest(),libraries={x:importlib.metadata.version(x) for x in ['numpy','scipy','matplotlib','Pillow','PyMuPDF']},compile_passed=True,pdf_qa=json.loads((ROOT/'pdf_qa.json').read_text(encoding='utf-8'))))
print('Final manifest:',len(manifest),'artifacts')
