"""Matched instrument derivatives, prior variety decomposition, and mechanisms."""
import importlib.util,json
import numpy as np
from model import ROOT,Model,dump
from calibration import prepare
from analyze import groups,record,pair_feasible
from verify import scalar

def load_old(name,file):
    sp=importlib.util.spec_from_file_location(name,file); mod=importlib.util.module_from_spec(sp);sp.loader.exec_module(mod);return mod

def elasticities():
    result=[]; eps=1e-4
    for ci in ['HN','WC','JX']:
        raw=json.loads((ROOT/'inputs'/f'{ci}.json').read_text(encoding='utf-8')); m=Model(raw); n=m.N0; ph=np.ones((m.S,4,3)); base=m.evaluate(n,ph,True); rows=[]
        for s in np.flatnonzero(m.adjustable):
            for h in range(4):
                if n[s,h]==0:continue
                outs=[]
                for sign in [-1,1]:
                    pp=ph.copy();pp[s,h]=np.exp(sign*eps);outs.append(m.evaluate(n,pp,True)['qr'][0])
                q=[x[:,:,:,s].sum(axis=(0,2,3)) for x in outs]; own=(np.log(q[1])-np.log(q[0]))/(2*eps)
                qty=base['qr'][0,:,:,h,s].sum(axis=(0,2)); allrail=(np.log(outs[1].sum())-np.log(outs[0].sum()))/(2*eps)
                rows.append(dict(product=raw['products'][s]['id'],period=h,quantity=qty.tolist(),own_by_class=own.tolist(),all_rail_response=allrail))
        # Own quantity must refer to the changed period only, not the whole day.
        for row in rows:
            s=next(i for i,p in enumerate(raw['products']) if p['id']==row['product']);h=row['period']; qs=[]
            for sign in [-1,1]:
                pp=ph.copy();pp[s,h]=np.exp(sign*eps); qr=m.evaluate(n,pp,True)['qr'][0];qs.append(qr[:,:,h,s].sum(axis=(0,2)))
            row['own_by_class']=((np.log(qs[1])-np.log(qs[0]))/(2*eps)).tolist()
        weights=np.array([r['quantity'] for r in rows]); deriv=np.array([r['own_by_class'] for r in rows]); weighted=float((weights*deriv).sum()/weights.sum())
        pooled=[]; common=[]
        for sign in [-1,1]:
            pp=ph.copy();pp[m.adjustable]*=np.exp(sign*eps); pooled.append(m.evaluate(n,pp,True)['qr'][0].sum(axis=(0,2,3,4)))
            pp=ph*np.exp(sign*eps);common.append(m.evaluate(n,pp,True)['qr'][0].sum(axis=(0,2,3,4)))
        pder=(np.log(pooled[1])-np.log(pooled[0]))/(2*eps); ader=(np.log(common[1])-np.log(common[0]))/(2*eps)
        assert abs(weighted+.8)<1e-5
        result.append(dict(case_id=ci,own_GD_weighted=weighted,own_GD_by_class=(weights*deriv).sum(axis=0)/weights.sum(axis=0),own_GD_range=[float(deriv.min()),float(deriv.max())],pooled_GD_K_fixed=pder,all_rail_fares=ader,products=rows,coefficient_scale=m.c['coefficient_scale']))
    dump(ROOT/'elasticities_round2.json',result);return result

