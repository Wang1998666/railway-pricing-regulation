"""Elasticity zero-crossing diagnostic; exact single-OD P3 masters."""
import os
for key in ['OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','OMP_NUM_THREADS']:os.environ[key]='1'
import json,time,itertools,hashlib,argparse
from concurrent.futures import ProcessPoolExecutor,as_completed
import numpy as np
from scipy.optimize import milp,Bounds,LinearConstraint
from scipy.sparse import lil_matrix
from model import ROOT,Model,solve,dump
from verify import scalar
from local_review_audit import audit
BASE=ROOT.parent/'experiments_v3_round3'
def exact_p3(m):
    gd=np.flatnonzero(m.adjustable);assert len(gd)==2 and m.W==1
    grid=np.round(np.arange(.8,m.fare_cap+.0001,.025),8);opts=[];enumerated=0
    for h in range(4):
        counts=list(itertools.product(*[range(int(m.Nmin[s,h]),int(m.Nmax[s,h])+1) for s in gd]));fares=list(itertools.product(grid,grid));best=[{},{}];batch=[]
        def process(b):
            nonlocal enumerated
            if not b:return
            enumerated+=len(b);b=np.array(b);N=np.broadcast_to(m.N0,(len(b),m.S,4)).copy();ph=np.ones((len(b),m.S,4,3))
            for j,s in enumerate(gd):N[:,s,h]=b[:,j];ph[:,s,h,:]=b[:,2+j,None]
            v=m.evaluate(N,ph,True);den=N[:,:,h,None,None]*m.seats[None,:,:,None];lf=np.divide(v['loads'][:,:,h],den,out=np.zeros_like(den+v['loads'][:,:,h]),where=den>0)
            ok=(lf.max(axis=(1,2,3))<=m.lam+1e-9)&np.all(v['paths'][:,h]<=m.cap[h]+1e-8,axis=1)&np.all(v['odservice'][:,:,h]>=m.odfloor[:,h]-1e-8,axis=1)
            for i in np.flatnonzero(ok):
                key=tuple(b[i,:2].astype(int))
                for k,obj in enumerate(['profit','welfare']):
                    score=float(v[obj][i]-(m.state_profit if obj=='profit' else 0.))
                    if key not in best[k] or score>best[k][key][1]:best[k][key]=(b[i].copy(),score)
        for ng,nd in counts:
            for fg,fd in fares:
                batch.append([ng,nd,fg,fd])
                if len(batch)>=4096:process(batch);batch=[]
        process(batch);opts.append(best)
    out=[]
    for k,obj in enumerate(['profit','welfare']):
        cols=[(h,b,score) for h,opt in enumerate(opts) for b,score in opt[k].values()];n=len(cols);mat=lil_matrix((6,n));score=np.array([c[2] for c in cols])
        for j,(h,b,z) in enumerate(cols):
            mat[h,j]=1
            for t,idx in [('G',0),('D',1)]:mat[4+idx,j]=sum(b[a]*m.cycle[s] for a,s in enumerate(gd) if m.tier[s]==t)
        res=milp(-score,integrality=np.ones(n),bounds=Bounds(0,1),constraints=LinearConstraint(mat.tocsr(),[1]*4+[-np.inf]*2,[1]*4+list(m.fleet[:2])),options={'mip_rel_gap':0.,'time_limit':180.})
        assert res.x is not None;N=m.N0.copy();ph=np.ones((m.S,4,3))
        for j,(h,b,z) in enumerate(cols):
            if res.x[j]>.5:
                for a,s in enumerate(gd):N[s,h]=b[a];ph[s,h,:]=b[2+a]
        r=m.record(N,ph,obj,'P3');upper=-float(res.mip_dual_bound)+(m.state_profit if obj=='profit' else 0.);cert=bool(res.success and r['feasible'] and abs(upper-r['objective_value'])<1e-4)
        r['meta'].update(method='period enumeration / fleet MILP; financial and retention relaxation',certificate=cert,upper_bound=upper,gap=upper-r['objective_value'],enumerated=enumerated)
        out.append(r)
    return out
