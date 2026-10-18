"""Resumable E1--E7 controller. Eight process workers; BLAS single threaded.
Every file stores its input fingerprint and exact experiment specification.
"""
import os
for name in ['OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','OMP_NUM_THREADS']: os.environ[name]='1'
import argparse, copy, hashlib, json, platform, sys, time
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor,as_completed
import numpy as np
from model import Model,ROOT,VERSION,INCOMES,ELECTRICS,dump,solve

def specs3():
    out=[('baseline',{}) ,('income_severe_uniform',{'income':'severe_uniform'}),('income_severe_polarized',{'income':'severe_polarized'})]
    out += [('electric_'+e,{'electric':e}) for e in ELECTRICS[1:]]
    for key,vals in [('money',[1.25,1.5,2.,3.]),('demand',[.75,1.25,1.5,2.]),('authority',[0.,.25,.75,1.]),('k_fare',[.9,.8,.7,.6]),('k_cost',[.75,.5,.25,.1]),('k_restart',[0.,.5,3.]),('k_time',[.9,.8,.7,.6])]:
        out += [(f'{key}_{v}',{key:v}) for v in vals]
    out += [('bundle_affordability',{'money':1.5,'k_fare':.8,'k_restart':.5}),('bundle_upgrade',{'k_time':.8,'k_cost':.5,'k_restart':.5}),('bundle_capacity',{'demand':1.5,'k_cost':.5,'k_restart':.5}),('bundle_support',{'money':1.5,'demand':1.25,'k_time':.8,'k_cost':.5,'k_fare':.8,'k_restart':0.}),('bundle_income',{'income':'severe_uniform','k_cost':.5,'k_fare':.8,'k_restart':0.})]
    assert len(out)==40,len(out)
    return out

def tasks():
    jobs=[]
    def add(ci,exp,label,spec=None,income='reference',electric='none',policies=None):
        jobs.append(dict(experiment=exp,id=ci+'_'+label,case=ci,income=income,electric=electric,spec=spec or {},policies=policies or ['P3','P4']))
    for ci in ['HN','WC','JX']:
        for income in ['reference','uniform','polarized']:
            for intensity in [0.,.05,.10,.20,.35,.50,.75,1.]:
                electric='none' if intensity==0 else 'all_high'; label=f'{income}_none' if intensity==0 else f'{income}_x{intensity:g}'
                add(ci,'E2',label,{'electric_scale':intensity,'same_state':income!='reference'},income,electric,['P0','P1','P2','P3','P4'])
            for electric in ['auto','am_low','am_high','all_low']:
                add(ci,'E2',f'{income}_{electric}',{'electric_scale':.35,'road_contrast':True,'same_state':income!='reference'},income,electric,['P0','P1','P2','P3','P4'])
        for label,spec in specs3(): add(ci,'E3',label,spec)
        nref=sum(sum(p['N0']) for p in json.loads((ROOT/'inputs'/f'{ci}.json').read_text(encoding='utf-8'))['products'])
        for income,intensity in [('reference',0.),('polarized',.35)]:
            for eta in [.9,.925,.95,.975,1.]:
                for allowance in [0.,2000.,5000.]: add(ci,'E4',f'{income}_{eta}_{int(allowance)}',{'eta':eta,'budget':allowance*nref,'electric_scale':intensity},income,'none' if intensity==0 else 'all_high')
        robust=[('grid025',{'step':.025}),('grid10',{'step':.1}),('rounds8',{'rounds':8}),('mu_sc_low',{'mu_sc':.25}),('mu_sc_high',{'mu_sc':.35}),('mu_pr_low',{'mu_pr':.4}),('mu_pr_high',{'mu_pr':.5}),('authority25',{'authority':.25}),('authority75',{'authority':.75}),('authority0',{'authority':0.}),('slope75',{'slope':.75}),('slope125',{'slope':1.25}),('homogeneous',{'homogeneous':True})]
        robust += [('grid05',{'step':.05}),('grid0125',{'step':.0125})]
        for label,spec in robust: add(ci,'E5',label,spec,policies=['P0','P1','P2','P3'])
        for load in [.85,.88,.92]:
            for cap in [.95,1.]:
                for var in [.5,.7,.9]: add(ci,'E5',f'head_{load}_{cap}_{var}',{'ref_load':load,'lambda':cap,'variable_share':var},policies=['P0','P1','P2','P3'])
        for income in ['reference','uniform','polarized']: add(ci,'E6',income,{'same_state':income!='reference'},income=income,policies=['P3','P3-sb'])
        for a,polar in enumerate([0.,.25,.5,1.,1.5]):
            for b,intensity in enumerate([0.,.25,.5,1.,1.5]): add(ci,'E7',f'{a:02d}_{b:02d}',{'dy':(polar*INCOMES['polarized']).tolist(),'electric_scale':intensity,'polarization_scale':polar},'phase','all_high')
        for chi in [.25,.5,1.]:
            for bg in [0.,.15,.30]: add(ci,'E8',f'network_{chi}_{bg}',{'chi':chi,'background':bg},policies=['P0','P3','P4'])
        for occ in [1.,3.]: add(ci,'E8',f'occupancy_{occ}',{'occupancy':occ},policies=['P0','P3','P4'])
        floors=[.95,.98,.99,.995,.997,.998,.999,.9995,1.,1.0025,1.005]
        refpath=ROOT/'runs'/'E2'/f'{ci}_reference_none.json'
        if refpath.exists():
            rr=json.loads(refpath.read_text(encoding='utf-8'))
            floors+= [r['eta'] for r in rr['records'] if r['policy']=='P3']
        for i,eta in enumerate(sorted(set(floors))): add(ci,'E9',f'reference_{i:02d}',{'eta':eta})
        for a,cost in enumerate([.1,.25,.5,.75,1.]):
            for b,intensity in enumerate([0.,.05,.10,.20,.35,.50,.75,1.]): add(ci,'E10',f'{a:02d}_{b:02d}',{'k_cost':cost,'electric_scale':intensity},electric='all_high')
        for income in ['uniform','polarized']:
            for intensity in [0.,.05,.10,.20,.35,.50,.75,1.]: add(ci,'E11',f'{income}_{intensity}',{'same_state':False,'electric_scale':intensity},income,'none' if intensity==0 else 'all_high',['P0','P1','P2','P3','P4'])
        for income in ['reference','polarized']:
            for intensity in [0.,.2]:
                for withdraw in [0.,.5,1.]:
                    for eta in [.9,.95,1.]: add(ci,'E12',f'{income}_{intensity}_{withdraw}_{eta}',{'k_withdraw':withdraw,'eta':eta,'electric_scale':intensity},income,'none' if intensity==0 else 'all_high')
    return jobs

