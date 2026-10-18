"""Transparent scenario recalibration, preserving aggregate seat loads and VOT."""
import copy,json
from functools import lru_cache
import numpy as np
from scipy.special import logsumexp,expit
TEMPLATES={}
KEYS=['ref_load','variable_share','background','chi','occupancy','mu_sc','mu_pr','slope','money','homogeneous','schedule_scale','displacement_cap']

def targets(c,load=.88,background=0.,homogeneous=False):
    ps=c['products']; W=len(c['ods']); S=len(ps); q=np.zeros((W,4,S,3))
    for s,p in enumerate(ps):
        if p['candidate']: continue
        w=np.array(p['serve'],float)/np.array(c['road_km']); w/=max(np.array(p['pax']).T@w)
        q[:,:,s,:]=w[:,None,None]*np.array(p['N0'])[None,:,None]*np.array(p['seats'])[None,None,:]*{'G':.78,'D':.72,'K':.70}[p['tier']]/.78*(load-background)
    shares=np.array(c['rail_share_targets']); pi=np.array([.9,.85,.8]) if not homogeneous else np.full(3,.85)
    rail=np.broadcast_to(shares[:,None],(W,3)).copy()
    if not homogeneous: rail+=np.array([.04,0,-.045])[None]
    pop=q.sum(axis=(2,3))[:,None,:]/(.85*shares[:,None,None])*np.array([.2,.6,.2])[None,:,None]
    desired=np.zeros((W,3,4,S,3))
    for w in range(W):
        for h in range(4):
            col=q[w,h].reshape(-1); rows=pop[w,:,h]*pi*rail[w]; active=col>0
            if not active.any(): continue
            score=[]
            for p in ps:
                for b in range(3): score.append((1.8 if p['premium'][b] else 0)+(.25 if p['tier']=='G' else -.5 if p['tier']=='K' else 0))
            affinity=np.exp(np.array([1.,0.,-1.])[:,None]*np.array(score)[None,active]) if not homogeneous else np.ones((3,active.sum()))
            mat=affinity*col[active][None]
            for _ in range(1000):
                mat*=rows[:,None]/mat.sum(axis=1)[:,None]; mat*=col[active][None]/mat.sum(axis=0)[None]
                if np.max(abs(mat.sum(axis=1)-rows))<1e-9: break
            full=np.zeros((3,S*3)); full[:,active]=mat; desired[w,:,h]=full.reshape(3,S,3)
    return pop,desired,pi,rail

def prepare(template,spec):
    ci=template['id']; TEMPLATES[ci]=template
    return _prepare(ci,json.dumps({k:spec[k] for k in KEYS if k in spec},sort_keys=True))

