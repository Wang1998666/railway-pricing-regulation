import numpy as np,time
from model import ROOT,dump
from run_round5 import engine
from fast_evaluator import CachedPeriods
from period_kernel import period
def main():
    rng=np.random.default_rng(6);checks=[]
    for ci in ['HN','WC','JX']:
        for spec in [{},{'electric_scale':.35,'k_withdraw':1.},{'money':3.,'mu_sc':.25,'mu_pr':.5},{'slope':1.25,'fare_cap':1.3,'schedule_slope':1.5},{'demand':2.,'displacement_cap':60}]:
            m=engine(dict(case=ci,income='polarized',electric='all_high',spec=spec));old=CachedPeriods(m);N=np.array([rng.integers(m.Nmin,m.Nmax+1) for _ in range(64)],float);ph=rng.choice(np.arange(.8,1.201,.025),(64,m.S,4,3));ph[:,m.tier=='K']=1.
            for h in range(4):
                a=old.period_reference(h,N[:,:,h],ph[:,:,h]);b=period(m,h,N[:,:,h],ph[:,:,h]);assert b is not None;err=float(np.max(abs(a-b)));assert err<1e-5;checks.append(dict(case=ci,spec=spec,period=h,error=err))
    m=engine({'case':'JX'});old=CachedPeriods(m);N=np.broadcast_to(m.N0[:,1],(81,m.S)).copy();ph=np.ones((81,m.S,3));ph[:,:2]=rng.choice(np.arange(.8,1.201,.025),(81,2,3));times=[]
    for fn in [old.period_reference,lambda h,n,p:period(m,h,n,p)]:
        t=time.perf_counter()
        for _ in range(60):fn(1,N,ph)
        times.append(time.perf_counter()-t)
    out=dict(passed=True,checks=checks,maximum_error=max(r['error'] for r in checks),old_seconds=times[0],new_seconds=times[1],kernel_speedup=times[0]/times[1]);dump(ROOT/'period_kernel_verification.json',out);print({k:v for k,v in out.items() if k!='checks'},flush=True)
if __name__=='__main__':main()