def execute(job):
    start=time.perf_counter(); ip=ROOT/'inputs'/f"{job['case']}.json"; case=json.loads(ip.read_text(encoding='utf-8'))
    fingerprint=hashlib.sha256(ip.read_bytes()).hexdigest(); path=ROOT/'runs'/job['experiment']/(job['id']+'.json')
    if path.exists():
        prev=json.loads(path.read_text(encoding='utf-8'))
        valid_hashes=all(prev.get(k)==hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for k,f in [('solver_sha256','model.py'),('calibration_sha256','calibration.py'),('controller_sha256','run_experiments.py')])
        if prev.get('version')==VERSION and prev.get('fingerprint')==fingerprint and prev.get('job')==job and valid_hashes: return job['id'],prev['seconds'],'cached'
        # The final commitment correction only changes K-withdrawal designs.
        # Reconstruct every unaffected saved record before retaining its search.
        old_source=prev.get('solver_sha256')=='3800d5529675e56fe7e2961ce6cad4704729f0f5a4bf3c627ba568cc74d612b9' and prev.get('controller_sha256')=='5fce59e6139b3ff768707d98a82bf10e4d2c8d9884243cd1ea282f15c8271bd0'
        if old_source and prev.get('job')==job and prev.get('fingerprint')==fingerprint and not job['spec'].get('k_withdraw',0):
            rebuilt=[]
            for r in prev['records']+[b['record'] for b in prev.get('budgets',[])]:
                engine=Model(case,r['income'],r['electric'],r['spec'])
                nr=engine.record(np.array(r['N']),np.array(r['phi']),r['objective'],r['policy'],{**r['meta'],'commitment_recomputed':True})
                assert nr['feasible']==r['feasible'] and max(abs(nr[k]-r[k]) for k in ['profit','welfare','U','maxlf','eta'])<1e-6
                rebuilt.append(nr)
            count=len(prev['records']);prev['records']=rebuilt[:count]
            for b,r in zip(prev.get('budgets',[]),rebuilt[count:]):b['record']=r
            prev['source_reconstruction']={'solver':prev['solver_sha256'],'controller':prev['controller_sha256'],'scope':'K-protected designs; every saved value reconstructed'}
            for key,file in [('solver_sha256','model.py'),('calibration_sha256','calibration.py'),('controller_sha256','run_experiments.py')]:prev[key]=hashlib.sha256((ROOT/file).read_bytes()).hexdigest()
            dump(path,prev);return job['id'],prev['seconds'],'reconstructed'
    spec=job.get('spec',{}); income=spec.get('income',job.get('income','reference')); electric=spec.get('electric',job.get('electric','none'))
    model=Model(case,income,electric,spec); records=[]; discrepancy=[]; policies=job['policies']
    warm=[]
    if path.exists(): warm+=json.loads(path.read_text(encoding='utf-8'))['records']
    exactpath=ROOT/f"exact_period_{job['case']}.json"
    if exactpath.exists(): warm+=[r['record'] for r in json.loads(exactpath.read_text(encoding='utf-8'))['results'] if r['certificate']]
    # Main-matrix saved designs seed the same and nearby experimental cells.
    seedfile=ROOT/'runs'/'E2'/f"{job['case']}_{income}_{electric}.json"
    if job['experiment']!='E2' and seedfile.exists():
        rr=json.loads(seedfile.read_text(encoding='utf-8')); warm+=rr['records']
    elif (ROOT/'runs'/'E2'/f"{job['case']}_reference_none.json").exists():
        warm+=json.loads((ROOT/'runs'/'E2'/f"{job['case']}_reference_none.json").read_text(encoding='utf-8'))['records']
    oldpath=ROOT.parent/'experiments_v3_review'/'runs'/job['experiment']/(job['id']+'.json')
    if oldpath.exists(): warm+=json.loads(oldpath.read_text(encoding='utf-8'))['records']
    if job['experiment']=='E5' and job['id'].endswith('grid0125'):
        fine=ROOT/'runs'/'E2'/f"{job['case']}_reference_none.json"
        if fine.exists(): warm+=json.loads(fine.read_text(encoding='utf-8'))['records']
    for policy in policies:
        pair=[]
        for objective in ['profit','welfare']:
            seeds=[r for r in records+pair+warm if policy=='P4' or np.array(r['N'])[model.candidate].sum()==0]
            if policy!='P3-sb': seeds=[r for r in seeds if r['policy']!='P3-sb']
            rec=solve(model,objective,policy,seeds=seeds,rounds=spec.get('rounds',4),step=spec.get('step',.025))
            pair.append(rec)
        discrepancy.append(dict(policy=policy,raw_search_difference=pair[0]['feasible']!=pair[1]['feasible']))
        # Shared feasible witnesses align feasibility, independent of objective.
        if pair[0]['feasible']!=pair[1]['feasible']:
            source=next(r for r in pair if r['feasible']); index=next(i for i,r in enumerate(pair) if not r['feasible'])
            pair[index]=solve(model,pair[index]['objective'],policy,seeds=[source,pair[index]],rounds=spec.get('rounds',4),step=spec.get('step',.025))
        # Cross-evaluate both witnesses under both objectives; incumbent closure.
        for j in range(2):
            other=pair[1-j]
            if other['feasible'] and (not pair[j]['feasible'] or other[pair[j]['objective']]>pair[j]['objective_value']+1e-6):
                pair[j]=solve(model,pair[j]['objective'],policy,seeds=pair,rounds=spec.get('rounds',4),step=spec.get('step',.025))
        records+=pair
    budgets=[]
    if job['experiment']=='E2':
        for policy in ['P3','P4']:
            if not any(r['feasible'] for r in records if r['policy']==policy):
                nm=Model(case,income,electric,{**spec,'budget':1e100}); rr=solve(nm,'profit',policy,seeds=records)
                budgets.append(dict(policy=policy,budget_fixable_found=rr['feasible'],Bstar_upper_bound=max(0.,-rr['profit']) if rr['feasible'] else None,record=rr))
    out=dict(version=VERSION,fingerprint=fingerprint,solver_sha256=hashlib.sha256((ROOT/'model.py').read_bytes()).hexdigest(),calibration_sha256=hashlib.sha256((ROOT/'calibration.py').read_bytes()).hexdigest(),controller_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),job=job,records=records,budgets=budgets,search_discrepancies=discrepancy,seconds=time.perf_counter()-start)
    dump(path,out)
    return job['id'],out['seconds'],'new'

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--experiments',nargs='+',default=['E2','E3','E4','E5','E6','E7','E8','E9','E10','E11','E12']); ap.add_argument('--workers',type=int,default=8); ap.add_argument('--reference-only',action='store_true'); args=ap.parse_args()
    jobs=[j for j in tasks() if j['experiment'] in args.experiments]
    if args.reference_only: jobs=[j for j in jobs if j['experiment']=='E2' and j['id'].endswith('_reference_none')]
    dump(ROOT/'experiment_manifest.json',tasks())
    dump(ROOT/'environment.json',dict(python=sys.version,platform=platform.platform(),processor=platform.processor(),numpy=np.__version__,workers=args.workers,version=VERSION))
    start=time.perf_counter(); n=0
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures=[pool.submit(execute,j) for j in jobs]
        for f in as_completed(futures):
            result=f.result(); n+=1
            if n%10==0 or n==len(jobs): print(f'{n}/{len(jobs)} elapsed={time.perf_counter()-start:.1f}s last={result}',flush=True)
    print('COMPLETE',len(jobs),time.perf_counter()-start,flush=True)
