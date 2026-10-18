"""Headroom factorial with full-train cost held at the central 0.88 anchor."""
import os
for key in ['OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','OMP_NUM_THREADS']: os.environ[key]='1'
import json,hashlib
from concurrent.futures import ProcessPoolExecutor
import numpy as np
from model import ROOT,Model,solve,dump
from verify import scalar
from local_review_audit import audit

def execute(job):
    ci,load,cap,var=job; c=json.loads((ROOT/'inputs'/f'{ci}.json').read_text(encoding='utf-8')); spec=dict(ref_load=load,**{'lambda':cap},variable_share=var,constant_cost_anchor=.88); m=Model(c,spec=spec)
    factor=.88/load; m.run_cost*=factor; m.fixed_cost*=factor
    for s,p in enumerate(m.c['products']): p['run_cost']*=factor; p['fixed_cost']*=factor
    m.c['full_reference_cost']*=factor
    zero=m.evaluate(m.N0,np.ones((m.S,4,3)),True,baseline=True); m.state_profit=float(zero['profit'][0]); m.state_U=float(zero['U'][0])
    warm=[]
    for path in [ROOT/'runs'/'E5'/f'{ci}_head_{load}_{cap}_{var}.json',ROOT/'runs'/'E2'/f'{ci}_reference_none.json']:
        if path.exists(): warm+=json.loads(path.read_text(encoding='utf-8'))['records']
    records=[]; errors=[]; audits=[]; scalar0=scalar(m.c,m.N0,np.ones((m.S,4,3)),'reference','none',spec)
    for pol in ['P0','P1','P2','P3']:
        pair=[]
        for obj in ['profit','welfare']:
            r=solve(m,obj,pol,seeds=records+pair+warm); pair.append(r)
        for j in range(2):
            other=pair[1-j]
            if other['feasible'] and (not pair[j]['feasible'] or other[pair[j]['objective']]>pair[j]['objective_value']+1e-6): pair[j]=solve(m,pair[j]['objective'],pol,seeds=pair)
        records+=pair
    for r in records:
        N=np.array(r['N']); ph=np.array(r['phi']); actual=scalar(m.c,N,ph,'reference','none',spec); welfare=actual['U']-scalar0['U']+actual['profit']-scalar0['profit']; eta=actual['Q'][:,2,:].sum()/scalar0['Q'][:,2,:].sum()
        err=max(abs(actual['profit']-r['profit']),abs(welfare-r['welfare']),abs(actual['maxlf']-r['maxlf']),abs(eta-r['eta'])); assert err<1e-6
        paths=np.einsum('sh,se->he',N,m.route); fleet=np.array([np.sum(N[m.tier==t]*m.cycle[m.tier==t,None]) for t in ['G','D','K']]); od=np.einsum('sh,sw->wh',N,m.serve)
        structural=np.all(N>=m.Nmin)&np.all(N<=m.Nmax)&np.all(N[m.fixed]==m.N0[m.fixed])&np.all(paths<=m.cap+1e-8)&np.all(fleet<=m.fleet+1e-8)&np.all(od>=m.odfloor)
        fea=bool(structural and actual['maxlf']<=cap+1e-9 and eta>=.95-1e-9 and actual['profit']>=-m.budget-1e-6); assert fea==r['feasible']
        errors.append(err)
        if r['policy']=='P3': audits.append(audit(r,engine=m))
    assert all(r['stable'] for r in audits)
    out=dict(job=dict(experiment='E5C',id=f'{ci}_{load}_{cap}_{var}',case=ci,income='reference',electric='none',spec=spec,policies=['P0','P1','P2','P3']),records=records,budgets=[],scalar_errors=errors,local_audits=audits,full_reference_cost=m.c['full_reference_cost'],reference_revenue=m.c['reference_revenue'])
    return out

def main():
    jobs=[(ci,load,cap,var) for ci in ['HN','WC','JX'] for load in [.85,.88,.92] for cap in [.95,1.] for var in [.5,.7,.9]]
    with ProcessPoolExecutor(max_workers=8) as pool: results=list(pool.map(execute,jobs))
    dump(ROOT/'constant_cost_grid.json',dict(program_sha256=hashlib.sha256((ROOT/'constant_cost_grid.py').read_bytes()).hexdigest(),groups=results))
    print('constant-cost grid',len(results),'records',sum(len(g['records']) for g in results),'max scalar error',max(max(g['scalar_errors']) for g in results),'local failures',sum(not r['stable'] for g in results for r in g['local_audits']))
if __name__=='__main__': main()
