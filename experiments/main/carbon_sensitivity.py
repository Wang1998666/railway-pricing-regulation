"""Road-carbon-augmented railway welfare; separate from the frozen main solver."""
import os
for key in ['OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','OMP_NUM_THREADS']: os.environ[key]='1'
import json,copy,math
from concurrent.futures import ProcessPoolExecutor
import numpy as np
from model import ROOT,Model,solve,dump
from analyze import groups,record
from verify import scalar,lse

PARAMS=dict(grid_kg_kwh=.5306,gasoline_kg_liter=8.887/3.785411784,diesel_kg_liter=10.180/3.785411784,fuel_liter_vehicle_km=[.07,.25,.09,.10],electric_kwh_vehicle_km=[.15,.90,.25,.28],occupancy=[2.,30.,6.,4.],carbon_prices=[100.,500.],baseline_ev_shares=[.25,.50])

def factors(m,baseline_share):
    fuel=np.array(PARAMS['fuel_liter_vehicle_km'])*np.array([PARAMS['gasoline_kg_liter'],PARAMS['diesel_kg_liter'],PARAMS['gasoline_kg_liter'],PARAMS['gasoline_kg_liter']])/np.array(PARAMS['occupancy'])
    ev=np.array(PARAMS['electric_kwh_vehicle_km'])*PARAMS['grid_kg_kwh']/np.array(PARAMS['occupancy']); assert np.all(ev<fuel)
    x=m.spec.get('electric_scale',0.) if m.electric!='none' else 0.; share=baseline_share+(1-baseline_share)*np.array([.5,1.,1.,1.])*x
    return (1-share)*fuel+share*ev

def vector_carbon(m,out,ef):
    Q=out['Q']; pm=out['mode_probs']; auto=Q*pm[...,2]; shared=Q[...,None]*pm[...,1,None]*m.road_probs[None]
    flows=np.concatenate([auto[...,None],shared],axis=-1)
    return (flows*np.array(m.c['road_km'])[None,:,None,None,None]*ef[None,None,None,None,:]).sum(axis=(1,2,3,4))

def scalar_carbon(c,N,phi,income,electric,spec,ef):
    r=scalar(c,N,phi,income,electric,spec); co2=0.; beta=np.array(c['beta']); from model import INCOMES
    beta[:,0]*=np.exp(-np.array([.7,.8,.9])*INCOMES[income])
    for w in range(len(c['ods'])):
        for k in range(3):
            for h in range(4):
                vals=[]
                for i,attrs in enumerate(c['road'][w]):
                    a=list(attrs)
                    if electric!='none':
                        x=spec['electric_scale']
                        if i==0: a[0]-=.58*c['road_km'][w]*.5*x/c['occupancy']
                        else: a[0]-=[0,.12,.20,.30][i]*c['road_km'][w]*.7*x
                    vals.append(c['road_alpha'][w][k][h][i]-sum(beta[k,j]*a[j] for j in range(7))+sum(beta[k,j]*a[j] for j in [7,8]))
                road=lse(vals[1:],.5); roadef=sum(math.exp((vals[i]-road)/.5)*ef[i] for i in range(1,4))
                co2+=r['Q'][w,k,h]*c['road_km'][w]*(r['mode_probs'][w,k,h,2]*ef[0]+r['mode_probs'][w,k,h,1]*roadef)
    return r,co2

def execute(job):
    g,price,baseEV=job; ci=g['job']['case']; spec=g['job']['spec']; c=json.loads((ROOT/'inputs'/f'{ci}.json').read_text(encoding='utf-8')); m=Model(c,'reference',g['job']['electric'],spec); ef=factors(m,baseEV); orig=m.evaluate
    base=orig(m.N0,np.ones((m.S,4,3)),True); base_co2=vector_carbon(m,base,ef)[0]
    def augmented(N,ph,details=False,baseline=False):
        values=orig(N,ph,True,baseline); co2=vector_carbon(m,values,ef); values['welfare']=values['welfare']-price*(co2-base_co2)/1000; return values
    m.evaluate=augmented;m.carbon_ef=ef;m.carbon_price=price;m.carbon_baseline=base_co2;old=record(g,'P4','welfare')
    if ci in ['HN','WC']:
        from exact_single_od import Exact
        result=Exact(m,seeds=g['records']).solve('P4','welfare');assert result and result['success'];r=result['record']
    else:
        from run_round5 import multistart
        r=multistart(m,'P4','welfare',g['records'],strong=True)
    final=orig(np.array(r['N']),np.array(r['phi']),True); co2=float(vector_carbon(m,final,ef)[0]); railW=float(final['welfare'][0]); oldaug=float(augmented(np.array(old['N']),np.array(old['phi']))['welfare'][0])
    sr,sc=scalar_carbon(m.c,np.array(r['N']),np.array(r['phi']),'reference',m.electric,spec,ef); br,bc=scalar_carbon(m.c,m.N0,np.ones((m.S,4,3)),'reference',m.electric,spec,ef)
    val=sr['U']-br['U']+sr['profit']-br['profit']-price*(sc-bc)/1000; error=abs(val-r['welfare']); assert error<1e-6 and abs(sc-co2)<1e-6
    out=dict(case_id=ci,intensity=spec['electric_scale'],price=price,baseline_ev=baseEV,emission_factors=ef.tolist(),feasible=r['feasible'],railway_welfare=railW,augmented_welfare=r['welfare'],road_CO2_change_tonnes=(co2-base_co2)/1000,optimization_gain=r['welfare']-oldaug,changed=not(np.array_equal(r['N'],old['N']) and np.allclose(r['phi'],old['phi'])),scalar_error=error,record=r)
    return out

def main():
    selected=[g for g in groups('E2') if g['job']['income']=='reference' and not g['job']['spec'].get('road_contrast') and g['job']['spec']['electric_scale'] in [0.,.35]]
    jobs=[(g,p,e) for g in selected for p in PARAMS['carbon_prices'] for e in PARAMS['baseline_ev_shares']]
    with ProcessPoolExecutor(max_workers=8) as pool: results=list(pool.map(execute,jobs))
    dump(ROOT/'carbon_sensitivity.json',dict(parameters=PARAMS,records=results)); print('carbon scenarios',len(results),'feasible',sum(r['feasible'] for r in results),'changed',sum(r['changed'] for r in results),'max gain',max(r['optimization_gain'] for r in results))
if __name__=='__main__': main()
