"""Sequential validation, analysis, vector rendering and manuscript build."""
import os,sys,subprocess,json,time
from pathlib import Path
from model import ROOT,dump
def run(label,cmd,cwd=ROOT):
    print('STAGE',label,flush=True);start=time.perf_counter()
    with (ROOT/(label+'.log')).open('w',encoding='utf-8') as f:r=subprocess.run(cmd,cwd=cwd,stdout=f,stderr=subprocess.STDOUT)
    if r.returncode:raise RuntimeError((label,r.returncode))
    print('DONE',label,round(time.perf_counter()-start,1),flush=True)
def main():
    py=sys.executable;run('closure',[py,'-u','refine_round5.py']);run('verification',[py,'-u','verify.py']);v=json.loads((ROOT/'verification.json').read_text());assert v['passed'],v['failures'][:5]
    run('audit',[py,'-u','audit_round5.py']);run('carbon',[py,'-u','carbon_sensitivity.py']);run('review_analysis',[py,'-u','analyze_review.py']);run('mechanisms',[py,'-c','from round2_diagnostics import elasticities,mechanisms;elasticities();mechanisms()']);run('accounting',[py,'-u','analyze_round3.py']);run('round5_analysis',[py,'-u','analyze_round5.py'])
    d=json.loads((ROOT/'round5_analysis.json').read_text());assert len(d['profiles'])==54 and sum(r['certificate'] for r in d['profiles'])==36 and all(r['W_change']<0 for r in d['profiles']);assert all(r['certificate'] and r['welfare_gain']>0 for r in d['strict'][:2])
    g=json.loads((ROOT/'runs/E2/JX_reference_none.json').read_text());r=next(r for r in g['records'] if r['policy']=='P3' and r['objective']=='welfare');assert r['welfare']>=780218.69169-1e-5
    run('writing',[py,'-u','write_round5.py']);run('figures',[py,'-u','figures_round5.py']);run('latex',['latexmk','-pdf','-interaction=nonstopmode','-halt-on-error','TRA-20261014-V3.tex'],ROOT.parent);run('pdf_qa',[py,'-u','qa_pdf.py']);run('finalization',[py,'-u','finalize_round5.py']);print('ALL ROUND-FIVE STAGES COMPLETE',flush=True)
if __name__=='__main__':main()
