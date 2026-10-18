"""Purpose-based reporting, factorial attribution, unique equity designs."""
import json,hashlib,collections
import numpy as np
from model import ROOT,Model,dump
from analyze import groups,record,pair_feasible

def main():
    C={c:json.loads((ROOT/'inputs'/f'{c}.json').read_text(encoding='utf-8')) for c in ['HN','WC','JX']}
    G={e:groups(e) for e in ['E2','E3','E4','E5','E6','E7','E8','E9','E10','E11','E12']}
    cp=ROOT/'constant_cost_grid.json'
    if cp.exists(): G['E5C']=json.loads(cp.read_text(encoding='utf-8'))['groups']
    refs={c:next(g for g in G['E2'] if g['job']['id']==c+'_reference_none') for c in C}; R=[]
    for ci,g in refs.items():
        for obj in ['profit','welfare']:
            z={p:record(g,p,obj)['objective_value'] for p in ['P0','P1','P2','P3','P4']}
            interaction=z['P3']-z['P1']-z['P2']+z['P0']; fare=.5*((z['P1']-z['P0'])+(z['P3']-z['P2'])); freq=.5*((z['P2']-z['P0'])+(z['P3']-z['P1']))
            R.append(dict(case_id=ci,objective=obj,values=z,joint_gain=z['P3']-z['P0'],joint_increment=z['P3']-max(z['P1'],z['P2']),factorial=interaction,fare_shapley=fare,frequency_shapley=freq,K_increment=z['P4']-z['P3']))
    stress=[]; budgets=[]; gov=[]; events=[]; eq={}; robust=[]; head=[]; network=[]; peaks=[]
    for g in G['E2']:
        j=g['job']; continuous=not j['spec'].get('road_contrast',False)
        stress.append(dict(case_id=j['case'],id=j['id'],income=j['income'],electric=j['electric'],intensity=j['spec'].get('electric_scale',0),continuous=continuous,feasible={p:pair_feasible(g,p) for p in ['P0','P1','P2','P3','P4']}))
        for b in g.get('budgets',[]): budgets.append(dict(case_id=j['case'],id=j['id'],income=j['income'],intensity=j['spec'].get('electric_scale',0),continuous=continuous,**b))
        if pair_feasible(g,'P4'):
            p=record(g,'P4','profit'); w=record(g,'P4','welfare')
            gov.append(dict(case_id=j['case'],id=j['id'],income=j['income'],electric=j['electric'],intensity=j['spec'].get('electric_scale',0),continuous=continuous,profit_gap=max(0.,p['profit']-w['profit']),welfare_gap=max(0.,w['welfare']-p['welfare']),CS_gap=w['U']-p['U']))
        if j['electric']=='none' and j['income']!='reference':
            p=record(g,'P0','profit'); ss,h,b,e=p['peak_load_index']; prod=C[j['case']]['products'][ss]
            peaks.append(dict(case_id=j['case'],income=j['income'],maxlf=p['maxlf'],product=prod['id'],seat=b,period=h,segment=e))
    for exp in ['E3','E10']:
        for g in G[exp]:
            for obj in ['profit','welfare']:
                p=record(g,'P3',obj); r=record(g,'P4',obj); ci=g['job']['case']; cand=np.array([x['candidate'] for x in C[ci]['products']]); N=np.array(r['N']); gain=r['objective_value']-p['objective_value']
                if r['feasible'] and (not p['feasible'] or gain>1e-4*max(1,abs(p['objective_value']))) and N[cand].sum()>0:
                    m=Model(C[ci],r['income'],r['electric'],r['spec']); Kcost=float((N[cand]*m.run_cost[cand,None]).sum()+np.sum((N[cand].sum(axis=1)>0)*m.fixed_cost[cand]))
                    events.append(dict(case_id=ci,experiment=exp,objective=obj,trigger=g['job']['id'],spec=r['spec'],role='gain' if p['feasible'] else 'recovery',departures=int(N[cand].sum()),patterns=[C[ci]['products'][s]['id'] for s in np.flatnonzero(cand&(N.sum(axis=1)>0))],gain=gain if p['feasible'] else None,profit_change=r['profit']-p['profit'],welfare_change=r['welfare']-p['welfare'],CS_change=r['U']-p['U'],revenue_change=r['revenue']-p['revenue'],cost_change=r['cost']-p['cost'],activation_cost=Kcost,incumbent_cost_change=r['cost']-p['cost']-Kcost))
    # Count physical decisions once for a common behavioral calibration and state.
    base_cache={}
    for exp,gg in G.items():
        for g in gg:
            for r in g['records']:
                spec=r['spec']; ci=r['case_id']; statekey=json.dumps([ci,r['income'],r['electric'],spec],sort_keys=True)
                if statekey not in base_cache:
                    m=Model(C[ci],r['income'],r['electric'],spec); p0=m.record(m.N0,np.ones((m.S,4,3)),'profit','P0'); ref=Model(C[ci],'reference','none',spec)
                    arr=np.concatenate([x.ravel() for x in [m.beta,m.qbar,m.fixed_rail,m.roadU,m.fare,np.array([m.mu_sc,m.mu_pr])]])
                    behavior=hashlib.sha256(arr.tobytes()).hexdigest()
                    base_cache[statekey]=(p0['Gmax'],p0['class_trips'][2],ref.ref_vul,behavior,p0['Gmean'])
                baseG,baseL,denom,behavior,baseMean=base_cache[statekey]
                dG=r['Gmax']-baseG; loss=baseL-r['class_trips'][2]; deta=-loss/denom
                physical_N=np.rint(np.array(r['N'])).astype(int)
                for s,p in enumerate(C[ci]['products']):
                    if p['candidate']:
                        parent=next(i for i,x in enumerate(C[ci]['products']) if x['id']==p['parent']);physical_N[parent]+=physical_N[s];physical_N[s]=0
                keyN=physical_N.tolist(); seatmask=np.array([p['seats'] for p in C[ci]['products']])[:,None,:]>0
                keyph=np.where(seatmask,np.round(np.array(r['phi']),8),0.)
                keyph[[p['candidate'] for p in C[ci]['products']]]=0
                keyphi=keyph.tolist()
                signature=json.dumps([ci,behavior,keyN,keyphi],sort_keys=True)
                observedK=np.array([p['tier']=='K' and not p['candidate'] for p in C[ci]['products']]); N0=np.array([p['N0'] for p in C[ci]['products']]); removed=int(np.maximum(N0[observedK]-physical_N[observedK],0).sum())
                if signature not in eq: eq[signature]=dict(case_id=ci,id=g['job']['id'],experiment=exp,income=r['income'],electric=r['electric'],dG=dG,dGmean=r['Gmean']-baseMean,deta=deta,exit_change=loss,feasible=r['feasible'],policies=[r['policy']],objectives=[r['objective']],k_withdraw=spec.get('k_withdraw',0.),observed_K_removed=removed,eta=r['eta'],Gmax=r['Gmax'],N=keyN,phi=keyphi,spec=spec)
                else:
                    x=eq[signature]
                    if r['feasible'] and not x['feasible']: x.update(id=g['job']['id'],experiment=exp,spec=spec,eta=r['eta'])
                    x['feasible']|=r['feasible']; x['policies']=sorted(set(x['policies']+[r['policy']])); x['objectives']=sorted(set(x['objectives']+[r['objective']])); x['k_withdraw']=max(x['k_withdraw'],spec.get('k_withdraw',0.))
                if exp in ['E5','E5C']:
                    base=record(refs[ci],'P3',r['objective']);
                    if r['policy']=='P3':
                        v=dict(case_id=ci,id=g['job']['id'],test=g['job']['id'][len(ci)+1:],objective=r['objective'],feasible=r['feasible'],profit=r['profit'],welfare=r['welfare'],gain=r['objective_value']-record(g,'P0',r['objective'])['objective_value'],signed_deviation=r['objective_value']-base['objective_value'],spec=spec,N=r['N'],eta=r['eta'],maxlf=r['maxlf'])
                        (head if 'ref_load' in spec else robust).append(v)
                if exp=='E8' and r['policy']=='P3': network.append(dict(case_id=ci,id=g['job']['id'],objective=r['objective'],spec=spec,feasible=r['feasible'],gain=r['objective_value']-record(g,'P0',r['objective'])['objective_value'],profit=r['profit'],eta=r['eta'],maxlf=r['maxlf']))
    equity=list(eq.values()); good=[x for x in equity if x['feasible']]; diverge=[x for x in good if x['dG']<-1e-7 and x['deta']<-1e-7]; ex=max(diverge,key=lambda x:x['exit_change']) if diverge else None
    strict=[]
    for ci in C:
        g=next(g for g in G['E9'] if g['job']['case']==ci and abs(g['job']['spec']['eta']-1.)<1e-10)
        for obj in ['profit','welfare']:
            r=record(g,'P3',obj); base=record(refs[ci],'P3',obj); sacrifice=base['objective_value']-r['objective_value']
            strict.append(dict(case_id=ci,objective=obj,feasible=r['feasible'],sacrifice=sacrifice,share=sacrifice/(base['objective_value']-record(refs[ci],'P0',obj)['objective_value'])))
    event_counts=collections.Counter(('_'.join(e['trigger'].split('_')[1:3]) if e['trigger'].split('_')[1]=='k' else e['trigger'].split('_')[1]) for e in events if e['experiment']=='E3')
    stats=dict(unique_all=len(equity),unique_feasible=len(good),divergent=len(diverge),mean_divergent=sum(x['dGmean']<-1e-7 and x['deta']<-1e-7 for x in good),share=len(diverge)/max(1,len(good)),example=ex)
    co_rescaled=[r for r in head if 'constant_cost_anchor' not in r['spec']]; fixed_cost=[r for r in head if 'constant_cost_anchor' in r['spec']]
    A=dict(counts={e:dict(groups=len(gg),records=sum(len(g['records']) for g in gg),budgets=sum(len(g.get('budgets',[])) for g in gg)) for e,gg in G.items()},reference=R,stress=stress,budgets=budgets,governance=gov,events=events,event_counts=dict(event_counts),robustness=robust,headroom=fixed_cost or head,headroom_rescaled=co_rescaled,network=network,peak_loads=peaks,strict_retention=strict,equity_stats=stats,path_max=max(r['path_utilization'] for g in G['E2'] for r in g['records'] if r['feasible']),fleet_max=np.max([r['fleet_utilization'] for g in G['E2'] for r in g['records'] if r['feasible']],axis=0).tolist())
    dump(ROOT/'review_analysis.json',A); dump(ROOT/'equity_unique.json',equity)
    print(json.dumps({k:A[k] for k in ['counts','reference','event_counts','strict_retention','path_max','fleet_max']},indent=2))

if __name__=='__main__': main()
