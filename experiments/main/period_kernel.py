"""Equivalent nested probabilities in positive-weight form, with safe fallback.

Returns None outside a conservative exponent range so the stable log-sum-exp
implementation remains available. No policy, parameter or objective is changed.
"""
import numpy as np
from scipy.special import expit
def period(m,h,n,ph):
    service=n.copy()
    for s,p in m.parent.items():service[:,p]+=n[:,s];service[:,s]=0
    fare=m.fare[None,:,None]*ph[:,None,None];sched=15*[3,8,3,10][h]/np.maximum(service,1)
    if m.displacement_cap is not None:sched=np.minimum(sched,m.displacement_cap)
    v=m.fixed_rail[None,:,:,h]-m.beta[None,None,:,0,None,None]*fare-m.beta[None,None,:,4,None,None]*sched[:,None,None,:,None]
    valid=(service[:,None,None,:,None]>0)&m.serve.T[None,:,None,:,None]&(m.seats[None,None,None]>0)
    if np.max(np.where(valid,v/m.mu_sc,-np.inf))>500 or np.max(abs(m.road_logs[:,:,h]/.75))>500:return None
    sw=np.where(valid,np.exp(np.clip(v/m.mu_sc,-745,500)),0.);ss=sw.sum(axis=-1);pw=ss**(m.mu_sc/m.mu_pr);rs=pw.sum(axis=-1);rw=rs**(m.mu_pr/.75);road=np.exp(m.road_logs[:,:,h]/.75);mw=np.concatenate([rw[...,None],np.broadcast_to(road[None],(*rw.shape,2))],axis=-1);ms=mw.sum(axis=-1);travel=.75*np.log(ms);part=expit(travel);pm=mw/ms[...,None]
    ps=np.divide(pw,rs[...,None],out=np.zeros_like(pw),where=rs[...,None]>0);pb=np.divide(sw,ss[...,None],out=np.zeros_like(sw),where=ss[...,None]>0);qr=m.qbar[None,:,:,h,None,None]*part[...,None,None]*pm[...,0,None,None]*ps[...,None]*pb
    rev=(qr*fare).sum(axis=(1,2,3,4));U=(m.qbar[None,:,:,h]*np.logaddexp(0,travel)/m.beta[None,None,:,0]).sum(axis=(1,2));L=(m.qbar[None,:,2,h]*part[:,:,2]).sum(axis=1)
    loads=np.einsum('awsb,swe->asbe',qr.sum(axis=2),m.pax,optimize=False);loads+=m.c['background_fraction']*m.N0[None,:,h,None,None]*m.seats[None,:,:,None]*m.route[None,:,None,:];den=service[:,:,None,None]*m.seats[None,:,:,None];lf=np.divide(loads,den,out=np.zeros_like(loads),where=den>0).max(axis=(1,2,3));co2=np.zeros(len(n))
    if hasattr(m,'carbon_ef'):
        ef=m.carbon_ef;shared=m.road_probs[:,:,h]@ef[1:];Q=m.qbar[None,:,:,h]*part;co2=(Q*np.array(m.c['road_km'])[None,:,None]*(pm[...,2]*ef[0]+pm[...,1]*shared)).sum(axis=(1,2))
    return np.column_stack([rev,U,L,lf,co2])
