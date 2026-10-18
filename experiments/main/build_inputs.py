"""Reconstruct observable corridor stopping signatures; archive calibrated inputs.

No global train origins/destinations, true rail kilometrage, occupancy or corridor
cost allocation are contained in the source snapshots. Those quantities must not
be described as observed. All observed frequencies are fixed (author instruction).
"""
import csv, hashlib, json, math, copy
from collections import defaultdict
from pathlib import Path
import numpy as np
from model import Model, dump, ROOT

OLD=ROOT.parents[1]/'data'/'corridors'
IDS={'HN':'hangzhou_nanjing','WC':'wuhan_changsha','JX':'jiangxi_ganzhou_ji_an_nanchang_jiujiang'}
SEATS={'G':['商务座','一等座','二等座'],'D':['一等座','二等座'],'K':['硬座','硬卧','软卧']}

def period(t):
    h=int(t.split(':')[0]); return 0 if 6<=h<9 else 1 if 9<=h<17 else 2 if 17<=h<20 else 3
def tier(code): return 'G' if code.startswith(('G','C')) else 'D' if code.startswith('D') else 'K'
def readcsv(p): return list(csv.DictReader(p.open(encoding='utf-8-sig',newline='')))

def build(short,slug):
    source=OLD/slug; old=json.loads((source/'case'/'pattern_case.json').read_text(encoding='utf-8'))
    raw=source/'raw_data'; tp=raw/f'{slug}_trains_20260805.csv'; pp=raw/f'{slug}_prices_20260805.csv'
    trains=readcsv(tp); prices=readcsv(pp); cities=old['sets']['cities']; ods=old['sets']['ods']; W=len(ods)
    endpoints=[od.split('-') for od in ods]; roads=old['attributes']['road_by_od']
    bytrain=defaultdict(list)
    for row in trains:
        od=row['od_origin']+'-'+row['od_dest']
        if od in ods: bytrain[row['train_no']].append(row)
    groups=defaultdict(list)
    for code,rows in bytrain.items():
        sig=tuple(sorted({ods.index(r['od_origin']+'-'+r['od_dest']) for r in rows}))
        groups[(tier(code),sig)].append((code,rows))
    products=[]; E=2*(len(cities)-1)
    load=old['calibration']['load_factor']
    for ti in ['G','D','K']:
        for idx,((t,sig),members) in enumerate(sorted(groups.items(),key=lambda x:str(x[0]))):
            if t!=ti: continue
            no=sum(p['tier']==t for p in products)+1
            a=min(cities.index(endpoints[w][0]) for w in sig); b=max(cities.index(endpoints[w][1]) for w in sig)
            line_offset=0 if t in ['G','D'] else len(cities)-1
            route=[0]*E
            for e in range(a,b): route[line_offset+e]=1
            pax=np.zeros((W,E))
            for w in sig:
                i,j=[cities.index(x) for x in endpoints[w]]
                pax[w,line_offset+i:line_offset+j]=1
            nf=[0]*4
            for code,rows in members:
                # One departure per unique train; period at earliest modeled boarding city.
                first=min(rows,key=lambda r:cities.index(r['od_origin'])); nf[period(first['start_time'])]+=1
            fares=np.zeros((W,3)); runtime=np.zeros(W)
            for w in sig:
                rr=[r for r in prices if r['train_code'] in {m[0] for m in members} and r['od_origin']+'-'+r['od_dest']==ods[w]]
                for si,seat in enumerate(SEATS[t]):
                    values=[float(r[seat]) for r in rr if r.get(seat)]
                    fares[w,si]=np.median(values) if values else old['attributes']['rail_fare'].get(ods[w],{}).get(t,{}).get(seat,0.)
                    if fares[w,si]<=0:
                        # Explicit inherited seat-ratio imputation, never claimed observed.
                        vals=old['attributes']['rail_fare'].get(ods[w],{}).get(t,{})
                        base=vals.get('二等座',vals.get('硬座',min(vals.values()) if vals else 50.))
                        fares[w,si]=base*({'商务座':3.5,'一等座':1.6,'二等座':1.,'硬座':1.,'硬卧':2.,'软卧':3.}[seat])
                rs=[r for _,rows in members for r in rows if r['od_origin']+'-'+r['od_dest']==ods[w]]
                runtime[w]=np.median([int(r['duration'].split(':')[0])*60+int(r['duration'].split(':')[1]) for r in rs])
            caps=[old['products'][t]['seat_capacity'].get(s,0) for s in SEATS[t]]
            if t=='D': caps.append(0)
            comfort=[old['products'][t]['seat_comfort'].get(s,0) for s in SEATS[t]]
            if t=='D': comfort.append(0)
            km=sum(old['network']['segment_lengths_km'][list(old['network']['segments'])[e]] for e in range(a,b))
            cycle=2*float(max(runtime))/60+1.
            p=dict(id=f'{t}{no:02d}',tier=t,candidate=False,source_trains=[m[0] for m in members],serve=[w in sig for w in range(W)],route=route,pax=pax.tolist(),N0=nf,Nmax=nf,seats=caps,comfort=comfort,premium=[t=='G',t in ['G','D'],False] if t=='G' else ([True,False,False] if t=='D' else [False,False,False]),fare=fares.tolist(),runtime=runtime.tolist(),cycle=cycle,length_proxy_km=km,run_cost=old['costs']['per_run'][t]+old['costs']['per_train_km'][t]*km,fixed_cost=0.)
            products.append(p)
    # Observed cost commitments are shared across the signature families.
    for t in ['G','D','K']:
        ps=[p for p in products if p['tier']==t]
        total=sum(sum(p['N0']) for p in ps)
        for p in ps: p['fixed_cost']=old['costs']['fixed_per_product_day'][t]*sum(p['N0'])/total if total else 0
    for p in list(products):
        if p['tier']=='K':
            c=copy.deepcopy(p); c.update(id='C'+p['id'],candidate=True,parent=p['id'],source_trains=[],N0=[0]*4,Nmax=[max(1,int(math.ceil(1.5*n))) for n in p['N0']],fixed_cost=.1*p['fixed_cost'])
            products.append(c)
    S=len(products); qrail=np.zeros((W,4,S,3))
    # Allocate each product's seats among its served ODs with inverse-distance weights,
    # normalized by its busiest segment, then apply a single corridor load rescale.
    for s,p in enumerate(products):
        if p['candidate']: continue
        weights=np.array([1/max(1,roads[od]['distance_km']) if p['serve'][w] else 0 for w,od in enumerate(ods)])
        norm=max(np.array(p['pax']).T@weights)
        weights/=norm
        qrail[:,:,s,:]=weights[:,None,None]*np.array(p['N0'])[None,:,None]*np.array(p['seats'])[None,None,:]*load[p['tier']]
    rescale=.92/max(load[p['tier']] for p in products if not p['candidate'])
    qrail*=rescale
    shares=np.array([.70 if roads[od]['distance_km']<=350 else .60 if roads[od]['distance_km']<=500 else .55 if roads[od]['distance_km']<=800 else .45 for od in ods])
    # No-train periods have no observable market-size anchor; potential demand zero.
    qbar=qrail.sum(axis=(2,3))[:,None,:]/shares[:,None,None]/.85*np.array([.2,.6,.2])[None,:,None]
    beta=np.array([[old['utility']['by_class'][k][key] for key in ['beta_c','beta_iv','beta_ac','beta_wt','beta_sc','beta_rel','beta_tr','gamma_com','gamma_flex']] for k in old['sets']['classes']])
    access=np.array([[old['attributes']['access_by_city'][a]['time_min']+old['attributes']['access_by_city'][b]['time_min'],old['attributes']['access_by_city'][a]['fare']+old['attributes']['access_by_city'][b]['fare']] for a,b in endpoints])
    road=[]
    for od in ods:
        r=roads[od]; at=r['auto_duration_min']; ct=r['coach_duration_min']
        road.append([[r['private_auto_cost'],at,0,0,0,.05*at,0,3,2],[r['coach_fare'],ct,18,30,15,.08*ct,0,2,1],[r['maas_fare'],at*1.1,10,15,5,.06*at*1.1,0,3,3],[r['business_van_fare'],at*1.02,5,5,0,.04*at*1.02,0,4,3]])
    N=np.array([p['N0'] for p in products]); route=np.array([p['route'] for p in products]); paths=np.einsum('sh,se->he',N,route)
    # 16 paths/hour or reference use plus reserve, whichever is larger; net resource
    # availability is a stylized feasible envelope, never an observed line capacity.
    pathcap=np.maximum(np.array([3,8,3,10])[:,None]*16,paths+4)
    fleet=[math.ceil(sum(sum(p['N0'])*p['cycle'] for p in products if p['tier']==t)/24)*24+sum(sum(p['Nmax'])*p['cycle'] for p in products if p['tier']==t and p['candidate']) for t in ['G','D','K']]
    od_floor=np.minimum(1,np.einsum('sh,sw->wh',N,np.array([p['serve'] for p in products],int)))
    c=dict(id=short,source_slug=slug,cities=cities,ods=ods,products=products,qbar=qbar.tolist(),beta=beta.tolist(),access=access.tolist(),road=road,road_km=[roads[od]['distance_km'] for od in ods],rail_share_targets=shares.tolist(),alpha=np.zeros((W,3,4,S,3)).tolist(),road_alpha=np.zeros((W,3,4,4)).tolist(),path_capacity=pathcap.tolist(),fleet_hours=fleet,od_floor=od_floor.tolist(),reference_profit=0.,reference_revenue=1.,reference_U=0.,calibration_rescale=rescale,snapshot_collection_dates=sorted({json.loads(p.read_text(encoding='utf-8')).get('collected_at_utc','unknown') for p in raw.glob('*rail_raw_*.json')}),source_hashes={str(p.relative_to(OLD)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [tp,pp,source/'case'/'pattern_case.json']})
    model=Model(c); desired=np.zeros((W,3,4,S,3)); alpha=np.zeros_like(desired)
    for w in range(W):
        for h in range(4):
            R=qrail[w,h].sum()
            # travel inclusive utility log(.85/.15) with zero upper intercepts.
            modeV=np.log(.85/.15)+.75*np.log(shares[w])
            for s,p in enumerate(products):
                qs=qrail[w,h,s].sum()
                if qs<=0: continue
                target=modeV+.45*np.log(qs/max(R,1e-20))+.30*np.log(np.maximum(qrail[w,h,s]/qs,1e-100))
                for k in range(3):
                    sched=15*[3,8,3,10][h]/p['N0'][h]
                    rawU=model.fixed_rail[w,k,0,s]-beta[k,0]*model.fare[w,s]-beta[k,4]*sched
                    alpha[w,k,h,s]=target-rawU
    for s,p in enumerate(products):
        if p['candidate']:
            parent=next(i for i,x in enumerate(products) if x['id']==p['parent']); ns=np.array(products[parent]['N0']); active=np.flatnonzero(ns)
            for h in range(4):
                near=h if ns[h]>0 else int(active[np.argmin(abs(active-h))])
                alpha[:,:,h,s]=alpha[:,:,near,parent]-.45*np.log(max(1,ns[near]))
        else:
            active=np.flatnonzero(p['N0'])
            for h in range(4):
                if p['N0'][h]==0:
                    near=int(active[np.argmin(abs(active-h))]); alpha[:,:,h,s]=alpha[:,:,near,s]
    c['alpha']=alpha.tolist()
    ra=np.zeros((W,3,4,4)); road=np.array(road)
    rawU=-np.einsum('kj,wij->wki',beta[:,:7],road[:,:,:7])+np.einsum('kj,wij->wki',beta[:,7:],road[:,:,7:])
    for w in range(W):
        mode_auto=np.log(.85/.15)+.75*np.log((1-shares[w])*.4)
        mode_road=np.log(.85/.15)+.75*np.log((1-shares[w])*.6)
        target=np.array([mode_auto,*list(mode_road+.5*np.log([.75,.22,.03]))])
        ra[w]=target[None,None,:]-rawU[w,:,None,:]
    c['road_alpha']=ra.tolist()
    model=Model(c); m=model.evaluate(model.N0,np.ones((S,4,3)),True)
    revenue=float(m['revenue'][0]); cost=float(m['cost'][0]); factor=.92*revenue/cost
    for p in c['products']: p['run_cost']*=factor; p['fixed_cost']*=factor
    c['reference_revenue']=revenue; c['reference_profit']=.08*revenue; c['reference_U']=float(m['U'][0]); c['cost_rescale']=factor
    model=Model(c); check=model.record(model.N0,np.ones((S,4,3)),'profit','P0')
    actual=model.evaluate(model.N0,np.ones((S,4,3)),True)
    err=float(np.max(abs(actual['qr'][0].sum(axis=1)-qrail)))
    check_summary=dict(case_id=short,products=S,observed_products=sum(not p['candidate'] for p in products),candidate_patterns=sum(p['candidate'] for p in products),reference_departures={t:int(N[np.array([p['tier']==t for p in products])].sum()) for t in ['G','D','K']},adjustable_reference_departures=0,max_target_flow_error=err,participation_error=float(np.max(abs(actual['participation'][0]-.85))),max_load_factor=float(actual['maxlf'][0]),feasible=bool(actual['feasible'][0]),operating_ratio=float(actual['cost'][0]/actual['revenue'][0]),reference_profit=float(actual['profit'][0]),reference_trips=float(actual['Q'].sum()),source_hashes=c['source_hashes'])
    assert err<1e-6 and check_summary['participation_error']<1e-10 and abs(check_summary['max_load_factor']-.92)<1e-8 and check_summary['feasible'],check_summary
    dump(ROOT/'inputs'/f'{short}.json',c); dump(ROOT/'inputs'/f'{short}_calibration.json',check_summary)
    return check_summary

if __name__=='__main__':
    reports=[build(k,v) for k,v in IDS.items()]; dump(ROOT/'inputs'/'calibration_audit.json',reports); print(json.dumps(reports,ensure_ascii=False,indent=2))
