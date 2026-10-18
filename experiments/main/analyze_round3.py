"""Accounting channels, constrained-domain checks and promoted evidence."""
import json,itertools,math
import numpy as np
from scipy.special import logsumexp
from scipy.optimize import milp,Bounds,LinearConstraint
from model import ROOT,Model,dump
from analyze import groups,record,pair_feasible
from verify import scalar

def effective(m,n):
    a=n.copy()
    for s,p in m.parent.items():a[p]+=n[s];a[s]=0
    return a
def channels(m,p,r):
    n0=effective(m,np.array(p['N']));n1=effective(m,np.array(r['N']));ph0=np.where(n0[:,:,None]>0,np.array(p['phi']),1.);ph1=np.where(n1[:,:,None]>0,np.array(r['phi']),1.)
    d0=15*np.array([3,8,3,10])[:,None]/np.maximum(n0.T,1);d1=15*np.array([3,8,3,10])[:,None]/np.maximum(n1.T,1)
    if m.displacement_cap is not None:d0=np.minimum(d0,m.displacement_cap);d1=np.minimum(d1,m.displacement_cap)
    a0=n0.T>0;a1=n1.T>0;both=a0&a1;vals={}
    for mask in range(8):
        ph=ph1 if mask&1 else ph0;sc=np.where(both,d1 if mask&2 else d0,np.where(a0,d0,d1));active=a1 if mask&4 else a0
        fare=m.fare[:,None,None,:,:]*ph.transpose(1,0,2)[None,None]
        v=m.fixed_rail-m.beta[None,:,None,0,None,None]*fare-m.beta[None,:,None,4,None,None]*sc[None,None,:,:,None]
        valid=active[None,None,:,:,None]&m.serve.T[:,None,None,:,None]&(m.seats[None,None,None,:,:]>0)
        v=np.where(valid,v,-1e100);seats=logsumexp(v/m.mu_sc,axis=-1)*m.mu_sc;rail=logsumexp(seats/m.mu_pr,axis=-1)*m.mu_pr
        vals[mask]=logsumexp(np.concatenate([rail[...,None],m.road_logs],axis=-1)/.75,axis=-1)*.75
    weight=np.array(p['Q'])/m.beta[None,:,None,0];out=[]
    for i in range(3):
        total=0.
        for order in itertools.permutations(range(3)):
            mask=0
            for j in order:
                if j==i:total+=float((weight*(vals[mask|1<<i]-vals[mask])).sum())/6
                mask|=1<<j
        out.append(total)
    u0=float((m.qbar*np.logaddexp(0,vals[0])/m.beta[None,:,None,0]).sum());u1=float((m.qbar*np.logaddexp(0,vals[7])/m.beta[None,:,None,0]).sum());assert abs(u0-p['U'])<1e-5 and abs(u1-r['U'])<1e-5
    return dict(fare=out[0],schedule=out[1],availability=out[2],participation=r['U']-p['U']-sum(out),total=r['U']-p['U'])

