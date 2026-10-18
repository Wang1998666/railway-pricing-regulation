"""Cache additive period demand during coordinated search; full records use Model.

This is an evaluation accelerator, not a new objective or decision domain.
"""
import numpy as np
from scipy.special import logsumexp,expit
class CachedPeriods:
    def __init__(self,m):self.m=m;self.original=m.evaluate;self.cache=[{} for _ in range(4)]
    def period(self,h,n,ph):
        from period_kernel import period
        result=period(self.m,h,n,ph)
        return self.period_reference(h,n,ph) if result is None else result
    def period_reference(self,h,n,ph):
        m=self.m;service=n.copy()
        for s,p in m.parent.items():service[:,p]+=n[:,s];service[:,s]=0
        fare=m.fare[None,:,None]*ph[:,None,None]
        sched=15*[3,8,3,10][h]/np.maximum(service,1)
        if m.displacement_cap is not None:sched=np.minimum(sched,m.displacement_cap)
        v=m.fixed_rail[None,:,:,h]-m.beta[None,None,:,0,None,None]*fare-m.beta[None,None,:,4,None,None]*sched[:,None,None,:,None]
        valid=(service[:,None,None,:,None]>0)&m.serve.T[None,:,None,:,None]&(m.seats[None,None,None]>0);v=np.where(valid,v,-1e100)
        ls=logsumexp(v/m.mu_sc,axis=-1)*m.mu_sc;rail=logsumexp(ls/m.mu_pr,axis=-1)*m.mu_pr;mode=np.concatenate([rail[...,None],np.broadcast_to(m.road_logs[None,:,:,h],(*rail.shape,2))],axis=-1);travel=logsumexp(mode/.75,axis=-1)*.75;part=expit(travel);pm=np.exp((mode-travel[...,None])/.75)
        qr=m.qbar[None,:,:,h,None,None]*part[...,None,None]*pm[...,0,None,None]*np.exp((ls-rail[...,None])/m.mu_pr)[...,None]*np.where(valid,np.exp((v-ls[...,None])/m.mu_sc),0)
        rev=(qr*fare).sum(axis=(1,2,3,4));U=(m.qbar[None,:,:,h]*np.logaddexp(0,travel)/m.beta[None,None,:,0]).sum(axis=(1,2));L=(m.qbar[None,:,2,h]*part[:,:,2]).sum(axis=1)
        loads=np.einsum('awsb,swe->asbe',qr.sum(axis=2),m.pax,optimize=False);loads+=m.c['background_fraction']*m.N0[None,:,h,None,None]*m.seats[None,:,:,None]*m.route[None,:,None,:];den=service[:,:,None,None]*m.seats[None,:,:,None];lf=np.divide(loads,den,out=np.zeros_like(loads),where=den>0).max(axis=(1,2,3))
        co2=np.zeros(len(n))
        if hasattr(m,'carbon_ef'):
            ef=m.carbon_ef;shared=m.road_probs[:,:,h]@ef[1:];Q=m.qbar[None,:,:,h]*part;co2=(Q*np.array(m.c['road_km'])[None,:,None]*(pm[...,2]*ef[0]+pm[...,1]*shared)).sum(axis=(1,2))
        return np.column_stack([rev,U,L,lf,co2])
    def __call__(self,N,phi,details=False,baseline=False):
        if details or baseline:return self.original(N,phi,details,baseline)
        m=self.m;N=np.asarray(N,float);phi=np.asarray(phi,float)
        if N.ndim==2:N=N[None]
        if phi.ndim==3:phi=phi[None]
        size=max(len(N),len(phi));N=np.broadcast_to(N,(size,m.S,4));phi=np.broadcast_to(phi,(size,m.S,4,3));m.evaluations+=size;values=[]
        for h in range(4):
            cache=self.cache[h];keys=[(N[i,:,h].tobytes(),phi[i,:,h].tobytes()) for i in range(size)];missing={k:i for i,k in enumerate(keys) if k not in cache}
            if missing:
                ids=list(missing.values());new=self.period(h,N[ids,:,h],phi[ids,:,h]);cache.update(zip(missing,new))
            values.append(np.array([cache[k] for k in keys]))
            if len(cache)>50000:self.cache[h]={k:cache[k] for k in keys}
        vals=np.stack(values,axis=1);service=N.copy()
        for s,p in m.parent.items():service[:,p]+=N[:,s];service[:,s]=0
        active=service.sum(axis=2)>0;active[:,m.candidate]=N[:,m.candidate].sum(axis=2)>0;cost=(N*m.run_cost[None,:,None]).sum(axis=(1,2))+(active*m.fixed_cost).sum(axis=1);rev=vals[:,:,0].sum(axis=1);profit=rev-cost;U=vals[:,:,1].sum(axis=1);eta=vals[:,:,2].sum(axis=1)/m.ref_vul;lf=vals[:,:,3].max(axis=1);welfare=U-m.state_U+profit-m.state_profit
        if hasattr(m,'carbon_ef'):welfare-=m.carbon_price*(vals[:,:,4].sum(axis=1)-m.carbon_baseline)/1000
        paths=np.einsum('ash,se->ahe',N,m.route,optimize=False);fleet=np.stack([(N[:,m.tier==t]*m.cycle[None,m.tier==t,None]).sum(axis=(1,2)) for t in ['G','D','K']],axis=1);ods=np.einsum('ash,sw->awh',N,m.serve.astype(float),optimize=False)
        struct=(np.maximum(paths-m.cap[None],0).max(axis=(1,2))<1e-8)&np.all(fleet<=m.fleet[None]+1e-8,axis=1)&np.all(ods>=m.odfloor[None]-1e-8,axis=(1,2));struct&=np.all(N[:,m.fixed]==m.N0[None,m.fixed],axis=(1,2))&np.all((N>=m.Nmin[None])&(N<=m.Nmax[None]),axis=(1,2))&np.all(N[:,m.adjustable].sum(axis=2)>=1,axis=1)
        violation=np.maximum(lf-m.lam,0)+np.maximum(m.eta_floor-eta,0)+np.maximum(-profit-m.budget,0)/max(1.,abs(m.c['reference_revenue']))+np.where(struct,0,100);feasible=struct&(lf<=m.lam+1e-9)&(eta>=m.eta_floor-1e-9)&(profit>=-m.budget-1e-6)
        return dict(profit=profit,welfare=welfare,U=U,revenue=rev,cost=cost,eta=eta,maxlf=lf,structural=struct,violation=violation,feasible=feasible)
def install(m):
    if not isinstance(m.evaluate,CachedPeriods):m.evaluate=CachedPeriods(m)
