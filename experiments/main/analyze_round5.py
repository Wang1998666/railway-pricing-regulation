"""One consistent result set for profiles, cap/floor tradeoffs and scope."""
import json,csv
import numpy as np
from model import ROOT,Model,dump
from run_round5 import engine
from analyze import groups,record
def operations(m,r):
    n=np.array(r['N']);p=np.array(r['phi'])[:,:,0];active=(n>0)&m.adjustable[:,None];cap=active&np.isclose(p,m.fare_cap)
    return dict(fare=float((n[m.adjustable]*p[m.adjustable]).sum()/n[m.adjustable].sum()),tier_departures=[int(n[m.tier==t].sum()) for t in ['G','D','K']],total_departures=int(n.sum()),cap_cells=int(cap.sum()),active_cells=int(active.sum()),cap_departure_fraction=float(n[cap].sum()/n[active].sum()))
def main():
    refs={c:next(g for g in groups('E2') if g['job']['id']==c+'_reference_none') for c in ['HN','WC','JX']};profiles=[];strict=[];tradeoffs=[]
    for g in groups('E16'):
        m=engine(g['job']);p=record(g,'P3','profit');b=record(g,'P0','profit');profiles.append(dict(case_id=m.c['id'],anchor=g['job']['anchor'],cap=g['job']['cap'],profit_gain=p['profit']-b['profit'],U_change=p['consumer_surplus_change'],W_change=p['welfare'],certificate=p['meta'].get('certificate',False),**operations(m,p)))
    for ci,g in refs.items():
        m=engine(g['job']);p=record(g,'P3','profit');b=record(g,'P0','profit');w=record(g,'P3','welfare');sg=next(x for x in groups('E9') if x['job']['case']==ci and abs(x['job']['spec']['eta']-1)<1e-10);s=record(sg,'P3','profit');z=dict(case_id=ci,commercial_fare=operations(m,p)['fare'],strict_fare=operations(m,s)['fare'],traveler_surplus_recovery=(s['U']-p['U'])/(b['U']-p['U']),profit_gain=s['profit']-b['profit'],welfare_gain=s['welfare'],benchmark_fraction=s['welfare']/w['welfare'],profit_retained=(s['profit']-b['profit'])/(p['profit']-b['profit']),certificate=s['meta'].get('certificate',False));strict.append(z)
        tight=next(x for x in profiles if x['case_id']==ci and x['anchor']==.8 and x['cap']==1.1)
        for label,r,model in [('Central cap 1.20',p,m),('Tighter cap 1.10',record(next(x for x in groups('E16') if x['job']['case']==ci and x['job']['anchor']==.8 and x['job']['cap']==1.1),'P3','profit'),m),('Strict floor 1.00',s,m)]:
            tradeoffs.append(dict(case_id=ci,lever=label,profit_gain=r['profit']-b['profit'],profit_retained=(r['profit']-b['profit'])/(p['profit']-b['profit']),U_change=r['U']-b['U'],W_change=r['welfare'],welfare_loss_reduction=1-r['welfare']/p['welfare'],fare=operations(model,r)['fare'],certificate=r['meta'].get('certificate',False)))
    states=[json.loads(p.read_text(encoding='utf-8')) for p in (ROOT/'states').glob('*.json')];certs=[]
    for g in states:
        for c in g['certificates']:
            r=next(r for r in g['records'] if r['policy']==c['policy'] and r['objective']==c['objective']);upper=c['upper']
            # COPT's finite infinity sentinel is not an available objective bound.
            if upper is not None and (not np.isfinite(upper) or abs(upper)>=1e25):upper=None
            certs.append(dict(state=g['key'],case_id=g['job']['case'],**{**c,'upper':upper},bound_status='finite' if upper is not None else 'unavailable',feasible=r['feasible'],value=r[c['objective']],remaining_gap=None if upper is None else upper-r[c['objective']]))
    unresolved=[c for c in certs if not c['certificate'] and not c['infeasible']]
    out=dict(profiles=profiles,strict=strict,tradeoffs=tradeoffs,certificates=certs,certificate_count=sum(c['certificate'] for c in certs),infeasibility_count=sum(c['infeasible'] for c in certs),unresolved_certification=unresolved,states=len(states));dump(ROOT/'round5_analysis.json',out)
    for name,rows in [('commercial_profile',profiles),('cap_floor_tradeoff',tradeoffs),('certification_scope',certs)]:
        with (ROOT/(name+'.csv')).open('w',encoding='utf-8',newline='') as fh:
            wr=csv.DictWriter(fh,fieldnames=rows[0].keys());wr.writeheader();wr.writerows(rows)
    print('certificates',out['certificate_count'],'infeasible',out['infeasibility_count'],'unresolved',len(unresolved));print('strict',strict)
if __name__=='__main__':main()
