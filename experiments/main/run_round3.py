"""Fare-cap/elasticity, displacement and fleet sensitivity controller."""
import os
for key in ['OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','OMP_NUM_THREADS']:os.environ[key]='1'
import json,hashlib,time
from concurrent.futures import ProcessPoolExecutor,as_completed
import numpy as np
from model import ROOT,Model,VERSION,solve,dump
def tasks():
    out=[]
    for ci in ['HN','WC','JX']:
        for anchor in [.6,.8,1.]:
            for cap in [1.1,1.2,1.3]:out.append(dict(experiment='E13',id=f'{ci}_elastic{anchor}_cap{cap}',case=ci,income='reference',electric='none',spec={'slope':anchor/.8,'fare_cap':cap},policies=['P0','P1','P2','P3','P4']))
        for label,spec in [('central',{}),('schedule_half',{'schedule_scale':.5}),('schedule_high',{'schedule_scale':1.5}),('displacement60',{'displacement_cap':60.}),('displacement120',{'displacement_cap':120.})]:
            for active in [False,True]:out.append(dict(experiment='E14',id=f'{ci}_{label}_'+('served' if active else 'all'),case=ci,income='reference',electric='none',spec={**spec,'active_period_K':active},policies=['P0','P3','P4']))
        for scale in [1.25,1.5]:out.append(dict(experiment='E15',id=f'{ci}_fleet{scale}',case=ci,income='reference',electric='none',spec={'fleet_scale':scale},policies=['P0','P3','P4']))
    return out
def execute(job):
    start=time.perf_counter();path=ROOT/'runs'/job['experiment']/(job['id']+'.json');fingerprint=hashlib.sha256((ROOT/'inputs'/f"{job['case']}.json").read_bytes()).hexdigest();hashes={k:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for k,f in [('solver_sha256','model.py'),('calibration_sha256','calibration.py'),('controller_sha256','run_round3.py')]}
    if path.exists():
        old=json.loads(path.read_text(encoding='utf-8'))
        if old.get('job')==job and all(old.get(k)==v for k,v in hashes.items()):return job['id'],'cached'
    raw=json.loads((ROOT/'inputs'/f"{job['case']}.json").read_text(encoding='utf-8'));m=Model(raw,spec=job['spec']);warm=json.loads((ROOT/'runs/E2'/f"{job['case']}_reference_none.json").read_text(encoding='utf-8'))['records']
    if path.exists():warm+=old['records']
    for prev in (ROOT/'runs'/job['experiment']).glob(job['case']+'*.json'):
        if prev==path:continue
        g=json.loads(prev.read_text(encoding='utf-8'));warm+=g['records']
    records=[]
    for pol in job['policies']:
        pair=[]
        for obj in ['profit','welfare']:
            seeds=[r for r in records+pair+warm if pol=='P4' or np.array(r['N'])[m.candidate].sum()==0];pair.append(solve(m,obj,pol,seeds=seeds))
        for j in range(2):
            other=pair[1-j]
            if other['feasible'] and (not pair[j]['feasible'] or other[pair[j]['objective']]>pair[j]['objective_value']+1e-6):pair[j]=solve(m,pair[j]['objective'],pol,seeds=records+pair)
        records+=pair
    dump(path,dict(version=VERSION,job=job,fingerprint=fingerprint,controller_file='run_round3.py',records=records,budgets=[],seconds=time.perf_counter()-start,**hashes));return job['id'],time.perf_counter()-start
def main():
    jobs=tasks();dump(ROOT/'round3_experiment_manifest.json',jobs)
    with ProcessPoolExecutor(max_workers=8) as pool:
        for i,fu in enumerate(as_completed([pool.submit(execute,j) for j in jobs])):
            r=fu.result()
            if (i+1)%5==0 or i+1==len(jobs):print(i+1,'/',len(jobs),r,flush=True)
if __name__=='__main__':main()