def execute(job):
    ci,anchor,cap=job;path=ROOT/'runs/E16'/f'{ci}_elastic{anchor:g}_cap{cap:g}.json';start=time.perf_counter();spec=dict(slope=anchor/.8,fare_cap=cap)
    hashes={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ['model.py','calibration.py','run_round4.py','verify.py']}
    if path.exists():
        g=json.loads(path.read_text(encoding='utf-8'))
        if g.get('hashes')==hashes:return path.name,'cached'
    raw=json.loads((ROOT/'inputs'/f'{ci}.json').read_text(encoding='utf-8'));m=Model(raw,spec=spec);p0=m.record(m.N0,np.ones((m.S,4,3)),'profit','P0')
    if ci in ['HN','WC']:rec=exact_p3(m)
    else:
        warm=[r for p in (BASE/'runs/E13').glob(ci+'*.json') for r in json.loads(p.read_text(encoding='utf-8'))['records'] if r['policy'] in ['P0','P1','P2','P3']]
        warm += [r for p in (ROOT/'runs/E16').glob(ci+'*.json') for r in json.loads(p.read_text(encoding='utf-8'))['records']]
        rec=[]
        for obj in ['profit','welfare']:rec.append(solve(m,obj,'P3',seeds=warm+rec,rounds=8))
    for i,r in enumerate(rec):
        if not r['feasible'] or (ci in ['HN','WC'] and not r['meta']['certificate']):
            fallback=solve(m,r['objective'],'P3',seeds=[r]+rec,rounds=8)
            if fallback['feasible']:rec[i]=fallback
    records=[p0]+rec;errors=[];reports=[]
    base=scalar(m.c,m.N0,np.ones((m.S,4,3)),'reference','none',spec)
    for r in records:
        z=scalar(m.c,np.array(r['N']),np.array(r['phi']),'reference','none',spec);err=max(abs(z['profit']-r['profit']),abs(z['U']-r['U']),abs(z['U']-base['U']+z['profit']-base['profit']-r['welfare']));assert err<1e-5;errors.append(err)
        if r['policy']=='P3':
            q=audit(r,engine=m)
            for _ in range(3):
                if q['stable']:break
                r=solve(m,r['objective'],'P3',seeds=[r],rounds=12)
                idx=next(j for j,x in enumerate(records) if x['policy']=='P3' and x['objective']==r['objective']);records[idx]=r;q=audit(r,engine=m)
            assert q['stable'];reports.append(q)
    errors=[]
    for r in records:
        z=scalar(m.c,np.array(r['N']),np.array(r['phi']),'reference','none',spec);err=max(abs(z['profit']-r['profit']),abs(z['U']-r['U']),abs(z['U']-base['U']+z['profit']-base['profit']-r['welfare']));assert err<1e-5;errors.append(err)
    baseflow=m.evaluate(m.N0,np.ones((m.S,4,3)),True);err=float(np.max(abs(baseflow['qr'][0]-np.array(m.c['target_rail']))));assert err<1e-6 and abs(baseflow['maxlf'][0]-.88)<1e-8
    dump(path,dict(job=dict(case=ci,anchor=anchor,cap=cap,spec=spec),records=records,scalar_errors=errors,calibration_error=err,local_audits=reports,hashes=hashes,seconds=time.perf_counter()-start))
    return path.name,time.perf_counter()-start
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--probe',action='store_true');args=ap.parse_args()
    jobs=[('WC',1.,cap) for cap in [1.1,1.2,1.3]] if args.probe else [(ci,a,cap) for ci in ['HN','WC','JX'] for a in [.6,.8,.85,.9,.95,1.] for cap in [1.1,1.2,1.3]]
    if not args.probe:dump(ROOT/'experiment_manifest.json',jobs)
    with ProcessPoolExecutor(max_workers=6) as pool:
        for i,f in enumerate(as_completed([pool.submit(execute,j) for j in jobs])):print(i+1,'/',len(jobs),f.result(),flush=True)
if __name__=='__main__':main()