def variety():
    oldroot=ROOT.parent/'experiments_v3_review'; cal=load_old('old_calibration',oldroot/'calibration.py'); ov=load_old('old_verifier',oldroot/'verify.py'); out=[]
    for label in ['JX_baseline','JX_k_cost_0.1']:
        g=json.loads((oldroot/'runs'/'E3'/f'{label}.json').read_text(encoding='utf-8')); p=record(g,'P3','welfare');r=record(g,'P4','welfare');raw=json.loads((ROOT/'inputs/JX.json').read_text(encoding='utf-8'));c=cal.prepare(raw,r['spec'])
        N3=np.array(p['N']);N4=np.array(r['N']);ph3=np.where(N3[:,:,None]>0,np.array(p['phi']),1.);ph4=np.where(N4[:,:,None]>0,np.array(r['phi']),1.)
        a=scalar(c,N3,ph3,'reference','none',r['spec']); b=scalar(c,N3,ph4,'reference','none',r['spec']); d=scalar(c,N4,ph4,'reference','none',r['spec']); old=ov.scalar(c,N4,ph4,'reference','none',r['spec'])
        fare=b['U']-a['U'];schedule=d['U']-b['U'];pure=old['U']-d['U'];total=r['U']-p['U'];assert abs(total-fare-schedule-pure)<1e-5
        out.append(dict(id=label,old_departures=int(N4[[p['candidate'] for p in c['products']]].sum()),total_CS=total,fare_CS=fare,schedule_availability_CS=schedule,representation_residual_CS=pure,merged_same_saved_decision_welfare=d['U']-a['U']+d['profit']-a['profit'],merged_maxlf=d['maxlf'],interpretation='Ordered accounting path; residual changes representation and cannot be called pure variety. Saved legacy designs need not remain feasible.'))
    dump(ROOT/'variety_decomposition.json',out);return out

def legacy_governance():
    oldroot=ROOT.parent/'experiments_v3_review';cal=load_old('old_calibration_gov',oldroot/'calibration.py');ov=load_old('old_verifier_gov',oldroot/'verify.py')
    g=json.loads((oldroot/'runs/E2/HN_uniform_x0.05.json').read_text(encoding='utf-8'));p=record(g,'P4','profit');w=record(g,'P4','welfare');raw=json.loads((ROOT/'inputs/HN.json').read_text(encoding='utf-8'));c=cal.prepare(raw,w['spec'])
    actual=[ov.scalar(c,np.array(r['N']),np.array(r['phi']),r['income'],r['electric'],r['spec']) for r in [p,w]]
    errs=[max(abs(a['U']-r['U']),abs(a['profit']-r['profit'])) for a,r in zip(actual,[p,w])];assert max(errs)<1e-5
    cs=w['U']-p['U'];comp=p['profit']-w['profit'];wg=w['welfare']-p['welfare'];assert abs(cs-comp-wg)<1e-5
    intermediate=ov.scalar(c,np.array(p['N']),np.array(w['phi']),w['income'],w['electric'],w['spec'])
    out=dict(id=g['job']['id'],CS_gap=cs,profit_compensation=comp,welfare_gap=wg,revenue_change=w['revenue']-p['revenue'],cost_change=w['cost']-p['cost'],fare_first_CS=intermediate['U']-p['U'],frequency_after_fare_CS=w['U']-intermediate['U'],commercial_N=p['N'],welfare_N=w['N'],commercial_phi=p['phi'],welfare_phi=w['phi'],commercial_class_trips=p['class_trips'],welfare_class_trips=w['class_trips'],scalar_errors=errs)
    dump(ROOT/'legacy_governance.json',out);return out

