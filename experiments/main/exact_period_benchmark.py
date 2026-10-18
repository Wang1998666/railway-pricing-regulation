"""Full reference HN/WC P3/P4: period enumeration and fleet-coupled MILP.

The master initially relaxes finance/retention. Its upper bound certifies the
original problem only when its reconstructed optimum satisfies those floors.
No discretization of participation, profit, or utility is used.
"""
import os
for key in ['OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','OMP_NUM_THREADS']: os.environ[key]='1'
import itertools,json,time
from concurrent.futures import ProcessPoolExecutor
import numpy as np
from scipy.optimize import milp,Bounds,LinearConstraint
from scipy.sparse import lil_matrix
from model import ROOT,Model,dump
from verify import scalar

def run(ci):
    start=time.perf_counter(); raw=json.loads((ROOT/'inputs'/f'{ci}.json').read_text(encoding='utf-8')); m=Model(raw)
    gd=np.flatnonzero(m.adjustable); cand=int(np.flatnonzero(m.candidate)[0]); assert len(gd)==2 and m.W==1
    grid=np.round(np.arange(.8,1.2001,.025),8); options=[]; enumerated=0; minima=[]
    for h in range(4):
        rows=[]; counts=list(itertools.product(*[range(int(m.Nmin[s,h]),int(m.Nmax[s,h])+1) for s in gd],range(int(m.Nmax[cand,h])+1)))
        fare=list(itertools.product(grid,grid)); batch=[]
        def process(batch):
            nonlocal enumerated
            if not batch:return
            enumerated+=len(batch); b=np.array(batch); N=np.broadcast_to(m.N0,(len(b),m.S,4)).copy(); ph=np.ones((len(b),m.S,4,3))
            for j,s in enumerate(gd):N[:,s,h]=b[:,j]; ph[:,s,h,:]=b[:,3+j,None]
            N[:,cand,h]=b[:,2]; r=m.evaluate(N,ph,True)
            sn=N.copy(); sn[:,m.parent[cand]]+=N[:,cand]; sn[:,cand]=0
            den=sn[:,:,h,None,None]*m.seats[None,:,:,None]; lf=np.divide(r['loads'][:,:,h],den,out=np.zeros_like(den+r['loads'][:,:,h]),where=den>0)
            good=(lf.max(axis=(1,2,3))<=m.lam+1e-9)&np.all(r['paths'][:,h]<=m.cap[h]+1e-8,axis=1)&np.all(r['odservice'][:,:,h]>=m.odfloor[:,h]-1e-8,axis=1)
            fixed=(b[:,2]>0)*m.fixed_cost[cand]; dp=r['profit']-m.state_profit+fixed; dw=r['welfare']+fixed
            L=r['Q'][:,:,2,h].sum(axis=1)
            for i in np.flatnonzero(good):rows.append([*b[i],float(dp[i]),float(dw[i]),float(L[i])])
        for ng,nd,nk in counts:
            for fg,fd in fare:
                batch.append([ng,nd,nk,fg,fd])
                if len(batch)==8192: process(batch);batch=[]
        process(batch); arr=np.array(rows); assert len(arr); options.append(arr)
        minima.append(dict(period=h,admissible=len(arr),minimum_vulnerable_trips=float(arr[:,-1].min())))
        print(ci,'period',h,'admissible',len(arr),flush=True)
    results=[]
    for policy in ['P1','P2','P3','P4']:
        for obj,col in [('profit',5),('welfare',6)]:
            retained=[]
            for h,arr in enumerate(options):
                best={}
                for r in arr:
                    if policy!='P4' and r[2]>0:continue
                    if policy=='P1' and any(r[z]!=m.N0[s,h] for z,s in enumerate(gd)):continue
                    if policy=='P2' and any(abs(r[z]-1)>1e-8 for z in [3,4]):continue
                    key=tuple(r[:3].astype(int))
                    if key not in best or r[col]>best[key][col]:best[key]=r
                retained.extend((h,r) for r in best.values())
            n=len(retained); mat=lil_matrix((8,n+1)); score=np.zeros(n+1)
            for j,(h,r) in enumerate(retained):
                mat[h,j]=1
                for t,k in [('G',0),('D',1)]:mat[4+k,j]=sum(r[z]*m.cycle[s] for z,s in enumerate(gd) if m.tier[s]==t)
                mat[6,j]=r[2]*m.cycle[cand]; mat[7,j]=int(r[2]>0); score[j]=r[col]
            mat[7,n]=-4; score[n]=-m.fixed_cost[cand]
            khours=float((m.N0[m.tier=='K']*m.cycle[m.tier=='K',None]).sum())
            lb=np.array([1]*4+[-np.inf]*4); ub=np.array([1]*4+[m.fleet[0],m.fleet[1],m.fleet[2]-khours,0.])
            res=milp(-score,integrality=np.ones(n+1),bounds=Bounds(0,1),constraints=LinearConstraint(mat.tocsr(),lb,ub),options={'mip_rel_gap':0.,'time_limit':300.})
            assert res.x is not None
            N=m.N0.copy(); ph=np.ones((m.S,4,3)); chosen=[]
            for j,(h,r) in enumerate(retained):
                if res.x[j]>.5:
                    for z,s in enumerate(gd):N[s,h]=r[z];ph[s,h,:]=r[3+z]
                    N[cand,h]=r[2];chosen.append([h,r.tolist()])
            rec=m.record(N,ph,obj,policy,{'method':'period-enumeration/fleet-master','milp_status':int(res.status)})
            act=scalar(m.c,N,np.array(rec['phi']),'reference','none',{}); base=scalar(m.c,m.N0,np.ones((m.S,4,3)),'reference','none',{})
            error=max(abs(act['profit']-rec['profit']),abs(act['U']-base['U']+act['profit']-base['profit']-rec['welfare']))
            relaxation_upper=-float(res.mip_dual_bound)+(m.state_profit if obj=='profit' else 0.)
            cert=bool(res.success and rec['feasible'] and abs(relaxation_upper-rec['objective_value'])<1e-4)
            results.append(dict(policy=policy,objective=obj,certificate=cert,relaxed_master_upper=relaxation_upper,gap=relaxation_upper-rec['objective_value'],milp_status=int(res.status),mip_gap=float(res.mip_gap),master_columns=n+1,record=rec,scalar_error=error))
    out=dict(case_id=ci,enumerated=enumerated,periods=minima,results=results,seconds=time.perf_counter()-start)
    dump(ROOT/f'exact_period_{ci}.json',out);return out

if __name__=='__main__':
    with ProcessPoolExecutor(max_workers=2) as pool:result=list(pool.map(run,['HN','WC']))
    dump(ROOT/'exact_period_benchmark.json',dict(cases=result))
    print('certificates',[(x['case_id'],[(r['policy'],r['objective'],r['certificate'],r['gap']) for r in x['results']]) for x in result],flush=True)
