"""Re-evaluate unchanged round-2 decisions under default-invariant extensions."""
import hashlib,json
import numpy as np
from model import ROOT,Model,VERSION,dump
def main():
    cases={ci:json.loads((ROOT/'inputs'/f'{ci}.json').read_text(encoding='utf-8')) for ci in ['HN','WC','JX']};count=0;maximum=0
    for p in (ROOT/'runs').glob('E*/*.json'):
        g=json.loads(p.read_text(encoding='utf-8'))
        if g['job']['experiment'] not in ['E2','E3','E4','E5','E6','E7','E8','E9','E10','E11','E12']:continue
        old={k:g.get(k) for k in ['version','solver_sha256','calibration_sha256','controller_sha256']};records=[]
        for r in g['records']:
            m=Model(cases[r['case_id']],r['income'],r['electric'],r['spec']);nr=m.record(np.array(r['N']),np.array(r['phi']),r['objective'],r['policy'],r['meta']);err=max(abs(nr[k]-r[k]) for k in ['profit','welfare','U','maxlf','eta','revenue','cost']);assert err<1e-5 and nr['feasible']==r['feasible'];maximum=max(maximum,err);records.append(nr);count+=1
        assert not g.get('budgets');g['records']=records;g['version']=VERSION;g['round3_default_reconstruction']=old
        for k,f in [('solver_sha256','model.py'),('calibration_sha256','calibration.py'),('controller_sha256','run_experiments.py')]:g[k]=hashlib.sha256((ROOT/f).read_bytes()).hexdigest()
        dump(p,g)
    dump(ROOT/'baseline_reconstruction.json',dict(records=count,maximum_error=maximum,passed=True,scope='Default fare cap 1.20; schedule scale 1; unbounded displacement; original fleet'))
    print('baseline reconstructed',count,'maximum error',maximum,flush=True)
if __name__=='__main__':main()