def mechanisms():
    C={ci:json.loads((ROOT/'inputs'/f'{ci}.json').read_text(encoding='utf-8')) for ci in ['HN','WC','JX']}; gg=groups('E2'); refs={ci:next(g for g in gg if g['job']['id']==ci+'_reference_none') for ci in C}; strict=[]; withdrawal=[]; fleet=[]; gov=[]; polarization=[]
    for ci in C:
        m=Model(C[ci]); base=m.evaluate(m.N0,np.ones((m.S,4,3)),True);q=base['qr'][0,:,:, :, :, :]; L=q[:,2]; fare=m.fare[:,None,:,:]; benchmark=float((L*fare).sum()/L.sum())
        sg=next(g for g in groups('E9') if g['job']['case']==ci and abs(g['job']['spec']['eta']-1)<1e-10)
        for obj in ['profit','welfare']:
            r0=record(refs[ci],'P3',obj);r1=record(sg,'P3',obj); restored=r1['class_trips'][2]-r0['class_trips'][2];required=base['Q'][0,:,2].sum()-r0['class_trips'][2];cost=r0['objective_value']-r1['objective_value'];dn=np.array(r1['N'])-np.array(r0['N'])
            average_run=float((m.N0[m.adjustable]*m.run_cost[m.adjustable,None]).sum()/m.N0[m.adjustable].sum())
            strict.append(dict(case_id=ci,objective=obj,sacrifice=cost,actual_trips_restored=restored,reference_shortfall=required,cost_per_restored=cost/restored if restored>1e-7 else None,cost_per_required=cost/required if required>1e-7 else None,L_reference_rail_fare=benchmark,voucher_arithmetic=max(0,required)*benchmark,net_departures=float(dn.sum()),added_departures=float(np.maximum(dn,0).sum()),withdrawn_departures=float(np.maximum(-dn,0).sum()),variable_cost_change=float((dn*m.run_cost[:,None]).sum()),reference_GD_departure_cost=average_run,departure_cost_equivalent=cost/average_run))
        for kw in [.5,1.]:
            rr=[g for g in groups('E12') if g['job']['case']==ci and g['job']['income']=='reference' and g['job']['spec']['electric_scale']==0 and g['job']['spec']['k_withdraw']==kw]
            p=record(next(g for g in rr if g['job']['spec']['eta']==.95),'P3','profit');s=record(next(g for g in rr if g['job']['spec']['eta']==1.),'P3','profit');tr=s['class_trips'][2]-p['class_trips'][2];cost=p['profit']-s['profit'];withdrawal.append(dict(case_id=ci,withdrawal=kw,feasible=p['feasible'] and s['feasible'],trips_restored=tr,profit_sacrifice=cost,cost_per_trip=cost/tr if tr>1e-7 else None,Gmax_change=s['Gmax']-p['Gmax']))
        cont=[g for g in gg if g['job']['case']==ci and not g['job']['spec'].get('road_contrast')]
        for ti,t in enumerate(['G','D','K']):
            choices=[(g,r) for g in cont for r in g['records'] if r['feasible']];g,r=max(choices,key=lambda z:z[1]['fleet_utilization'][ti]); fleet.append(dict(case_id=ci,tier=t,id=g['job']['id'],policy=r['policy'],objective=r['objective'],utilization=r['fleet_utilization'][ti],hours=r['fleet'][ti],envelope=Model(C[ci]).fleet[ti],N=r['N']))
        for g in cont:
            if not pair_feasible(g,'P4'):continue
            p=record(g,'P4','profit');w=record(g,'P4','welfare');gov.append(dict(case_id=ci,id=g['job']['id'],income=g['job']['income'],intensity=g['job']['spec']['electric_scale'],profit_gap=p['profit']-w['profit'],welfare_gap=w['welfare']-p['welfare'],CS_gap=w['U']-p['U'],revenue_change=w['revenue']-p['revenue'],cost_change=w['cost']-p['cost'],departures_change=np.array(w['N']).sum()-np.array(p['N']).sum(),class_trip_changes=np.array(w['class_trips'])-np.array(p['class_trips']),p=p,w=w))
        for x in [0.,.05,.1,.2,.35,.5,.75,1.]:
            matching=[next(g for g in cont if g['job']['income']==inc and abs(g['job']['spec']['electric_scale']-x)<1e-9) for inc in ['uniform','polarized']]
            for pol in ['P3','P4']:
                for obj in ['profit','welfare']:
                    ur,pr=[record(g,pol,obj) for g in matching];gd=np.array([p['tier']!='K' for p in C[ci]['products']]);cand=np.array([p['candidate'] for p in C[ci]['products']]);ph=lambda r:float((np.array(r['N'])[gd]*np.array(r['phi'])[gd,:,0]).sum()/np.array(r['N'])[gd].sum())
                    polarization.append(dict(case_id=ci,intensity=x,policy=pol,objective=obj,feasible_uniform=ur['feasible'],feasible_polarized=pr['feasible'],uniform_fare=ph(ur),polarized_fare=ph(pr),uniform_departures=np.array(ur['N']).sum(),polarized_departures=np.array(pr['N']).sum(),uniform_K=np.array(ur['N'])[cand].sum(),polarized_K=np.array(pr['N'])[cand].sum(),uniform_absolute_retention=ur['class_trips'][2]/m.ref_vul,polarized_absolute_retention=pr['class_trips'][2]/m.ref_vul))
    dump(ROOT/'round2_mechanisms.json',dict(strict=strict,withdrawal=withdrawal,fleet=fleet,governance=gov,polarization=polarization))

if __name__=='__main__':
    elasticities();variety();legacy_governance();mechanisms();print('round2 matched diagnostics complete')