@lru_cache(maxsize=200)
def _prepare(ci,encoded):
    spec=json.loads(encoded); c=copy.deepcopy(TEMPLATES[ci]); ps=c['products']; S=len(ps); W=len(c['ods'])
    load=spec.get('ref_load',.88); bg=spec.get('background',0.); delta=spec.get('variable_share',.7); chi=spec.get('chi',1.); occ=spec.get('occupancy',2.)
    pop,qr,pi,rail=targets(c,load,bg,spec.get('homogeneous',False)); basepop,baseqr,_,_=targets(c,load,0.,spec.get('homogeneous',False))
    beta=np.array(c['beta']); fares=np.array([p['fare'] for p in ps]).transpose(1,0,2)
    # Quantity-weighted own G/D product-period fare elasticity; K held fixed.
    _,anchorqr,anchorpi,anchorrail=targets(c,.88,0.,False)
    product_q=anchorqr.sum(axis=-1)
    conditional=product_q/product_q.sum(axis=-1,keepdims=True)
    mean_fare=np.divide((anchorqr*fares[:,None,None,:,:]).sum(axis=-1),product_q,out=np.zeros_like(product_q),where=product_q>0)
    outer=((1-anchorrail)/.75+(1-anchorpi)[None]*anchorrail)[:,:,None,None]
    sensitivity=beta[None,:,None,0,None]*mean_fare*((1-conditional)/.45+conditional*outer)
    gd=np.array([p['tier']!='K' and not p['candidate'] for p in ps])
    anchor=float((product_q[...,gd]*sensitivity[...,gd]).sum()/product_q[...,gd].sum()); factor=.8/anchor*spec.get('slope',1.)
    beta*=factor; beta[:,0]*=spec.get('money',1.)
    beta[:,4]*=spec.get('schedule_scale',1.)
    mu_sc=spec.get('mu_sc',.30); mu_pr=spec.get('mu_pr',.45)
    road=np.array(c['road']); road[:,0,0]/=occ
    access=np.array(c['access']); alpha=np.zeros_like(qr)
    rawroad=-np.einsum('kj,wij->wki',beta[:,:7],road[:,:,:7])+np.einsum('kj,wij->wki',beta[:,7:],road[:,:,7:]); ra=np.zeros((W,3,4,4))
    comfort=np.array([p['comfort'] for p in ps]); flex=np.array([1 if p['tier']=='K' else 2 for p in ps]); rel=np.array([{'G':.02,'D':.03,'K':.08}[p['tier']] for p in ps])
    for w in range(W):
        for h in range(4):
            # Class-specific road/auto allocation; retain aggregate auto fraction .4.
            nonrail=pop[w,:,h]*pi*(1-rail[w]); mode=np.array([.6,.4,.2]) if not spec.get('homogeneous',False) else np.full(3,.4)
            mat=nonrail[:,None]*np.stack([mode,1-mode],axis=1)
            if nonrail.sum()>0:
                for _ in range(200):
                    mat*=np.array([.4,.6])[None]*nonrail.sum()/mat.sum(axis=0)[None]; mat*=nonrail[:,None]/mat.sum(axis=1)[:,None]
                auto=mat[:,0]/nonrail
            else: auto=np.full(3,.4)
            for k in range(3):
                travel=np.log(pi[k]/(1-pi[k])); railV=travel+.75*np.log(rail[w,k]); roadV=travel+.75*np.log((1-rail[w,k])*(1-auto[k])); autoV=travel+.75*np.log((1-rail[w,k])*auto[k])
                ra[w,k,h]=np.array([autoV,*list(roadV+.5*np.log([.75,.22,.03]))])-rawroad[w,k]
                total=qr[w,k,h].sum()
                for s,p in enumerate(ps):
                    qs=qr[w,k,h,s].sum()
                    if qs<=0: continue
                    seat=qr[w,k,h,s]/qs
                    target=railV+mu_pr*np.log(qs/total)+mu_sc*np.log(np.maximum(seat,1e-100))
                    rt=np.array(p['runtime'])[w]; sched=15*[3,8,3,10][h]/p['N0'][h]
                    if spec.get('displacement_cap') is not None:sched=min(sched,spec['displacement_cap'])
                    raw=(-beta[k,0]*(fares[w,s]+access[w,1])-beta[k,1]*rt-beta[k,2]*access[w,0]-beta[k,3]*10-beta[k,4]*sched-beta[k,5]*rt*rel[s]+beta[k,7]*comfort[s]+beta[k,8]*flex[s])
                    alpha[w,k,h,s]=target-raw
    for s,p in enumerate(ps):
        parent=next(i for i,x in enumerate(ps) if x['id']==p['parent']) if p['candidate'] else s; ns=np.array(ps[parent]['N0']); active=np.flatnonzero(ns)
        for h in range(4):
            near=h if ns[h]>0 else int(active[np.argmin(abs(active-h))])
            if p['candidate']: alpha[:,:,h,s]=alpha[:,:,near,parent]-mu_pr*np.log(max(1,ns[near]))
            elif ns[h]==0: alpha[:,:,h,s]=alpha[:,:,near,s]
    # Separate marginal departure cost and retained product commitments at fixed total reference cost.
    refrev=float((baseqr*fares[:,None,None,:,:]).sum()); totalcost=.92*refrev
    vweights=np.array([sum(p['N0'])*p['run_cost'] if not p['candidate'] else 0 for p in ps]); fweights=np.array([p['fixed_cost'] if not p['candidate'] else 0 for p in ps])
    for s,p in enumerate(ps):
        if p['candidate']: continue
        p['run_cost']=chi*delta*totalcost*vweights[s]/vweights.sum()/sum(p['N0']); p['fixed_cost']=chi*(1-delta)*totalcost*fweights[s]/fweights.sum()
    for p in ps:
        if p['candidate']:
            parent=next(x for x in ps if x['id']==p['parent']); p['run_cost']=parent['run_cost']; p['fixed_cost']=.1*parent['fixed_cost']
    ref_revenue=float((qr*fares[:,None,None,:,:]).sum())
    c.update(qbar=pop.tolist(),beta=beta.tolist(),road=road.tolist(),alpha=alpha.tolist(),road_alpha=ra.tolist(),mu_sc=mu_sc,mu_pr=mu_pr,occupancy=occ,reference_load=load,background_fraction=bg,variable_share=delta,cost_share=chi,coefficient_scale=factor,target_rail=qr.tolist(),class_participation_targets=pi.tolist(),class_rail_targets=rail.tolist(),calibrated_reference_revenue=ref_revenue,reference_revenue=ref_revenue,reference_profit=ref_revenue-chi*totalcost,full_reference_cost=totalcost)
    return c
