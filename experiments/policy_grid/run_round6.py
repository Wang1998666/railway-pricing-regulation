"""Focused round-six cap/floor certification and JX schedule rechecks.

The validated round-five engine and records remain immutable dependencies.
"""
import os
for k in ['OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','OMP_NUM_THREADS']:
    os.environ[k]='1'
import sys,json,time,argparse,hashlib
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor,as_completed
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'main'
sys.path.insert(0,str(BASE))
import numpy as np
from model import Model,dump
from exact_single_od import Exact
from run_round5 import multistart,engine
from analyze import groups,record
from verify import scalar

def check(m,r):
    N=np.array(r['N']);ph=np.array(r['phi']);z=scalar(m.c,N,ph,m.income,m.electric,m.spec)
    b=scalar(m.c,m.N0,np.ones((m.S,4,3)),m.income,m.electric,m.spec)
    err=max(abs(z['profit']-r['profit']),abs(z['U']-b['U']+z['profit']-b['profit']-r['welfare']),abs(z['maxlf']-r['maxlf']))
    assert err<1e-5,(m.c['id'],m.spec,err)
    assert r['feasible']
    eta=z['Q'][:,2,:].sum()/b['Q'][:,2,:].sum()
    assert abs(eta-r['eta'])<1e-9 and eta>=m.eta_floor-1e-9
    assert z['profit']>=-m.budget-1e-6 and z['maxlf']<=m.lam+1e-9
    assert np.max(abs(N-N.round()))<1e-8 and np.all(N>=m.Nmin) and np.all(N<=m.Nmax)
    assert np.array_equal(N[m.fixed],m.N0[m.fixed]) and np.all(N[m.adjustable].sum(axis=1)>=1)
    assert np.all(N.T@m.route<=m.cap+1e-8) and np.all((N.T@m.serve).T>=m.odfloor-1e-8)
    fleet=np.array([np.sum(N[m.tier==t]*m.cycle[m.tier==t,None]) for t in ['G','D','K']])
    assert np.all(fleet<=m.fleet+1e-8)
    active=(N>0)&m.adjustable[:,None];v=ph[active];step=m.spec.get('step',.025)
    assert np.all(v>=.8-1e-8) and np.all(v<=m.fare_cap+1e-8)
    assert np.max(abs((v-.8)/step-np.round((v-.8)/step)),initial=0)<1e-7
    if r['policy']!='P4':assert not N[m.candidate].any()
    if r['policy']!='P3-sb':assert np.max(abs(ph[:,:,1:]-ph[:,:,:1]),initial=0)<1e-8
    return err

def frontier(task):
    ci,cap=task;path=HERE/'grid'/f'{ci}_{cap:.2f}.json'
    if path.exists():
        saved=json.loads(path.read_text(encoding='utf-8'))
        if saved.get('complete'):return saved
    start=time.perf_counter();raw=json.loads((BASE/'inputs'/f'{ci}.json').read_text(encoding='utf-8'))
    ref=next(g for g in groups('E2') if g['job']['id']==ci+'_reference_none')
    seeds=ref['records']+[r for g in groups('E9') if g['job']['case']==ci for r in g['records']]
    m=Model(raw,spec={'fare_cap':cap,'eta':.95});ex=Exact(m,seeds);rows=[]
    for eta in [.95,.96,.97,.98,.99,1.]:
        m.spec['eta']=eta;m.eta_floor=eta
        result=ex.solve('P3','profit')
        if not result or not result.get('success'):
            opts=ex.columns('P3','profit',True)
            result=ex.master(opts,'profit',True,time_limit=600,incumbent=ex.lower_bound('P3','profit'))
            if result and 'record' in result:
                result['record']['meta'].update(certificate=result['success'],solver_backend='COPT',upper_bound=result.get('upper'),certificate_gap=result.get('gap'),finance_retention_hard=True)
        assert result and result.get('success'),(ci,cap,eta,result and {k:v for k,v in result.items() if k!='record'})
        r=result['record'];r['policy']='P3';r['meta']['certificate']=True;r['spec']=dict(m.spec)
        err=check(m,r);ex.seeds.append(r)
        active=(np.array(r['N'])>0)&m.adjustable[:,None]
        mean=float(np.sum(np.array(r['N'])[active]*np.array(r['phi'])[:,:,0][active])/np.sum(np.array(r['N'])[active]))
        rows.append(dict(case_id=ci,cap=cap,floor=eta,record=r,scalar_error=err,profit_gain=r['profit']-m.state_profit,welfare=r['welfare'],U_change=r['U']-m.state_U,departures=int(np.array(r['N']).sum()),fare=mean))
        dump(path,dict(case_id=ci,cap=cap,complete=False,rows=rows,seconds=time.perf_counter()-start))
        print('GRID',ci,cap,eta,'certified',round(r['profit']),round(r['welfare']),flush=True)
    out=dict(case_id=ci,cap=cap,complete=True,rows=rows,seconds=time.perf_counter()-start);dump(path,out);return out

def variant(label):
    path=HERE/'variants'/f'JX_{label}_served.json'
    if path.exists():return json.loads(path.read_text(encoding='utf-8'))
    g=next(g for g in groups('E14') if g['job']['id']==f'JX_{label}_served');m=engine(g['job'])
    ref=next(g for g in groups('E2') if g['job']['id']=='JX_reference_none')
    paired=[r for v in groups('E14') if v['job']['case']=='JX' and label in v['job']['id'] for r in v['records']]
    warm=g['records']+ref['records']+paired;rows=[];start=time.perf_counter()
    for pol in ['P3','P4']:
        old=record(g,pol,'welfare');new=multistart(m,pol,'welfare',warm+rows,strong=True)
        err=check(m,new);assert new['welfare']>=old['welfare']-1e-5
        rows.append(new);warm.append(new)
        print('VARIANT',label,pol,'change',new['welfare']-old['welfare'],flush=True)
    a,b=rows;out=dict(job=g['job'],records=rows,previous=g['records'],scalar_errors=[check(m,r) for r in rows],profit_increment=b['profit']-a['profit'],U_increment=b['U']-a['U'],welfare_increment=b['welfare']-a['welfare'],added_K=int(np.array(b['N'])[m.candidate].sum()),seconds=time.perf_counter()-start)
    dump(path,out);return out

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--workers',type=int,default=4);args=ap.parse_args();start=time.perf_counter()
    tasks=[(ci,cap) for ci in ['HN','WC'] for cap in [1.,1.05,1.1,1.15,1.2]]
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        jobs={pool.submit(frontier,t):str(t) for t in tasks}
        jobs.update({pool.submit(variant,l):l for l in ['schedule_half','displacement60']})
        for i,f in enumerate(as_completed(jobs)):
            r=f.result();print('COMPLETE',i+1,'/',len(jobs),jobs[f],'elapsed',round(time.perf_counter()-start,1),flush=True)
    paths=sorted((HERE/'grid').glob('*.json'));grid=[json.loads(p.read_text(encoding='utf-8')) for p in paths]
    assert len(grid)==10 and all(g['complete'] for g in grid)
    sources={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),BASE/'model.py',BASE/'exact_single_od.py',BASE/'copt_backend.py',BASE/'verify.py']}
    dump(HERE/'run_manifest.json',dict(grid_points=sum(len(g['rows']) for g in grid),grid_certificates=sum(r['record']['meta']['certificate'] for g in grid for r in g['rows']),workers=args.workers,seconds=time.perf_counter()-start,source_sha256=sources))
if __name__=='__main__':main()
