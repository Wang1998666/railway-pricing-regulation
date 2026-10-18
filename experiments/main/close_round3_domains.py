"""Close saved feasible witnesses over nested fare caps/fleet/entry domains."""
import json,hashlib
import numpy as np
from model import ROOT,Model,solve,dump
def main():
    raw={ci:json.loads((ROOT/'inputs'/f'{ci}.json').read_text(encoding='utf-8')) for ci in ['HN','WC','JX']};changed=[]
    extras=[p for exp in ['E13','E14','E15'] for p in (ROOT/'runs'/exp).glob('*.json')]
    for _ in range(3):
        did=False;gs=[(p,json.loads(p.read_text(encoding='utf-8'))) for p in extras]
        for p,g in gs:
            m=Model(raw[g['job']['case']],spec=g['job']['spec']);pool=[]
            for q,h in gs:
                if h['job']['case']!=g['job']['case'] or h['job']['experiment']!=g['job']['experiment']:continue
                a,b=g['job']['spec'],h['job']['spec']
                if g['job']['experiment']=='E13' and a['slope']==b['slope'] and b['fare_cap']<=a['fare_cap']:pool+=h['records']
                if g['job']['experiment']=='E14' and {k:v for k,v in a.items() if k!='active_period_K'}=={k:v for k,v in b.items() if k!='active_period_K'} and not a['active_period_K']:pool+=h['records']
                if g['job']['experiment']=='E15' and b['fleet_scale']<=a['fleet_scale']:pool+=h['records']
            a=g['job']['spec']
            if g['job']['experiment']=='E15' or (g['job']['experiment']=='E14' and set(a)<= {'active_period_K'}):
                pool+=json.loads((ROOT/'runs/E13'/f'{g["job"]["case"]}_elastic0.8_cap1.2.json').read_text(encoding='utf-8'))['records']
            for i,r in enumerate(g['records']):
                if r['policy']=='P0':continue
                candidates=[x for x in pool if x['policy']==r['policy']]
                for w in candidates:
                    val=m.evaluate(np.array(w['N']),np.array(w['phi']))
                    if val['feasible'][0] and (not r['feasible'] or val[r['objective']][0]>r['objective_value']+1e-5):
                        nr=solve(m,r['objective'],r['policy'],seeds=g['records']+[w],rounds=8);g['records'][i]=r=nr;did=True;changed.append(dict(file=p.name,policy=r['policy'],objective=r['objective']))
            dump(p,g)
        if not did:break
    defaults={'electric_scale':0.,'same_state':False,'ref_load':.88,'variable_share':.7,'chi':1.,'background':0.,'occupancy':2.,'money':1.,'slope':1.,'homogeneous':False,'mu_sc':.3,'mu_pr':.45,'k_cost':1.,'k_fare':1.,'k_time':1.,'k_restart':1.,'capacity':1.}
    for p in (ROOT/'runs').glob('E*/*.json'):
        g=json.loads(p.read_text(encoding='utf-8'));j=g['job'];s=j['spec']
        if j['experiment'] in ['E13','E14','E15'] or j['income']!='reference' or (j['electric']!='none' and s.get('electric_scale',1)!=0):continue
        if any(k not in ['eta','budget','authority','lambda','step','rounds'] and (k not in defaults or v!=defaults[k]) for k,v in s.items()):continue
        pool=json.loads((ROOT/'runs/E13'/f'{j["case"]}_elastic0.8_cap1.2.json').read_text(encoding='utf-8'))['records'];m=Model(raw[j['case']],spec=s);touched=False
        for i,r in enumerate(g['records']):
            if r['policy']=='P0':continue
            for w in pool:
                n=np.array(w['N']);ph=np.array(w['phi']);active=n>0;free=active&~(m.tier=='K')[:,None];step=s.get('step',.025)
                if r['policy']!='P4' and n[m.candidate].sum()>0:continue
                if r['policy']=='P1' and not np.array_equal(n,m.N0):continue
                if r['policy']=='P2' and np.any(abs(ph[active]-1)>1e-8):continue
                if np.any(abs((ph[free]-.8)/step-np.round((ph[free]-.8)/step))>1e-7):continue
                nr=m.record(n,ph,r['objective'],r['policy'],{'round3_witness_source':'E13 central; same behavioral calibration and final constraints'})
                if nr['feasible'] and (not r['feasible'] or nr['objective_value']>r['objective_value']+1e-5):g['records'][i]=r=nr;touched=True
        if touched:g['round3_witness_closure']=True;dump(p,g);changed.append(dict(file=p.name,scope='baseline equivalent-domain witness'))
    dump(ROOT/'round3_witness_closure.json',changed);print('domain closures',len(changed))
if __name__=='__main__':main()
