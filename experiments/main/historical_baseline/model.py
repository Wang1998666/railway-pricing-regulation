"""Review revision: recalibrated demand, explicit costs and occupancy sensitivities."""
from __future__ import annotations
import copy, hashlib, itertools, json, time
from pathlib import Path
import numpy as np
from scipy.special import logsumexp, expit

VERSION = 'v3-round3-1'
ROOT = Path(__file__).resolve().parent
CLASSES = ['H','M','L']
INCOMES = {'reference': np.zeros(3), 'uniform': np.full(3,np.dot([.2,.6,.2],np.log([1.02,.92,.85]))), 'polarized':np.log([1.02,.92,.85]), 'severe_uniform':np.full(3,np.log(.9)), 'severe_polarized':1.5*np.log([1.02,.92,.85])}
ELECTRICS = ['none','auto','am_low','am_high','all_low','all_high']

def dump(path, obj):
    def default(x):
        if isinstance(x,np.ndarray): return x.tolist()
        if isinstance(x,np.generic): return x.item()
        raise TypeError(type(x).__name__)
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp'); tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2,default=default,allow_nan=False),encoding='utf-8'); tmp.replace(path)

class Model:
    def __init__(self, case, income='reference', electric='none', spec=None, _reference=True):
        from calibration import prepare
        self.spec=spec or {}; self.c=copy.deepcopy(prepare(case,self.spec)); c=self.c
        self.income=income; self.electric=electric
        self.S=len(c['products']); self.W=len(c['ods']); self.H=4; self.B=3
        self.tier=np.array([p['tier'] for p in c['products']]); self.candidate=np.array([p['candidate'] for p in c['products']])
        self.parent={s:next(i for i,p in enumerate(c['products']) if p['id']==c['products'][s]['parent']) for s in np.flatnonzero(self.candidate)}
        self.N0=np.array([p['N0'] for p in c['products']],float); self.Nmax=np.array([p['Nmax'] for p in c['products']],float)
        self.authority=float(self.spec.get('authority',.50))
        self.adjustable=(self.tier!='K')&~self.candidate
        self.fixed=(self.tier=='K')&~self.candidate
        self.k_withdraw=float(self.spec.get('k_withdraw',0.))
        self.withdrawable=(self.tier=='K')&~self.candidate&(self.k_withdraw>0)
        self.fixed &= ~self.withdrawable
        self.freq_adjustable=self.adjustable|self.withdrawable
        self.Nmin=np.zeros_like(self.N0)
        self.Nmin[self.fixed]=self.N0[self.fixed]
        self.Nmin[self.withdrawable]=np.ceil((1-self.k_withdraw)*self.N0[self.withdrawable])
        self.Nmin[self.adjustable]=np.ceil((1-self.authority)*self.N0[self.adjustable])
        self.Nmax[self.adjustable]=np.maximum(2,self.N0[self.adjustable]+np.floor(self.authority*self.N0[self.adjustable]))
        if self.authority<=0:
            self.Nmin[self.adjustable]=self.N0[self.adjustable]
            self.Nmax[self.adjustable]=self.N0[self.adjustable]
        if self.spec.get('active_period_K',False):
            for s,parent in self.parent.items():self.Nmax[s,self.N0[parent]==0]=0
        self.seats=np.array([p['seats'] for p in c['products']],float)
        self.route=np.array([p['route'] for p in c['products']],float)
        self.pax=np.array([p['pax'] for p in c['products']],float) # s,w,e
        self.serve=np.array([p['serve'] for p in c['products']],bool)
        self.qbar=np.array(c['qbar'],float)*self.spec.get('demand',1.) # w,k,h
        if 'class_shares' in self.spec:
            self.qbar*=np.array(self.spec['class_shares'])[None,:,None]/np.array([.2,.6,.2])[None,:,None]
        self.beta=np.array(c['beta'],float)
        dy=INCOMES[income] if income in INCOMES else np.array(self.spec['dy'])
        self.beta[:,0]*=np.exp(-np.array([.7,.8,.9])*dy)
        self.mu_sc=self.spec.get('mu_sc',.30); self.mu_pr=self.spec.get('mu_pr',.45); self.mu_mode=.75
        self.eta_floor=self.spec.get('eta',.95); self.budget=self.spec.get('budget',2000.*self.N0.sum())
        self.lam=self.spec.get('lambda',.95)
        self.fare_cap=float(self.spec.get('fare_cap',1.2))
        self.displacement_cap=self.spec.get('displacement_cap',None)
        self.alpha=np.array(c['alpha'],float) # w,k,h,s,b
        self.fare=np.array([p['fare'] for p in c['products']],float).transpose(1,0,2) # w,s,b
        self.runtime=np.array([p['runtime'] for p in c['products']],float).T
        self.fare[:,self.tier=='K']*=self.spec.get('k_fare',1.)
        self.runtime[:,self.tier=='K']*=self.spec.get('k_time',1.)
        self.run_cost=np.array([p['run_cost'] for p in c['products']],float)
        self.fixed_cost=np.array([p['fixed_cost'] for p in c['products']],float)
        self.run_cost[self.tier=='K']*=self.spec.get('k_cost',1.)
        self.fixed_cost[self.tier=='K']*=self.spec.get('k_cost',1.)
        self.fixed_cost[self.candidate]*=self.spec.get('k_restart',1.)
        self.cycle=np.array([p['cycle'] for p in c['products']],float)
        self.cycle[self.tier=='K']=(self.cycle[self.tier=='K']-1.)*self.spec.get('k_time',1.)+1.
        self.cap=np.array(c['path_capacity'],float)
        self.fleet=np.array(c['fleet_hours'],float)*self.spec.get('fleet_scale',1.)
        if 'capacity' in self.spec: self.cap*=self.spec['capacity']
        self.odfloor=np.array(c['od_floor'],float)
        # Stable preference coefficients and nonmonetary rail attributes.
        access=np.array(c['access'],float)
        comfort=np.array([p['comfort'] for p in c['products']],float)
        flex=np.array([2. if p['tier']!='K' else 1. for p in c['products']])
        rel=np.array([{'G':.02,'D':.03,'K':.08}[p['tier']] for p in c['products']])
        beta=self.beta
        base=(-beta[None,:,None,1,None,None]*self.runtime[:,None,None,:,None]
              -beta[None,:,None,2,None,None]*access[:,None,None,None,0,None]
              -beta[None,:,None,3,None,None]*10
              -beta[None,:,None,5,None,None]*self.runtime[:,None,None,:,None]*rel[None,None,None,:,None]
              +beta[None,:,None,7,None,None]*comfort[None,None,None,:,:]
              +beta[None,:,None,8,None,None]*flex[None,None,None,:,None]
              -beta[None,:,None,0,None,None]*access[:,None,None,None,1,None])
        self.fixed_rail=self.alpha+base
        road=np.array(c['road'],float) # w,i,cost,iv,ac,wt,sc,rel,transfer,comfort,flex
        scale=self.spec.get('electric_scale',1.)
        if electric!='none':
            road[:,0,0]-=.58*np.array(c['road_km'])*.5*scale/c['occupancy']
            affected=[2,3] if electric.startswith('am') else ([1,2,3] if electric.startswith('all') else [])
            psi=.3 if electric.endswith('low') else .7
            for i in affected: road[:,i,0]-=np.array(c['road_km'])*[0,.12,.20,.30][i]*psi*scale
        if np.any(road[:,:,0]<=0): raise ValueError('Electrification implies nonpositive road monetary cost')
        self.road=road
        rb=-np.einsum('kj,wij->wki',beta[:,:7],road[:,:,:7])+np.einsum('kj,wij->wki',beta[:,7:],road[:,:,7:])
        self.roadU=rb[:,:,None,:]+np.array(c['road_alpha'])
        self.road_logs=np.stack([logsumexp(self.roadU[:,:,:,1:]/.5,axis=-1)*.5,self.roadU[:,:,:,0]],axis=-1)
        self.road_probs=np.exp(self.roadU[:,:,:,1:]/.5-self.road_logs[:,:,:,0,None]/.5)
        # Reference denominator is the unperturbed calibrated reference market.
        # Demand/share robustness uses its own reference populations.
        self.ref_vul=float(self.qbar[:,2,:].sum()*.85)
        self.base_profit=float(c['reference_profit'])
        self.base_U=float(c['reference_U'])
        self.evaluations=0
        raw=self.evaluate(self.N0,np.ones((self.S,4,3)),details=True,baseline=True)
        self.state_profit=float(raw['profit'][0]); self.state_U=float(raw['U'][0])
        if _reference and (income!='reference' or electric!='none'):
            ref=Model(case,'reference','none',self.spec,_reference=False)
            self.ref_vul=ref.ref_vul
        else:
            self.ref_vul=float(raw['Q'][0,:,2,:].sum())
        if self.spec.get('same_state',False): self.ref_vul=float(raw['Q'][0,:,2,:].sum())

    def evaluate(self,N,phi,details=False,baseline=False):
        N=np.asarray(N,float); phi=np.asarray(phi,float)
        if N.ndim==2: N=N[None]
        if phi.ndim==3: phi=phi[None]
        size=max(len(N),len(phi)); N=np.broadcast_to(N,(size,self.S,4)); phi=np.broadcast_to(phi,(size,self.S,4,3))
        self.evaluations+=size
        service_N=N.copy()
        for s,parent in self.parent.items():
            service_N[:,parent]+=N[:,s]
            service_N[:,s]=0
        # V shape: batch,w,k,h,s,b.
        ph=phi.transpose(0,2,1,3)[:,None,None,:,:,:]
        fare=self.fare[None,:,None,None,:,:]*ph
        sched=15*np.array([3,8,3,10])[None,None,None,:,None,None]/np.maximum(service_N.transpose(0,2,1)[:,None,None,:,:,None],1)
        if self.displacement_cap is not None:sched=np.minimum(sched,self.displacement_cap)
        v=self.fixed_rail[None]-self.beta[None,None,:,None,0,None,None]*fare-self.beta[None,None,:,None,4,None,None]*sched
        valid=(service_N.transpose(0,2,1)[:,None,None,:,:,None]>0)&self.serve.T[None,:,None,None,:,None]&(self.seats[None,None,None,None,:,:]>0)
        v=np.where(valid,v,-1e100)
        ls=logsumexp(v/self.mu_sc,axis=-1)*self.mu_sc
        lrail=logsumexp(ls/self.mu_pr,axis=-1)*self.mu_pr
        lmode=np.concatenate([lrail[...,None],np.broadcast_to(self.road_logs[None],(size,*self.road_logs.shape))],axis=-1)
        travel=logsumexp(lmode/.75,axis=-1)*.75
        part=expit(travel); pm=np.exp((lmode-travel[...,None])/.75)
        ps=np.exp((ls-lrail[...,None])/self.mu_pr)
        pb=np.exp((v-ls[...,None])/self.mu_sc); pb=np.where(valid,pb,0.)
        qr=self.qbar[None,:,:,:,None,None]*part[:,:,:,:,None,None]*pm[:,:,:,:,0,None,None]*ps[...,None]*pb
        qr=np.where(valid,qr,0.)
        revenue=(qr*fare).sum(axis=(1,2,3,4,5))
        commitments=service_N.sum(axis=2)>0
        commitments[:,self.candidate]=N[:,self.candidate].sum(axis=2)>0
        cost=(N*self.run_cost[None,:,None]).sum(axis=(1,2))+(commitments*self.fixed_cost[None]).sum(axis=1)
        profit=revenue-cost
        U=(self.qbar[None]*np.logaddexp(0,travel)/self.beta[None,None,:,None,0]).sum(axis=(1,2,3))
        welfare=U-self.state_U+profit-self.state_profit if not baseline else np.zeros(size)
        eta=(self.qbar[None,:,2,:]*part[:,:,2,:]).sum(axis=(1,2))/self.ref_vul
        # Sum class flows onto actual passenger subpaths; capacity by s,h,b,e.
        qws=qr.sum(axis=2) # batch,w,h,s,b
        loads=np.einsum('awhsb,swe->ashbe',qws,self.pax,optimize=False)
        loads+=self.c['background_fraction']*self.N0[None,:,:,None,None]*self.seats[None,:,None,:,None]*self.route[None,:,None,None,:]
        denom=service_N[:,:,:,None,None]*self.seats[None,:,None,:,None]
        lf=np.divide(loads,denom,out=np.zeros_like(loads),where=denom>0)
        maxlf=lf.max(axis=(1,2,3,4))
        paths=np.einsum('ash,se->ahe',N,self.route,optimize=False)
        pathgap=np.maximum(paths-self.cap[None],0).max(axis=(1,2))
        fleet=np.stack([(N[:,self.tier==t,:]*self.cycle[None,self.tier==t,None]).sum(axis=(1,2)) for t in ['G','D','K']],axis=1)
        odservice=np.einsum('ash,sw->awh',N,self.serve.astype(float),optimize=False)
        structural=(pathgap<1e-8)&np.all(fleet<=self.fleet[None]+1e-8,axis=1)&np.all(odservice>=self.odfloor[None]-1e-8,axis=(1,2))
        structural &= np.all(N[:,self.fixed,:]==self.N0[None,self.fixed,:],axis=(1,2))&np.all((N>=self.Nmin[None])&(N<=self.Nmax[None]),axis=(1,2))
        structural &= np.all(N[:,self.adjustable,:].sum(axis=2)>=1,axis=1)
        violations=np.maximum(maxlf-self.lam,0)+np.maximum(self.eta_floor-eta,0)+np.maximum(-profit-self.budget,0)/max(1.,abs(self.c['reference_revenue']))+np.where(structural,0,100)
        feasible=structural&(maxlf<=self.lam+1e-9)&(eta>=self.eta_floor-1e-9)&(profit>=-self.budget-1e-6)
        out=dict(profit=profit,welfare=welfare,U=U,revenue=revenue,cost=cost,eta=eta,maxlf=maxlf,violation=violations,feasible=feasible,structural=structural)
        if details:
            # Realized cost ratio diagnostic, including all modes and own VOT.
            timecost=(self.alpha[None]-v)/self.beta[None,None,:,None,0,None,None]
            timecost=np.where(valid,timecost,0.) # equals monetary + nonmonetary cost net of comfort/flex
            # Remove comfort/flex from generalized COST, as in eq:generalized_cost.
            comfort=np.array([p['comfort'] for p in self.c['products']]); flex=np.where(self.tier=='K',1.,2.)
            gcrail=timecost+(self.beta[None,None,:,None,7,None,None]*comfort[None,None,None,None,:,:]+self.beta[None,None,:,None,8,None,None]*flex[None,None,None,None,:,None])/self.beta[None,None,:,None,0,None,None]
            gcr=np.sum(ps[...,None]*pb*gcrail,axis=(4,5))
            gcroad=(np.einsum('kj,wij->wki',self.beta[:,:7],self.road[:,:,:7])/self.beta[None,:,0,None])[:,:,None,:]
            gp=np.sum(self.road_probs*gcroad[:,:,:,1:],axis=-1)
            gn=pm[...,0]*gcr+pm[...,1]*gp[None]+pm[...,2]*gcroad[None,:,:,:,0]
            Q=self.qbar[None]*part
            gmean=(Q*gn).sum(axis=2)/np.maximum(Q.sum(axis=2),1e-20)
            G=(gn/gmean[:,:,None,:]).max(axis=2)
            out.update(qr=qr,participation=part,mode_probs=pm,Q=Q,q0=self.qbar[None]-Q,G=G,loads=loads,paths=paths,fleet=fleet,odservice=odservice)
        return out

    def record(self,N,phi,objective,policy,meta=None):
        fare_active=N.copy()
        for s,parent in self.parent.items(): fare_active[parent]+=N[s]
        phi=np.where(fare_active[:,:,None]>0,phi,0.)
        m=self.evaluate(N,phi,True); d={k:float(v[0]) if np.asarray(v).ndim==1 else v[0] for k,v in m.items()}
        d['feasible']=bool(m['feasible'][0]); d['structural']=bool(m['structural'][0])
        qr=d.pop('qr'); Q=d['Q']; pm=d['mode_probs']
        d['rail_by_od']=qr.sum(axis=(1,2,3,4)); d['rail_by_class']=qr.sum(axis=(0,2,3,4))
        d['tier_by_class']={t:qr[:,:,:,self.tier==t,:].sum(axis=(0,2,3,4)) for t in ['G','D','K']}
        premium=np.array([p['premium'] for p in self.c['products']],bool)
        d['premium_by_class']=(qr*premium[None,None,None,:,:]).sum(axis=(0,2,3,4))
        d['class_trips']=Q.sum(axis=(0,2)); d['class_potential']=self.qbar.sum(axis=(0,2))
        d['mode_trips']=(Q[...,None]*pm).sum(axis=(0,1,2))
        d['rail_revenue_by_product']=(qr*self.fare[:,None,None,:,:]*phi.transpose(1,0,2)[None,None,:,:,:]).sum(axis=(0,1,2,4))
        d['seat_by_class']=qr.sum(axis=(0,2,3))
        d['product_by_class']=qr.sum(axis=(0,2,4))
        d['consumer_surplus_change']=d['U']-self.state_U
        d['path_utilization']=float(np.max(d['paths']/self.cap))
        d['fleet_utilization']=(d['fleet']/self.fleet)
        service_N=N.copy()
        for s,parent in self.parent.items(): service_N[parent]+=N[s]; service_N[s]=0
        den=service_N[:,:,None,None]*self.seats[:,None,:,None]; lf=np.divide(d['loads'],den,out=np.zeros_like(d['loads']),where=den>0)
        d['peak_load_index']=list(map(int,np.unravel_index(np.argmax(lf),lf.shape)))
        d['budget']=self.budget
        d['Gmax']=float(d['G'].max()); d['Gmean']=float(np.average(d['G'],weights=Q.sum(axis=1)))
        d.update(N=N,phi=phi,authority_share=self.authority,objective=objective,policy=policy,case_id=self.c['id'],income=self.income,electric=self.electric,spec=self.spec,version=VERSION,evaluations=self.evaluations,meta=meta or {})
        d['objective_value']=d[objective]
        return d

