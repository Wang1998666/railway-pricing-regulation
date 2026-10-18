"""Exact full HN P1 via period separability and certified slack global floors."""
import itertools,json
import numpy as np
from model import ROOT,Model,dump

def main():
    c=json.loads((ROOT/'inputs'/'HN.json').read_text(encoding='utf-8')); m=Model(c); grid=np.arange(.8,1.201,.05); one=np.ones((m.S,4,3)); sections=[]; minL=[]; minRev=[]; candidates=0
    for h in range(4):
        sids=[s for s in range(m.S) if m.adjustable[s] and m.N0[s,h]>0]; combos=list(itertools.product(grid,repeat=len(sids))); phi=np.broadcast_to(one,(len(combos),*one.shape)).copy()
        for i,combo in enumerate(combos):
            for s,v in zip(sids,combo): phi[i,s,h,:]=v
        out=m.evaluate(m.N0,phi,True); admissible=out['structural']&(out['maxlf']<=m.lam+1e-9); ids=np.flatnonzero(admissible); candidates+=len(combos)
        assert len(ids)>0
        fare=m.fare[None,:,None,None,:,:]*phi.transpose(0,2,1,3)[:,None,None,:,:,:]
        revenue=(out['qr'][:,:,:,h,:,:]*fare[:,:,:,h,:,:]).sum(axis=(1,2,3,4))
        utility=(m.qbar[None,:,:,h]*(-np.log1p(-out['participation'][:,:,:,h]))/m.beta[None,None,:,0]).sum(axis=(1,2))
        vulnerable=out['Q'][:,:,2,h].sum(axis=1); minL.append(float(min(vulnerable[ids]))); minRev.append(float(min(revenue[ids])))
        sections.append(dict(h=h,sids=sids,combos=combos,profit_index=int(ids[np.argmax(revenue[ids])]),welfare_index=int(ids[np.argmax(revenue[ids]+utility[ids])]),admissible=len(ids)))
    cost=float(m.evaluate(m.N0,one)['cost'][0]); worst_eta=sum(minL)/m.ref_vul; worst_profit=sum(minRev)-cost
    certified=bool(worst_eta>=m.eta_floor-1e-9 and worst_profit>=-m.budget-1e-6)
    result=dict(case_id='HN',policy='P1',local_combinations_evaluated=candidates,logical_joint_combinations=int(np.prod([len(x['combos']) for x in sections])),worst_admissible_retention=worst_eta,worst_admissible_profit=worst_profit,budget=m.budget,global_floors_slack_for_every_capacity_admissible_combination=certified,records=[])
    if certified:
        base=json.loads((ROOT/'runs'/'E2'/'HN_reference_none.json').read_text(encoding='utf-8'))
        for objective in ['profit','welfare']:
            ph=one.copy()
            for sec in sections:
                combo=sec['combos'][sec[objective+'_index']]
                for s,v in zip(sec['sids'],combo): ph[s,sec['h'],:]=v
            r=m.record(m.N0,ph,objective,'P1',dict(exact_period_certificate=True)); old=next(x for x in base['records'] if x['policy']=='P1' and x['objective']==objective)
            assert r['feasible']
            result['records'].append(dict(objective=objective,exact_value=r['objective_value'],heuristic_value=old['objective_value'],gap=r['objective_value']-old['objective_value'],record=r))
        from verify import scalar
        raw=scalar(m.c,m.N0,one,'reference','none',{}); errors=[]
        for x in result['records']:
            actual=scalar(m.c,m.N0,np.array(x['record']['phi']),'reference','none',{}); value=actual['profit'] if x['objective']=='profit' else actual['U']-raw['U']+actual['profit']-raw['profit']; error=abs(value-x['exact_value']); assert error<1e-6; errors.append(error)
        result['independent_scalar_errors']=errors
    dump(ROOT/'exact_fare_benchmark.json',result)
    print(json.dumps({k:v for k,v in result.items() if k!='records'},indent=2)); print('gaps',[(r['objective'],r['gap']) for r in result['records']])
if __name__=='__main__': main()