def main():
    C={ci:json.loads((ROOT/'inputs'/f'{ci}.json').read_text(encoding='utf-8')) for ci in ['HN','WC','JX']};refs={ci:next(g for g in groups('E2') if g['job']['id']==ci+'_reference_none') for ci in C};entry=[];floors=[];broad=[];fleet=[];checks=[]
    for ci in C:
        m=Model(C[ci]);g=refs[ci]
        for obj in ['profit','welfare']:
            p=record(g,'P3',obj);r=record(g,'P4',obj);N=np.array(r['N']);sn=effective(m,N);det=m.evaluate(N,np.array(r['phi']),True);qr=det['qr'][0];fa=m.fare[:,None,None,:,:]*np.array(r['phi']).transpose(1,0,2)[None,None];rh=(qr*fa).sum(axis=(0,1,4)).T
            addedrev=sum(float((rh[parent]*np.divide(N[s],sn[parent],out=np.zeros(4),where=sn[parent]>0)).sum()) for s,parent in m.parent.items());newcost=float((N[m.candidate]*m.run_cost[m.candidate,None]).sum()+((N[m.candidate].sum(axis=1)>0)*m.fixed_cost[m.candidate]).sum());inc_rev=r['revenue']-addedrev-p['revenue'];inc_save=p['cost']-(r['cost']-newcost);dp=r['profit']-p['profit'];assert abs(addedrev+inc_rev+inc_save-newcost-dp)<1e-5
            nc=np.array(p['N']);nc[m.candidate]=N[m.candidate];ph=np.array(p['phi']);ph[m.tier=='K']=1.;cf=m.record(nc,ph,obj,'P4');a=scalar(m.c,nc,np.array(cf['phi']),'reference','none',{});assert abs(a['profit']-cf['profit'])<1e-5
            entry.append(dict(case_id=ci,objective=obj,departures=int(N[m.candidate].sum()),new_revenue_allocation=addedrev,incumbent_revenue=inc_rev,incumbent_cost_saving=inc_save,new_cost=newcost,profit_change=dp,U_change=r['U']-p['U'],welfare_change=r['welfare']-p['welfare'],U_channels=channels(m,p,r),fixed_GD_profit=cf['profit']-p['profit'],fixed_GD_welfare=cf['welfare']-p['welfare'],fixed_GD_feasible=cf['feasible']))
        strict=next(g for g in groups('E9') if g['job']['case']==ci and abs(g['job']['spec']['eta']-1)<1e-10);p=record(refs[ci],'P3','profit');r=record(strict,'P3','profit');restored=r['class_trips'][2]-p['class_trips'][2];raw=m.evaluate(m.N0,np.ones((m.S,4,3)),True);q=raw['qr'][0,:,2];fare=float((q*m.fare[:,None,:,:]).sum()/q.sum());delta=r['profit']-p['profit'];du=r['U']-p['U'];dw=r['welfare']-p['welfare'];assert abs(delta+du-dw)<1e-5
        floors.append(dict(case_id=ci,profit_change=delta,U_change=du,welfare_change=dw,restored=restored,required=m.ref_vul-p['class_trips'][2],operator_cost_per_trip=-delta/restored,L_fare=fare,net_departures=float(np.array(r['N']).sum()-np.array(p['N']).sum())))
        for t in ['G','D','K']:
            z=m.tier==t;used=float((m.N0[z]*m.cycle[z,None]).sum());upper=int(np.floor(m.fleet[['G','D','K'].index(t)]/m.cycle[z][0]+1e-8)) if ci!='JX' else None;fleet.append(dict(case_id=ci,tier=t,used=used,envelope=float(m.fleet[['G','D','K'].index(t)]),utilization=used/m.fleet[['G','D','K'].index(t)],single_family_fleet_count_upper=upper,reference_departures=int(m.N0[z].sum())))
    for exp in ['E13','E14','E15']:
        for g in groups(exp):
            m=Model(C[g['job']['case']],spec=g['job']['spec']);z=m.evaluate(m.N0,np.ones((m.S,4,3)),True);checks.append(dict(id=g['job']['id'],flow_error=float(np.max(abs(z['qr'][0]-np.array(m.c['target_rail'])))),load=float(z['maxlf'][0])))
    for g in groups('E7'):
        j=g['job'];m=Model(C[j['case']],j['income'],j['electric'],j['spec']);p=m.record(m.N0,np.ones((m.S,4,3)),'profit','P0');broad.append(dict(case_id=j['case'],income_scale=j['spec']['polarization_scale'],road_scale=j['spec']['electric_scale'],P0_feasible=p['feasible'],P3_feasible=pair_feasible(g,'P3'),P4_feasible=pair_feasible(g,'P4'),capacity_violation=p['maxlf']>m.lam+1e-9,retention_violation=p['eta']<m.eta_floor-1e-9,finance_violation=p['profit']<-m.budget-1e-6,maxlf=p['maxlf'],eta=p['eta'],profit=p['profit']))
    eq=json.loads((ROOT/'equity_unique.json').read_text(encoding='utf-8'));good=[r for r in eq if r['feasible']];div=[r for r in good if r['dG']<-1e-7 and r['deta']<-1e-7];examples=[max([r for r in div if r['case_id']==ci],key=lambda r:r['exit_change']) for ci in C if any(r['case_id']==ci for r in div)]
    assert all(r['flow_error']<1e-6 and abs(r['load']-.88)<1e-8 for r in checks)
    dump(ROOT/'round3_analysis.json',dict(entry=entry,floors=floors,broad=broad,fleet_reference=fleet,calibration_checks=checks,equity=dict(feasible=len(good),divergent=len(div),share=len(div)/len(good),examples=examples)))
    print('accounting/calibration passed',len(checks),'new calibrations; entries',[(r['case_id'],r['objective'],r['U_channels']) for r in entry if r['departures']])
if __name__=='__main__':main()
