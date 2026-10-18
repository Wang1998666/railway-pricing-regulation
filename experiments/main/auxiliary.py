"""E1 partial reoptimizations, E3 confirmation, independent local audit."""
import json,itertools,time,copy
import numpy as np
from model import ROOT,Model,dump,solve
from analyze import groups,record,event

def main():
    cases={ci:json.loads((ROOT/'inputs'/f'{ci}.json').read_text(encoding='utf-8')) for ci in ['HN','WC','JX']}; partial=[]; confirmed=[]
    for g in groups('E2'):
        if g['job']['income']!='reference' or g['job']['electric']!='none': continue
        m=Model(cases[g['job']['case']])
        for obj in ['profit','welfare']:
            p3=record(g,'P3',obj)
            mf=Model(cases[g['job']['case']]); mf.Nmin=np.array(p3['N']); mf.Nmax=np.array(p3['N']); f=solve(mf,obj,'P3',seeds=[p3],rounds=8)
            mp=Model(cases[g['job']['case']]); original_evaluate=mp.evaluate; locked=np.where(np.array(p3['N'])[:,:,None]>0,np.array(p3['phi']),1.)
            def locked_evaluate(N,ph,details=False,baseline=False,engine=mp,original=original_evaluate,lock=locked):
                values=original(N,ph,details,baseline); nn=np.asarray(N); pp=np.asarray(ph)
                if nn.ndim==2: nn=nn[None]
                if pp.ndim==3: pp=pp[None]
                bad=np.any((np.abs(pp-lock[None])>1e-8)&(nn[:,:,:,None]>0),axis=(1,2,3)); values['feasible']&=~bad; values['structural']&=~bad; values['violation']+=bad*100
                return values
            mp.evaluate=locked_evaluate
            phi=solve(mp,obj,'P3',seeds=[p3],rounds=8)
            partial.append(dict(case_id=g['job']['case'],objective=obj,P3F=f,P3phi=phi,own_effect=max(f['objective_value'],phi['objective_value'])-max(record(g,'P1',obj)['objective_value'],record(g,'P2',obj)['objective_value']),interaction=record(g,'P3',obj)['objective_value']-max(f['objective_value'],phi['objective_value'])))
    dump(ROOT/'E1_partial.json',partial)
    for g in groups('E3'):
        for obj in ['profit','welfare']:
            e=event(g,obj)
            if e is None: continue
            r=record(g,'P3',obj); p=record(g,'P4',obj); m=Model(cases[g['job']['case']],r['income'],r['electric'],r['spec']); a=solve(m,obj,'P3',seeds=[r],rounds=8); b=solve(m,obj,'P4',seeds=[a,p],rounds=8)
            confirmed.append(dict(trigger=e['trigger'],objective=obj,P3=a,P4=b,confirmed=b['feasible'] and (not a['feasible'] or b['objective_value']>a['objective_value']+1e-4*max(1,abs(a['objective_value'])))))
    dump(ROOT/'E3_confirmations.json',confirmed)
    # Reconstruct the prescribed disjoint period/product adjacent-pair blocks.
    reports=[]; seen={}
    for exp in ['E2','E3','E4','E5','E6','E7','E8','E9','E10']:
        for g in groups(exp):
            for r in g['records']:
                if r['policy'] not in ['P3','P4'] or not r['feasible']: continue
                signature=json.dumps([r['case_id'],r['income'],r['electric'],r['spec'],r['policy'],r['objective'],r['N'],r['phi']],sort_keys=True)
                if signature in seen: continue
                seen[signature]=True; m=Model(cases[r['case_id']],r['income'],r['electric'],r['spec']); N=np.array(r['N']); phi=np.array(r['phi']); phi[m.tier=='K']=1.; step=r['spec'].get('step',.05); obj=r['objective']; base=m.evaluate(N,phi)[obj][0]
                phi=np.where(N[:,:,None]>0,phi,1.); phi[m.tier=='K']=1.
                nc=[(s,h) for s in range(m.S) if m.adjustable[s] or (r['policy']=='P4' and m.candidate[s]) for h in range(4)]
                fc=[(s,h,0) for s in range(m.S) if m.adjustable[s] for h in range(4) if m.Nmax[s,h]>0]
                blocks=[]
                for family,coords in [('N',nc),('F',fc)]:
                    for axis in [0,1]:
                        for val in sorted({x[axis] for x in coords}):
                            subset=[x for x in coords if x[axis]==val]
                            blocks.extend((family,subset[i:i+2]) for i in range(0,len(subset),2))
                bestgain=0.; evaluated=0
                for family,coords in blocks:
                    alternatives=[]
                    for x in coords:
                        current=N[x] if family=='N' else phi[x]
                        if family=='N': vals=sorted(set([max(m.Nmin[x],current-1),current,min(m.Nmax[x],current+1)]))
                        else: vals=[v for v in [round(current-step,8),current,round(current+step,8)] if .8-1e-9<=v<=1.2+1e-9]
                        alternatives.append(vals)
                    combos=list(itertools.product(*alternatives)); nb=np.broadcast_to(N,(len(combos),*N.shape)).copy(); pb=np.broadcast_to(phi,(len(combos),*phi.shape)).copy()
                    for j,x in enumerate(coords):
                        for i,combo in enumerate(combos):
                            if family=='N': nb[(i,*x)]=combo[j]
                            else: pb[i,x[0],x[1],:]=combo[j]
                    rr=m.evaluate(nb,pb); evaluated+=len(combos)
                    if rr['feasible'].any(): bestgain=max(bestgain,float(max(rr[obj][rr['feasible']])-base))
                reports.append(dict(case_id=r['case_id'],experiment=exp,policy=r['policy'],objective=obj,evaluated=evaluated,best_gain=bestgain,stable=bestgain<=1e-5))
    dump(ROOT/'local_audit.json',dict(unique_feasible_design_objectives=len(reports),checked_candidates=sum(x['evaluated'] for x in reports),failures=[r for r in reports if not r['stable']],reports=reports))
    print('partials',len(partial),'confirmed',len(confirmed),all(x['confirmed'] for x in confirmed),'local',len(reports),'failures',sum(not x['stable'] for x in reports),flush=True)

if __name__=='__main__': main()
