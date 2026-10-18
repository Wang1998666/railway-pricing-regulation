"""Independent reconstruction of the prescribed local blocks, parallel by design."""
import os
for key in ['OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','OMP_NUM_THREADS']: os.environ[key]='1'
import json,itertools,time,hashlib
from concurrent.futures import ProcessPoolExecutor,as_completed
import numpy as np
from model import ROOT,Model,dump

def audit(r,engine=None):
    if engine is None:
        c=json.loads((ROOT/'inputs'/f"{r['case_id']}.json").read_text(encoding='utf-8')); m=Model(c,r['income'],r['electric'],r['spec'])
    else: m=engine
    N=np.array(r['N']); ph=np.array(r['phi']); ph=np.where(N[:,:,None]>0,ph,1.); ph[m.tier=='K']=1.; step=r['spec'].get('step',.025); obj=r['objective']; base=m.evaluate(N,ph)[obj][0]
    nc=[(s,h) for s in range(m.S) if m.freq_adjustable[s] or (r['policy']=='P4' and m.candidate[s]) for h in range(4)]
    fc=[(s,h,b) for s in range(m.S) if m.adjustable[s] for h in range(4) if m.Nmax[s,h]>0 for b in (range(3) if r['policy']=='P3-sb' else [0]) if m.seats[s,b]>0]
    blocks=[]
    for fam,coords in [('N',nc),('F',fc)]:
        for axis in [0,1]:
            for val in sorted({x[axis] for x in coords}):
                subset=[x for x in coords if x[axis]==val]; blocks.extend((fam,subset[i:i+2]) for i in range(0,len(subset),2))
    bestgain=0.; checked=0
    for fam,coords in blocks:
        options=[]
        for x in coords:
            v=N[x] if fam=='N' else ph[x]
            options.append(sorted(set([max(m.Nmin[x],v-1),v,min(m.Nmax[x],v+1)])) if fam=='N' else [z for z in [round(v-step,8),v,round(v+step,8)] if .8-1e-9<=z<=m.fare_cap+1e-9])
        combos=list(itertools.product(*options)); nb=np.broadcast_to(N,(len(combos),*N.shape)).copy(); pb=np.broadcast_to(ph,(len(combos),*ph.shape)).copy()
        for j,x in enumerate(coords):
            for i,combo in enumerate(combos):
                if fam=='N': nb[(i,*x)]=combo[j]
                elif r['policy']=='P3-sb': pb[(i,*x)]=combo[j]
                else: pb[i,x[0],x[1],:]=combo[j]
        out=m.evaluate(nb,pb); checked+=len(combos)
        if out['feasible'].any(): bestgain=max(bestgain,float(max(out[obj][out['feasible']])-base))
    # Rebuild joint domains independently of the optimizer implementation.
    joint=[]
    for h in range(4):
        cells=[(s,h) for s in range(m.S) if (m.freq_adjustable[s] or (r['policy']=='P4' and m.candidate[s])) and m.Nmax[s,h]>0]
        joint += [cells[i:i+2] for i in range(max(1,len(cells)-1)) if cells[i:i+2]]
        if r['policy']=='P4':
            for s in np.flatnonzero(m.candidate):
                if m.Nmax[s,h]<=0:continue
                gs=[g for g in np.flatnonzero(m.adjustable) if m.Nmax[g,h]>0 and np.any(m.serve[g]&m.serve[s])]
                if gs:
                    g=max(gs,key=lambda g:(np.sum(m.serve[g]&m.serve[s])/max(1,np.sum(m.serve[g]|m.serve[s])),m.N0[g].sum()));joint.append([(g,h),(s,h)])
    for s in range(m.S):
        cells=[(s,h) for h in range(4) if m.freq_adjustable[s] and m.Nmax[s,h]>0];joint += [cells[i:i+2] for i in range(max(1,len(cells)-1)) if cells[i:i+2]]
    for cells in joint:
        tags=[];opts=[]
        for s,h in cells:
            tags.append(('N',s,h,0));opts.append(sorted(set([max(m.Nmin[s,h],N[s,h]-1),N[s,h],min(m.Nmax[s,h],N[s,h]+1)])))
            if m.adjustable[s]:
                for b in (range(3) if r['policy']=='P3-sb' else [0]):
                    if m.seats[s,b]>0:tags.append(('F',s,h,b));opts.append([v for v in [round(ph[s,h,b]-step,8),ph[s,h,b],round(ph[s,h,b]+step,8)] if .8-1e-8<=v<=m.fare_cap+1e-8])
        subsets=[[i for i,t in enumerate(tags) if t[1:3]==cell] for cell in cells] if np.prod([len(v) for v in opts])>1000 else [list(range(len(tags)))]
        for ix in subsets:
            combos=list(itertools.product(*[opts[i] for i in ix]));nb=np.broadcast_to(N,(len(combos),*N.shape)).copy();pb=np.broadcast_to(ph,(len(combos),*ph.shape)).copy()
            for j,idx in enumerate(ix):
                kind,s,h,b=tags[idx];v=np.array([c[j] for c in combos])
                if kind=='N':nb[:,s,h]=v
                elif r['policy']=='P3-sb':pb[:,s,h,b]=v
                else:pb[:,s,h,:]=v[:,None]
            out=m.evaluate(nb,pb);checked+=len(combos)
            if out['feasible'].any():bestgain=max(bestgain,float(np.max(out[obj][out['feasible']])-base))
    return dict(case_id=r['case_id'],policy=r['policy'],objective=obj,spec=r['spec'],evaluated=checked,best_gain=bestgain,stable=bestgain<=1e-5,joint_blocks=True)

def main():
    seen=set(); todo=[];keys=[];reports=[]
    solver_hash=hashlib.sha256((ROOT/'model.py').read_bytes()).hexdigest();program_hash=hashlib.sha256((ROOT/'local_review_audit.py').read_bytes()).hexdigest();previous={}
    if (ROOT/'local_audit.json').exists():
        old=json.loads((ROOT/'local_audit.json').read_text(encoding='utf-8'))
        if old.get('solver_sha256')==solver_hash and old.get('program_sha256')==program_hash:previous={r['cache_key']:r for r in old['reports']}
    for p in (ROOT/'runs').glob('E*/*.json'):
        g=json.loads(p.read_text(encoding='utf-8'))
        for r in g['records']:
            if r['policy'] not in ['P3','P4','P3-sb'] or not r['feasible']: continue
            key=json.dumps([r['case_id'],r['income'],r['electric'],r['spec'],r['policy'],r['objective'],r['N'],r['phi']],sort_keys=True)
            if key in seen: continue
            seen.add(key);cachekey=hashlib.sha256(key.encode()).hexdigest()
            if cachekey in previous:reports.append(previous[cachekey])
            else:todo.append(r);keys.append(cachekey)
    start=time.perf_counter()
    with ProcessPoolExecutor(max_workers=8) as pool:
        for i,r in enumerate(pool.map(audit,todo)):
            reports.append(dict(r,cache_key=keys[i]))
            if (i+1)%200==0: print('audited',i+1,'/',len(todo),flush=True)
    result=dict(solver_sha256=solver_hash,program_sha256=program_hash,unique_feasible_design_objectives=len(reports),checked_candidates=sum(r['evaluated'] for r in reports),failures=[r for r in reports if not r['stable']],reports=reports,seconds=time.perf_counter()-start)
    dump(ROOT/'local_audit.json',result); print('COMPLETE',len(reports),'failures',len(result['failures']),flush=True)
if __name__=='__main__': main()
