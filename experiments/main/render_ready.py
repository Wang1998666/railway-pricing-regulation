"""Early visual QA using the already complete E2/E3/E6 outputs."""
import json
from model import ROOT
from analyze import groups,record,pair_feasible
import review_figures as rf
C={ci:json.loads((ROOT/'inputs'/f'{ci}.json').read_text(encoding='utf-8')) for ci in rf.CIS};REF={ci:next(g for g in groups('E2') if g['job']['id']==ci+'_reference_none') for ci in rf.CIS};A={'reference':[],'governance':[]}
for ci,g in REF.items():
    for obj in rf.OBJS:
        z={p:record(g,p,obj)['objective_value'] for p in ['P0','P1','P2','P3','P4']};A['reference'].append(dict(case_id=ci,objective=obj,values=z,factorial=z['P3']-z['P1']-z['P2']+z['P0']))
for g in groups('E2'):
    if g['job']['spec'].get('road_contrast') or not pair_feasible(g,'P4'):continue
    p=record(g,'P4','profit');w=record(g,'P4','welfare');A['governance'].append(dict(case_id=g['job']['case'],income=g['job']['income'],intensity=g['job']['spec']['electric_scale'],profit_gap=p['profit']-w['profit'],welfare_gap=w['welfare']-p['welfare'],continuous=True))
rf.load=lambda:(A,C,REF);rf.old.load=rf.load;rf.rev.load=rf.load
for n in [4,6,7,8,9,11,14]:
    if n==7:rf.rev.figure07()
    elif n==8:rf.old.figure08()
    else:getattr(rf,f'figure{n:02d}')()
rf.polarization_plot();print('Ready figures rendered')
