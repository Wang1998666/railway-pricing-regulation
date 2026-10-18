import json,collections,math
import numpy as np
from scipy.stats import spearmanr
from model import Model,ROOT,dump,VERSION

def groups(experiment): return [json.loads(p.read_text(encoding='utf-8')) for p in sorted((ROOT/'runs'/experiment).glob('*.json'))]
def record(group,policy,obj): return next(r for r in group['records'] if r['policy']==policy and r['objective']==obj)
def pair_feasible(g,p): return any(r['feasible'] for r in g['records'] if r['policy']==p)
def event(g,obj):
    a=record(g,'P3',obj); b=record(g,'P4',obj); c=json.loads((ROOT/'inputs'/f"{g['job']['case']}.json").read_text(encoding='utf-8')); cand=np.array([p['candidate'] for p in c['products']]); N=np.array(b['N']); selected=np.flatnonzero(cand&(N.sum(axis=1)>0))
    tol=1e-4*max(1,abs(a['objective_value']))
    if not b['feasible'] or len(selected)==0 or (a['feasible'] and b['objective_value']<=a['objective_value']+tol): return None
    role='improvement' if a['feasible'] else 'restoration'
    # The largest low-income shortfall is measured by OD-period, with potential
    # reference demand .85 times the scenario-specific population.
    target=np.array(c['qbar'])[:,2,:]*.85*a['spec'].get('demand',1.)
    short=target-np.array(a['Q'])[:,2,:]; w,h=np.unravel_index(short.argmax(),short.shape)
    coverage=any(c['products'][s]['serve'][w] and N[s,h]>0 for s in selected) and short[w,h]>0
    trigger=g['job']['id']; own=sum(b['rail_revenue_by_product'][s] for s in selected)
    incumbent_change=sum(b['rail_revenue_by_product'][s]-a['rail_revenue_by_product'][s] for s in range(len(c['products'])) if not cand[s])
    addedcost=sum((N[s].sum()*c['products'][s]['run_cost']+c['products'][s]['fixed_cost']*b['spec'].get('k_restart',1.))*b['spec'].get('k_cost',1.) for s in selected)
    incumbent_cost_change=b['cost']-a['cost']-addedcost
    channel='coverage' if coverage else 'affordability' if own>0 and own>=max(0,incumbent_change) else 'cost' if 'k_cost' in trigger or 'k_restart' in trigger else 'affordability'
    return dict(case_id=c['id'],objective=obj,trigger=trigger,role=role,departures=int(N[cand].sum()),patterns=[c['products'][s]['id'] for s in selected],channel=channel,own_revenue=own if role=='improvement' else None,incumbent_revenue_change=incumbent_change if role=='improvement' else None,activation_cost=addedcost if role=='improvement' else None,incumbent_cost_change=incumbent_cost_change if role=='improvement' else None,profit_change=b['profit']-a['profit'],retention_change=b['eta']-a['eta'],financial_margin_before=a['profit']+a['spec'].get('budget',500000),financial_margin_after=b['profit']+b['spec'].get('budget',500000))

