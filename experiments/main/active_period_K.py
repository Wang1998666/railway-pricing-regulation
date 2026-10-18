"""Additional K restricted to periods already served by its parent family."""
import os
for key in ['OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','OMP_NUM_THREADS']:os.environ[key]='1'
import json
from concurrent.futures import ProcessPoolExecutor
import numpy as np
from model import ROOT,Model,solve,dump
from verify import scalar

def run(job):
    ci,cost=job; raw=json.loads((ROOT/'inputs'/f'{ci}.json').read_text(encoding='utf-8'));m=Model(raw,spec={'k_cost':cost,'active_period_K':True})
    for s,parent in m.parent.items():m.Nmax[s,m.N0[parent]==0]=0
    path=ROOT/'runs/E2'/f'{ci}_reference_none.json';warm=json.loads(path.read_text(encoding='utf-8'))['records'];records=[];base=scalar(m.c,m.N0,np.ones((m.S,4,3)),'reference','none',m.spec)
    for policy in ['P3','P4']:
        for obj in ['profit','welfare']:
            r=solve(m,obj,policy,seeds=records+warm); records.append(r)
    errors=[]
    for r in records:
        a=scalar(m.c,np.array(r['N']),np.array(r['phi']),'reference','none',m.spec);err=max(abs(a['profit']-r['profit']),abs(a['U']-base['U']+a['profit']-base['profit']-r['welfare']));assert err<1e-5;assert np.all(np.array(r['N'])<=m.Nmax);errors.append(err)
    return dict(case_id=ci,k_cost=cost,records=records,scalar_errors=errors)
if __name__=='__main__':
    with ProcessPoolExecutor(max_workers=3) as pool:rows=list(pool.map(run,[(ci,cost) for ci in ['HN','WC','JX'] for cost in [1.,.1]]))
    dump(ROOT/'active_period_K.json',rows);print([(r['case_id'],r['k_cost'],[(x['objective'],x['feasible'],int(np.array(x['N'])[[p['candidate'] for p in json.loads((ROOT/'inputs'/f'{r["case_id"]}.json').read_text(encoding='utf-8'))['products']]].sum())) for x in r['records'] if x['policy']=='P4']) for r in rows])
