"""Independent scalar implementation of equations in Section 3.

Does not call Model.evaluate. Recomputes utilities, each nested probability,
flows, revenue, costs, capacity, retention and welfare from saved decisions.
"""
import hashlib,json,math,time
from pathlib import Path
import numpy as np
from model import ROOT,INCOMES,VERSION,dump

def lse(values,scale):
    if not values: return -1e100
    peak=max(values); return peak+scale*math.log(sum(math.exp((v-peak)/scale) for v in values))

def scalar(c,N,phi,income,electric,spec):
    service_N=N.copy()
    for s,p in enumerate(c['products']):
        if p['candidate']:
            parent=next(i for i,x in enumerate(c['products']) if x['id']==p['parent'])
            service_N[parent]+=N[s]; service_N[s]=0
    W=len(c['ods']); S=len(c['products']); qr=np.zeros((W,3,4,S,3)); Q=np.zeros((W,3,4)); q0=np.zeros_like(Q); pm=np.zeros((W,3,4,3)); U=0.; G=np.zeros((W,4)); generalized=np.zeros_like(Q)
    shares=np.array(spec.get('class_shares',[.2,.6,.2])); qbar=np.array(c['qbar'])*spec.get('demand',1.)*shares[None,:,None]/np.array([.2,.6,.2])[None,:,None]
    dy=INCOMES[income] if income in INCOMES else np.array(spec['dy']); musc=spec.get('mu_sc',.3); mupr=spec.get('mu_pr',.45)
    revenue=0.; cost=0.; loads=np.zeros((S,4,3,len(c['path_capacity'][0])))
    for w in range(W):
        for k in range(3):
            beta=np.array(c['beta'][k],float); beta[0]*=math.exp(-[.7,.8,.9][k]*dy[k])
            for h in range(4):
                seats=[]; productvals=[]; active=[]
                for s,p in enumerate(c['products']):
                    if not p['serve'][w] or service_N[s,h]<=0: continue
                    valid=[]; utilities=[]; costs=[]
                    for b in range(3):
                        if p['seats'][b]<=0: continue
                        fare=p['fare'][w][b]*phi[s,h,b]*(spec.get('k_fare',1.) if p['tier']=='K' else 1.)
                        iv=p['runtime'][w]*(spec.get('k_time',1.) if p['tier']=='K' else 1.)
                        displacement=15*[3,8,3,10][h]/service_N[s,h]
                        if spec.get('displacement_cap') is not None:displacement=min(displacement,spec['displacement_cap'])
                        attr=np.array([fare+c['access'][w][1],iv,c['access'][w][0],10.,displacement,iv*{'G':.02,'D':.03,'K':.08}[p['tier']],0.,p['comfort'][b],1. if p['tier']=='K' else 2.])
                        utility=c['alpha'][w][k][h][s][b]-sum(beta[j]*attr[j] for j in range(7))+sum(beta[j]*attr[j] for j in [7,8])
                        valid.append(b); utilities.append(utility); costs.append(sum(beta[j]*attr[j] for j in range(7))/beta[0])
                    ls=lse(utilities,musc); active.append(s); productvals.append(ls); seats.append((valid,utilities,costs))
                rail=lse(productvals,mupr)
                roadU=[]; roadcost=[]
                for i,a in enumerate(c['road'][w]):
                    attr=list(a); scale=spec.get('electric_scale',1.)
                    if electric!='none':
                        if i==0: attr[0]-=.58*c['road_km'][w]*.5*scale/c['occupancy']
                        affected=[2,3] if electric.startswith('am') else ([1,2,3] if electric.startswith('all') else [])
                        if i in affected: attr[0]-=[0,.12,.2,.3][i]*c['road_km'][w]*(.3 if electric.endswith('low') else .7)*scale
                    utility=c['road_alpha'][w][k][h][i]-sum(beta[j]*attr[j] for j in range(7))+sum(beta[j]*attr[j] for j in [7,8])
                    roadU.append(utility); roadcost.append(sum(beta[j]*attr[j] for j in range(7))/beta[0])
                road=lse(roadU[1:],.5); mode=[rail,road,roadU[0]]; travel=lse(mode,.75)
                part=1/(1+math.exp(-travel)); Q[w,k,h]=qbar[w,k,h]*part; q0[w,k,h]=qbar[w,k,h]-Q[w,k,h]
                pm[w,k,h]=[math.exp((v-travel)/.75) for v in mode]
                U+=qbar[w,k,h]*math.log1p(math.exp(travel))/beta[0]
                gn=pm[w,k,h,2]*roadcost[0]+pm[w,k,h,1]*sum(math.exp((roadU[i]-road)/.5)*roadcost[i] for i in range(1,4))
                for j,s in enumerate(active):
                    p=c['products'][s]; sp=math.exp((productvals[j]-rail)/mupr); bs,vals,gcs=seats[j]
                    for b,val,gc in zip(bs,vals,gcs):
                        prob=pm[w,k,h,0]*sp*math.exp((val-productvals[j])/musc); flow=Q[w,k,h]*prob; qr[w,k,h,s,b]=flow
                        revenue+=flow*p['fare'][w][b]*phi[s,h,b]*(spec.get('k_fare',1.) if p['tier']=='K' else 1.)
                        loads[s,h,b]+=flow*np.array(p['pax'][w]); gn+=prob*gc
                generalized[w,k,h]=gn
    for s,p in enumerate(c['products']):
        factor=spec.get('k_cost',1.) if p['tier']=='K' else 1.
        cost+=N[s].sum()*p['run_cost']*factor
        retained=N[s].sum()>0 if p['candidate'] else service_N[s].sum()>0
        if retained: cost+=p['fixed_cost']*factor*(spec.get('k_restart',1.) if p['candidate'] else 1.)
    for w in range(W):
        for h in range(4):
            denom=sum(Q[w,k,h]*generalized[w,k,h] for k in range(3))/max(sum(Q[w,:,h]),1e-20)
            G[w,h]=max(generalized[w,:,h])/denom
    seats=np.array([p['seats'] for p in c['products']]); denom=service_N[:,:,None,None]*seats[:,None,:,None]
    loads+=c['background_fraction']*np.array([p['N0'] for p in c['products']])[:,:,None,None]*seats[:,None,:,None]*np.array([p['route'] for p in c['products']])[:,None,None,:]
    lf=np.divide(loads,denom,out=np.zeros_like(loads),where=denom>0)
    return dict(profit=revenue-cost,revenue=revenue,cost=cost,U=U,Q=Q,q0=q0,qr=qr,mode_probs=pm,maxlf=float(lf.max()),G=G)