def main():
    allgroups={e:groups(e) for e in ['E2','E3','E4','E5','E6','E7','E8','E9','E10']}; cases={ci:json.loads((ROOT/'inputs'/f'{ci}.json').read_text(encoding='utf-8')) for ci in ['HN','WC','JX']}
    counts={e:dict(groups=len(gs),design_records=sum(len(g['records']) for g in gs),no_floor_records=sum(len(g.get('budgets',[])) for g in gs)) for e,gs in allgroups.items()}
    ref={ci:next(g for g in allgroups['E2'] if g['job']['id']==f'{ci}_reference_none') for ci in cases}
    reference=[]
    for ci,g in ref.items():
        for obj in ['profit','welfare']:
            rs={p:record(g,p,obj) for p in ['P0','P1','P2','P3','P4']}
            reference.append(dict(case_id=ci,objective=obj,values={p:r['objective_value'] for p,r in rs.items()},joint_gain=rs['P3']['objective_value']-rs['P0']['objective_value'],joint_increment=rs['P3']['objective_value']-max(rs['P1']['objective_value'],rs['P2']['objective_value']),K_increment=rs['P4']['objective_value']-rs['P3']['objective_value'],eta=rs['P3']['eta'],maxlf=rs['P3']['maxlf'],financial_margin=rs['P3']['profit']+500000))
    feasible={ci:{p:sum(pair_feasible(g,p) for g in allgroups['E2'] if g['job']['case']==ci) for p in ['P0','P1','P2','P3','P4']} for ci in cases}
    recovery=sum(not pair_feasible(g,'P0') and pair_feasible(g,'P3') for g in allgroups['E2']); krecovery=sum(not pair_feasible(g,'P3') and pair_feasible(g,'P4') for g in allgroups['E2'])
    failures=collections.Counter(); matrix=[]
    for g in allgroups['E2']:
        r=record(g,'P0','profit'); fail=''.join([k for k,test in [('F',r['profit']< -500000-1e-6),('R',r['eta']<.95-1e-9),('C',r['maxlf']>.95+1e-9),('N',not r['structural'])] if test]); failures[fail or 'none']+=1
        sufficient=next((p for p in ['P0','P1','P2','P3','P4'] if pair_feasible(g,p)),'none')
        matrix.append(dict(case_id=g['job']['case'],income=g['job']['income'],electric=g['job']['electric'],p0_failures=fail,minimum_policy=sufficient,search_discrepancy=any(x['raw_search_difference'] for x in g['search_discrepancies'])))
    events=[e for exp in ['E2','E3'] for g in allgroups[exp] for obj in ['profit','welfare'] if (e:=event(g,obj)) is not None]
    governance=[]
    for g in allgroups['E8']:
        if not pair_feasible(g,'P4'): continue
        p=record(g,'P4','profit'); w=record(g,'P4','welfare')
        governance.append(dict(case_id=g['job']['case'],budget=14000000.,income=g['job']['income'],electric=g['job']['electric'],profit_gap=p['profit']-w['profit'],welfare_gap=w['welfare']-p['welfare'],ratio=(p['profit']-w['profit'])/(w['welfare']-p['welfare']) if w['welfare']-p['welfare']>1e-6 else None,profit_P=p['profit'],profit_W=w['profit'],surplus_P=p['U']-Model(cases[g['job']['case']],p['income'],p['electric']).state_U,surplus_W=w['U']-Model(cases[g['job']['case']],w['income'],w['electric']).state_U))
    budgets=[dict(case_id=g['job']['case'],income=g['job']['income'],electric=g['job']['electric'],**{k:v for k,v in b.items() if k!='record'}) for g in allgroups['E2'] for b in g.get('budgets',[])]
    phase=[]
    for g in allgroups['E7']:
        f3=pair_feasible(g,'P3'); f4=pair_feasible(g,'P4')
        for obj in ['profit','welfare']:
            a=record(g,'P3',obj); b=record(g,'P4',obj)
            regime='unresolved' if not f4 else 'restoration' if not f3 else 'improvement' if b['objective_value']>a['objective_value']+1e-4*max(1,abs(a['objective_value'])) else 'inactive'
            phase.append(dict(case_id=g['job']['case'],objective=obj,polarization=g['job']['spec']['polarization_scale'],electric=g['job']['spec']['electric_scale'],regime=regime,gain=b['objective_value']-a['objective_value'] if f3 and f4 else None))
    robustness=[]
    for g in allgroups['E5']:
        for r in g['records']:
            base=record(ref[g['job']['case']],'P3',r['objective']); dev=100*(r['objective_value']-base['objective_value'])/abs(base['objective_value']) if abs(base['objective_value'])>1e-6 else None
            robustness.append(dict(case_id=r['case_id'],objective=r['objective'],test=g['job']['id'].split('_',1)[1],feasible=r['feasible'],deviation_percent=dev,absolute_deviation=r['objective_value']-base['objective_value']))
    equity=[]; baselines={}
    for exp,gs in allgroups.items():
        for g in gs:
            for r in g['records']:
                key=json.dumps([r['case_id'],r['income'],r['electric'],r['spec']],sort_keys=True)
                if key not in baselines:
                    m=Model(cases[r['case_id']],r['income'],r['electric'],r['spec']); baselines[key]=m.record(m.N0,np.ones((m.S,4,3)),'profit','P0')
                base=baselines[key]; equity.append(dict(case_id=r['case_id'],job_id=g['job']['id'],experiment=exp,policy=r['policy'],objective=r['objective'],income=r['income'],feasible=r['feasible'],dG=r['Gmax']-base['Gmax'],dGmean=r['Gmean']-base['Gmean'],deta=r['eta']-base['eta'],exit_change=float(np.array(r['q0'])[:,2,:].sum()-np.array(base['q0'])[:,2,:].sum()),rail_L_change=r['rail_by_class'][2]-base['rail_by_class'][2]))
    def eqstats(rows):
        x=np.array([r['dG'] for r in rows]); y=np.array([r['deta'] for r in rows]); mask=(x < -1e-9)&(y < -1e-9); corr=spearmanr(x,y).statistic
        return dict(n=len(rows),divergence_n=int(mask.sum()),divergence_share=float(mask.mean()),spearman=float(corr),example=next((rows[i] for i in np.flatnonzero(mask)),None))
    stats=dict(all_saved=eqstats(equity),feasible_only=eqstats([r for r in equity if r['feasible']]))
    out=dict(counts=counts,reference=reference,feasibility=feasible,p3_recoveries=recovery,k_recoveries=krecovery,p0_failure_counts=dict(failures),matrix=matrix,events=events,governance=governance,budgets=budgets,phase=phase,robustness=robustness,equity_stats=stats,search_discrepancies=sum(x['search_discrepancy'] for x in matrix),seconds_sum=sum(g['seconds'] for gs in allgroups.values() for g in gs),version=VERSION)
    dump(ROOT/'analysis.json',out); dump(ROOT/'equity_designs.json',equity)
    print(json.dumps({k:out[k] for k in ['counts','reference','feasibility','p0_failure_counts','p3_recoveries','k_recoveries','equity_stats','search_discrepancies']},ensure_ascii=False,indent=2))

if __name__=='__main__': main()
