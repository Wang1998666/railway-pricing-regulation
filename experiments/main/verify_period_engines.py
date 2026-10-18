"""Independent equivalence checks for search caching and single-OD columns."""
import json,numpy as np
from model import ROOT,dump
from run_round5 import engine
from exact_single_od import Exact
from fast_evaluator import CachedPeriods
def main():
    rng=np.random.default_rng(20261015);checks=[]
    specs=[{}, {'electric_scale':.35,'k_withdraw':.5}, {'displacement_cap':60,'background':.15,'chi':.5}, {'ref_load':.92,'variable_share':.5,'lambda':1.}, {'slope':1.25,'fare_cap':1.3,'eta':1.}, {'k_cost':.1,'k_restart':0.,'k_time':.6}, {'schedule_slope':.5}, {'mu_sc':.35,'mu_pr':.5}]
    for ci in ['HN','WC','JX']:
        for spec in specs:
            job=dict(case=ci,income='polarized',electric='all_high',spec=spec);m=engine(job);fast=CachedPeriods(m);N=np.array([rng.integers(m.Nmin,m.Nmax+1) for _ in range(24)],float);grid=np.round(np.arange(.8,m.fare_cap+.001,.025),8);phi=rng.choice(grid,(24,m.S,4,3));phi[:,m.tier=='K']=1.;a=m.evaluate(N,phi);b=fast(N,phi);errors={k:float(np.max(abs(a[k].astype(float)-b[k].astype(float)))) for k in a};assert max(errors.values())<1e-5
            check=dict(case=ci,spec=spec,cache_errors=errors,designs=len(N))
            if ci!='JX':
                phi=np.repeat(phi[:,:,:,:1],3,axis=3);a=m.evaluate(N,phi);ex=Exact(m)
                # period accepts a Cartesian count/fare product, so compare each
                # random matched fare separately rather than pairing by index.
                rows=np.array([[ex.period(h,N[i,:,h][None],phi[i,:2,h,0][None])[0] for h in range(4)] for i in range(len(N))]);service=N.copy();service[:,2]+=N[:,3];service[:,3]=0;active=service.sum(axis=2)>0;active[:,3]=N[:,3].sum(axis=1)>0;profit=rows[:,:,6].sum(axis=1)*1000-active@m.fixed_cost;U=rows[:,:,7].sum(axis=1)*1000;eta=rows[:,:,8].sum(axis=1)/m.ref_vul;err=max(float(np.max(abs(profit-a['profit']))),float(np.max(abs(U-a['U']))),float(np.max(abs(eta-a['eta']))));assert err<1e-5;check['column_error']=err
                canonical=N.copy();total=N[:,2]+N[:,3];canonical[:,2]=np.minimum(total,m.Nmax[2]);canonical[:,3]=total-canonical[:,2];can=m.evaluate(canonical,phi);assert np.max(abs(can['U']-a['U']))<1e-5 and np.all(can['profit']>=a['profit']-1e-5) and np.max(abs(can['maxlf']-a['maxlf']))<1e-9 and np.array_equal(can['structural'],a['structural']);check['pooled_K_dominance']=True
            checks.append(check)
    dump(ROOT/'period_engine_verification.json',dict(passed=True,checks=checks,designs=sum(x['designs'] for x in checks),maximum_cache_error=max(max(x['cache_errors'].values()) for x in checks),maximum_column_error=max(x.get('column_error',0) for x in checks)));print('period engines verified',len(checks),'contexts')
if __name__=='__main__':main()