def choose(m,objective):
    ok=m['feasible']; z=m[objective]
    if ok.any():
        ids=np.flatnonzero(ok); return int(ids[np.argmax(z[ids])])
    best=np.min(m['violation']); ids=np.flatnonzero(m['violation']<=best+1e-12)
    return int(ids[np.argmax(z[ids])])

def solve(model,objective,policy,seeds=(),rounds=4,step=.025):
    start=time.perf_counter(); S=model.S
    policy_actual=policy
    # Through-service K hard seats/sleepers anchor the whole product multiplier.
    fare_coords=[(s,h,b) for s in range(S) if model.adjustable[s] for h in range(4) if model.Nmax[s,h]>0 for b in (range(3) if policy=='P3-sb' else [0]) if model.seats[s,b]>0] if policy not in ['P0','P2'] else []
    freq_coords=[(s,h) for s in range(S) if (model.freq_adjustable[s] or (policy=='P4' and model.candidate[s])) for h in range(4)] if policy in ['P2','P3','P4','P3-sb'] else []
    grid=np.round(np.arange(.8,model.fare_cap+step/2,step),8)
    def key(N,phi):
        m=model.evaluate(N,phi); return (int(m['feasible'][0]),-float(m['violation'][0]) if not m['feasible'][0] else 0.,float(m[objective][0]))
    starts=[(model.N0.copy(),np.ones((S,4,3)))]
    for rec in seeds:
        N=np.array(rec['N'],float); ph=np.array(rec['phi'],float)
        if policy!='P4': N[model.candidate]=0
        if policy in ['P0','P1']: N=model.N0.copy()
        N=np.clip(N,model.Nmin,model.Nmax)
        if policy in ['P0','P2']: ph[:]=1
        ph=np.where(N[:,:,None]>0,ph,1.)
        if policy!='P3-sb': ph=np.repeat(ph[:,:,:1],3,axis=2)
        ph[model.tier=='K']=1.
        ph[model.tier!='K']=np.clip(.8+np.round((ph[model.tier!='K']-.8)/step)*step,.8,model.fare_cap)
        starts.append((N,ph))
    if policy not in ['P0','P2']:
        for value in [.8,model.fare_cap]:
            ph=np.ones((S,4,3)); ph[model.tier!='K']=value; starts.append((model.N0.copy(),ph))
    if freq_coords:
        for factor in [.65,.85,1.15]:
            nt=model.N0.copy(); nt[model.adjustable]=np.rint(nt[model.adjustable]*factor); nt=np.clip(nt,model.Nmin,model.Nmax)
            starts.append((nt,np.ones((S,4,3))))
    # Stable, deterministic initial selection; original design first resolves ties.
    N,phi=max(starts,key=lambda x:key(*x)); N=N.copy(); phi=phi.copy()
    phi[model.tier=='K']=1.
    if policy_actual=='P0': return model.record(N,phi,objective,policy,{'seconds':time.perf_counter()-start,'rounds':0,'local_stable':True,'equivalent_to':'P0'})
    history=[]
    def optimize_N(coords,neighborhood=False):
        nonlocal N,phi
        vals=[]
        for s,h in coords:
            if neighborhood: val=sorted(set([max(model.Nmin[s,h],N[s,h]-1),N[s,h],min(model.Nmax[s,h],N[s,h]+1)]))
            else: val=sorted(set([N[s,h],*range(int(model.Nmin[s,h]),int(model.Nmax[s,h])+1)]))
            vals.append(val)
        combos=list(itertools.product(*vals))
        if len(combos)>20000: raise ValueError('Block exceeds enumeration cap')
        nb=np.broadcast_to(N,(len(combos),S,4)).copy()
        for i,(s,h) in enumerate(coords): nb[:,s,h]=np.array(combos)[:,i]
        m=model.evaluate(nb,phi); j=choose(m,objective)
        if key(nb[j],phi)>key(N,phi): N=nb[j].copy(); return True
        return False
    def optimize_phi(coords,neighborhood=False):
        nonlocal N,phi
        vals=[]
        for s,h,b in coords:
            val=sorted(set([phi[s,h,b],*grid]))
            if neighborhood: val=[v for v in val if abs(v-phi[s,h,b])<=step+1e-8]
            vals.append(val)
        combos=list(itertools.product(*vals)); pb=np.broadcast_to(phi,(len(combos),S,4,3)).copy()
        for i,(s,h,b) in enumerate(coords):
            if policy=='P3-sb': pb[:,s,h,b]=np.array(combos)[:,i]
            else: pb[:,s,h,:]=np.array(combos)[:,i,None]
        m=model.evaluate(N,pb); j=choose(m,objective)
        if key(N,pb[j])>key(N,phi): phi=pb[j].copy(); return True
        return False
    for r in range(rounds):
        changed=False
        for coord in freq_coords: changed=optimize_N([coord]) or changed
        for coord in fare_coords: changed=optimize_phi([coord]) or changed
        history.append(key(N,phi))
        if not changed: break
    # Radius-one blocks: adjacent products in a period, and periods of a product.
    blocks=[]
    for h in range(4):
        ns=[x for x in freq_coords if x[1]==h]
        fs=[x for x in fare_coords if x[1]==h]
        blocks.extend([('N',ns[i:i+2]) for i in range(0,len(ns),2)])
        blocks.extend([('F',fs[i:i+2]) for i in range(0,len(fs),2)])
    for s in range(S):
        ns=[x for x in freq_coords if x[0]==s]; fs=[x for x in fare_coords if x[0]==s]
        blocks.extend([('N',ns[i:i+2]) for i in range(0,len(ns),2)])
        blocks.extend([('F',fs[i:i+2]) for i in range(0,len(fs),2)])
    stable=False; polish=0
    for p in range(16):
        changed=False
        for kind,coords in blocks:
            if coords: changed=(optimize_N(coords,True) if kind=='N' else optimize_phi(coords,True)) or changed
        polish=p+1
        if not changed: stable=True; break
    phi[model.tier=='K']=1.
    return model.record(N,phi,objective,policy,{'seconds':time.perf_counter()-start,'rounds':len(history),'polish_passes':polish,'local_stable':stable,'blocks':len(blocks),'cap':20000,'history':history,'equivalent_to':policy_actual})