def verify_all():
    start=time.perf_counter(); cases={ci:json.loads((ROOT/'inputs'/f'{ci}.json').read_text(encoding='utf-8')) for ci in ['HN','WC','JX']}; cache={}; refcache={}; results=[]; failures=[]; totals=0; maxerrors={}
    for path in sorted((ROOT/'runs').glob('E*/*.json')):
        from calibration import prepare
        group=json.loads(path.read_text(encoding='utf-8')); c=prepare(cases[group['job']['case']],group['job'].get('spec',{}))
        if group['version']!=VERSION: failures.append((str(path),'stale_version')); continue
        if hashlib.sha256((ROOT/'inputs'/f"{c['id']}.json").read_bytes()).hexdigest()!=group['fingerprint']: failures.append((str(path),'fingerprint'))
        if hashlib.sha256((ROOT/'model.py').read_bytes()).hexdigest()!=group['solver_sha256']: failures.append((str(path),'solver_hash'))
        controller=group.get('controller_file','run_experiments.py')
        if hashlib.sha256((ROOT/controller).read_bytes()).hexdigest()!=group['controller_sha256']: failures.append((str(path),'controller_hash'))
        if hashlib.sha256((ROOT/'calibration.py').read_bytes()).hexdigest()!=group['calibration_sha256']: failures.append((str(path),'calibration_hash'))
        for r in group['records']+[b['record'] for b in group.get('budgets',[])]:
            totals+=1; N=np.array(r['N']); phi=np.array(r['phi']); spec=r['spec']; refkey=json.dumps([c['id'],spec],sort_keys=True)
            if refkey not in refcache:
                N0=np.array([p['N0'] for p in c['products']],float); refcache[refkey]=scalar(c,N0,np.where(N0[:,:,None]>0,1.,0.)*np.ones((len(N0),4,3)),'reference','none',spec)
            base=refcache[refkey]; statekey=json.dumps([c['id'],r['income'],r['electric'],spec],sort_keys=True)
            if statekey not in refcache:
                N0=np.array([p['N0'] for p in c['products']],float); refcache[statekey]=scalar(c,N0,np.where(N0[:,:,None]>0,1.,0.)*np.ones((len(N0),4,3)),r['income'],r['electric'],spec)
            state=refcache[statekey]; key=json.dumps([statekey,r['N'],r['phi']])
            if key not in cache: cache[key]=scalar(c,N,phi,r['income'],r['electric'],spec)
            actual=cache[key]; errors={k:float(np.max(abs(np.array(r[k])-actual[k]))) for k in ['profit','revenue','cost','U','Q','q0','mode_probs','maxlf','G']}
            errors['welfare']=abs(r['welfare']-(actual['U']-state['U']+actual['profit']-state['profit']))
            retention_base=state if spec.get('same_state',False) else base
            errors['eta']=abs(r['eta']-actual['Q'][:,2,:].sum()/retention_base['Q'][:,2,:].sum())
            qbar=np.array(c['qbar'])*spec.get('demand',1.)*np.array(spec.get('class_shares',[.2,.6,.2]))[None,:,None]/np.array([.2,.6,.2])[None,:,None]
            # Road demand plus rail demand reconstruct realized flow independently.
            railtotal=actual['qr'].sum(axis=(3,4)); roadtotal=actual['Q']*(actual['mode_probs'][...,1]+actual['mode_probs'][...,2])
            errors['conservation']=float(np.max(abs(actual['q0']+railtotal+roadtotal-qbar)))
            errors['integer_frequency']=float(np.max(abs(N-N.round())))
            allk=np.array([not p['candidate'] and p['tier']=='K' for p in c['products']]); withdraw=spec.get('k_withdraw',0.); obs=allk&(withdraw==0); N0=np.array([p['N0'] for p in c['products']],float); errors['fixed_frequency']=float(np.max(abs(N[obs]-N0[obs]),initial=0))
            errors['K_withdraw_bounds']=float(max(np.max(np.maximum(np.ceil((1-withdraw)*N0[allk])-N[allk],0),initial=0),np.max(np.maximum(N[allk]-N0[allk],0),initial=0)))
            gd=np.array([not p['candidate'] and p['tier']!='K' for p in c['products']]); authority=spec.get('authority',.5)
            floor=np.ceil((1-authority)*N0[gd]); upper=np.maximum(2,N0[gd]+np.floor(authority*N0[gd])) if authority>0 else N0[gd]
            errors['protected_departures']=float(np.max(np.maximum(floor-N[gd],0),initial=0)); errors['frequency_upper']=float(np.max(np.maximum(N[gd]-upper,0),initial=0))
            candidate=np.array([p['candidate'] for p in c['products']]); caps=np.array([p['Nmax'] for p in c['products']])
            if spec.get('active_period_K',False):
                for s,p in enumerate(c['products']):
                    if p['candidate']:
                        parent=next(i for i,x in enumerate(c['products']) if x['id']==p['parent']);caps[s,N0[parent]==0]=0
            errors['candidate_upper']=float(np.max(np.maximum(N[candidate]-caps[candidate],0),initial=0)); errors['negative_frequency']=float(np.max(np.maximum(-N,0),initial=0))
            if r['policy']!='P4': errors['candidate_policy']=float(np.max(N[candidate],initial=0))
            if r['policy'] in ['P0','P1']: errors['fixed_timetable_policy']=float(np.max(abs(N-N0)))
            if r['policy'] in ['P0','P2']: errors['fixed_fare_policy']=float(np.max(abs(phi[N>0]-1),initial=0))
            active=N>0; kt=np.array([p['tier']=='K' for p in c['products']]); errors['fixed_K_tariff']=float(np.max(abs(phi[kt][active[kt]]-1),initial=0))
            fare_active=active.copy()
            for s,p in enumerate(c['products']):
                if p['candidate']:
                    parent=next(i for i,x in enumerate(c['products']) if x['id']==p['parent'])
                    fare_active[parent]|=active[s]
            errors['inactive_fare']=float(np.max(abs(phi[~fare_active]),initial=0))
            step=spec.get('step',.025); free=np.repeat((active&~kt[:,None])[:,:,None],3,axis=2)
            errors['fare_menu']=float(np.max(abs((phi[free]-.8)/step-np.round((phi[free]-.8)/step)),initial=0))
            errors['fare_band']=float(max(np.max(np.maximum(.8-phi[free],0),initial=0),np.max(np.maximum(phi[free]-spec.get('fare_cap',1.2),0),initial=0)))
            if r['policy']!='P3-sb': errors['common_fare']=float(np.max(abs(phi[:,:,1:]-phi[:,:,:1]),initial=0))
            route=np.array([p['route'] for p in c['products']]); paths=np.einsum('sh,se->he',N,route)
            fleet=[]
            for t in ['G','D','K']:
                fleet.append(sum(N[s].sum()*((p['cycle']-1)*spec.get('k_time',1.)+1 if t=='K' else p['cycle']) for s,p in enumerate(c['products']) if p['tier']==t))
            odservice=np.einsum('sh,sw->wh',N,np.array([p['serve'] for p in c['products']],int))
            struct=np.all(paths<=np.array(c['path_capacity'])*spec.get('capacity',1.)+1e-8) and np.all(np.array(fleet)<=np.array(c['fleet_hours'])*spec.get('fleet_scale',1.)+1e-8) and np.all(odservice>=np.array(c['od_floor'])-1e-8) and np.all(N[gd]>=floor) and np.all(N[gd]<=upper) and np.all(N[obs]==N0[obs]) and np.all(N[gd].sum(axis=1)>=1) and errors['K_withdraw_bounds']<1e-8
            fea=struct and actual['maxlf']<=spec.get('lambda',.95)+1e-9 and actual['Q'][:,2,:].sum()/retention_base['Q'][:,2,:].sum()>=spec.get('eta',.95)-1e-9 and actual['profit']>=-r['budget']-1e-6
            if fea!=r['feasible']: errors['feasibility_flag']=1.
            bad={k:v for k,v in errors.items() if v>(1e-5 if k in ['profit','revenue','cost','U','welfare'] else 1e-7)}
            if bad: failures.append((str(path),r['objective'],r['policy'],bad))
            for k,v in errors.items(): maxerrors[k]=max(maxerrors.get(k,0),v)
        # Nested policy dominance is meaningful only among feasible designs.
        for obj in ['profit','welfare']:
            rs={r['policy']:r for r in group['records'] if r['objective']==obj}
            for a,b in [('P0','P1'),('P0','P2'),('P1','P3'),('P2','P3'),('P3','P4'),('P3','P3-sb')]:
                if a in rs and b in rs and rs[a]['feasible']:
                    if not rs[b]['feasible'] or rs[b]['objective_value']<rs[a]['objective_value']-1e-5: failures.append((str(path),'dominance',obj,a,b))
    report=dict(records=totals,unique_scalar_designs=len(cache),maximum_errors=maxerrors,failures=failures,seconds=time.perf_counter()-start,passed=not failures)
    dump(ROOT/'verification.json',report); print(json.dumps({**report,'failures':failures[:20]},ensure_ascii=False,indent=2)); return report

if __name__=='__main__': verify_all()
