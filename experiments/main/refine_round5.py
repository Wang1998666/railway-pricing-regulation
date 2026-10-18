"""Priority certificates and propagation of improved reference witnesses."""
import os
for k in ['OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','OMP_NUM_THREADS']:os.environ[k]='1'
import json,time,hashlib,numpy as np
from concurrent.futures import ProcessPoolExecutor,as_completed
from model import ROOT,dump,solve
from run_round5 import engine,multistart,rank,transfer,polish
from exact_single_od import Exact
from verify import scalar
def project_design(m,r,pol):
    N=np.clip(np.array(r['N']),m.Nmin,m.Nmax);ph=np.array(r['phi']).copy();step=m.spec.get('step',.025)
    if pol!='P4':N[m.candidate]=0
    if pol in ['P0','P1']:N=m.N0.copy()
    if pol!='P3-sb':ph=np.repeat(ph[:,:,:1],3,axis=2)
    ph=np.clip(.8+np.round((ph-.8)/step)*step,.8,m.fare_cap);ph[m.tier=='K']=1.
    if pol in ['P0','P2']:ph[:]=1.
    ph=np.where(N[:,:,None]>0,ph,1.)
    return N,ph
def project(m,r,pol,obj):return m.record(*project_design(m,r,pol),obj,pol)
def close_reference(states,key):
    """Test every discovered JX physical design at the common reference state."""
    s=states[key];m=engine(s['job']);records=s['records'];pool=[r for z in states.values() if z['job']['case']=='JX' for r in z['records']];changed=[]
    for pol in ['P1','P2','P3','P4','P3-sb']:
        indexes=[i for i,r in enumerate(records) if r['policy']==pol]
        if not indexes:continue
        best={obj:records[next(i for i in indexes if records[i]['objective']==obj)] for obj in ['profit','welfare']};seen=set();tested=0
        for seed in pool:
            N,ph=project_design(m,seed,pol);signature=(N.tobytes(),ph.tobytes())
            if signature in seen:continue
            seen.add(signature);a=m.record(N,ph,'profit',pol);tested+=1
            if not a['feasible']:continue
            for obj in best:
                if a[obj]>best[obj][obj]+1e-5:best[obj]=a
        for i in indexes:
            r=records[i];obj=r['objective']
            if best[obj][obj]>r[obj]+1e-5:
                nr=multistart(m,pol,obj,records+[best[obj]],strong=True)
                assert nr['feasible'] and nr[obj]>=best[obj][obj]-1e-5
                changed.append(dict(policy=pol,objective=obj,before=r[obj],after=nr[obj],tested=tested));records[i]=nr
    if changed:
        base=scalar(m.c,m.N0,np.ones((m.S,4,3)),m.income,m.electric,m.spec);errors=[]
        for r in records:
            a=scalar(m.c,np.array(r['N']),np.array(r['phi']),m.income,m.electric,m.spec);errors.append(max(abs(a['profit']-r['profit']),abs(a['U']-base['U']+a['profit']-base['profit']-r['welfare'])))
        assert max(errors)<1e-5;s['scalar_max_error']=max(errors);s['records']=records;s['cross_scenario_reference_changes']=s.get('cross_scenario_reference_changes',[])+changed;dump(ROOT/'states'/(key+'.json'),s)
    return changed
def refine(item):
    state,central=item;m=engine(state['job']);records=state['records'];changed=0;trials=[]
    for i,r in enumerate(records):
        if r['policy']=='P0' or r['meta'].get('certificate'):continue
        projected=[project(m,x,r['policy'],r['objective']) for x in central];best=max(projected+[r],key=lambda x:rank(x,r['objective']))
        if best['feasible'] and (not r['feasible'] or best[r['objective']]>r[r['objective']]+1e-5):
            nr=multistart(m,r['policy'],r['objective'],records+central+projected);nr['meta']['reference_witness_propagated']=True;records[i]=nr;changed+=1
    for _ in range(3):
        improved=False
        for i,r in enumerate(records):
            allow={'P1':['P0','P1'],'P2':['P0','P2'],'P3':['P0','P1','P2','P3'],'P4':['P0','P1','P2','P3','P4'],'P3-sb':['P0','P1','P2','P3','P3-sb']}.get(r['policy'],['P0'])
            eligible=[x for x in records if x['policy'] in allow and x['feasible']]
            if not eligible:continue
            best=max(eligible,key=lambda x:x[r['objective']])
            if not r['feasible'] or best[r['objective']]>r[r['objective']]+1e-5:
                assert not r['meta'].get('certificate') and not r['meta'].get('infeasibility_certificate'),('certificate contradicted by a known feasible design',state['key'],r['policy'],r['objective'])
                nr=multistart(m,r['policy'],r['objective'],records+central)
                for k in ['exact_single_od','certificate','infeasibility_certificate','master_incumbent_considered','lp_screened','solver_backend','master_status','upper_bound']:
                    if k in r['meta']:nr['meta'][k]=r['meta'][k]
                records[i]=nr;changed+=1;improved=True
        if not improved:break
    if changed:
        base=scalar(m.c,m.N0,np.ones((m.S,4,3)),m.income,m.electric,m.spec)
        for r in records:
            a=scalar(m.c,np.array(r['N']),np.array(r['phi']),m.income,m.electric,m.spec);error=max(abs(a['profit']-r['profit']),abs(a['U']-base['U']+a['profit']-base['profit']-r['welfare']));assert error<1e-5;trials.append(error)
        state['records']=records;state['scalar_max_error']=max(trials);state['reference_closure_changes']=changed;state['reference_closure_source']=hashlib.sha256((ROOT/'refine_round5.py').read_bytes()).hexdigest()
        if state['job']['case'] in ['HN','WC']:state['certificates']=[dict(policy=r['policy'],objective=r['objective'],certificate=r['meta'].get('certificate',False),infeasible=r['meta'].get('infeasibility_certificate',False),upper=r['meta'].get('upper_bound'),gap=r['meta'].get('certificate_gap')) for r in records if r['policy'] not in ['P0','P3-sb']]
        dump(ROOT/'states'/(state['key']+'.json'),state)
    return state['key'],changed
def project_all(states):
    for path in (ROOT/'runs').glob('*/*.json'):
        g=json.loads(path.read_text(encoding='utf-8'));s=states[g['state_key']];m=engine(g['job']);lookup={(r['policy'],r['objective']):r for r in s['records']};g['records']=[transfer(m,lookup[(r['policy'],r['objective'])],r['objective'],r['policy']) for r in g['records']];g['postprocess_sha256']=hashlib.sha256((ROOT/'refine_round5.py').read_bytes()).hexdigest();dump(path,g)
    cc=json.loads((ROOT/'constant_cost_grid.json').read_text(encoding='utf-8'));ak=json.loads((ROOT/'active_period_K.json').read_text(encoding='utf-8'))
    for g in cc['groups']+ak:
        s=states[g['state_key']];m=engine(g['job']);lookup={(r['policy'],r['objective']):r for r in s['records']};g['records']=[transfer(m,lookup[(r['policy'],r['objective'])],r['objective'],r['policy']) for r in g['records']];g['scalar_errors']=[s['scalar_max_error']]
    dump(ROOT/'constant_cost_grid.json',cc);dump(ROOT/'active_period_K.json',ak)
def main():
    states={p.stem:json.loads(p.read_text(encoding='utf-8')) for p in (ROOT/'states').glob('*.json')};keys=set()
    for ci in ['HN','WC']:
        for path in list((ROOT/'runs/E9').glob(ci+'*.json'))+list((ROOT/'runs/E6').glob(ci+'*.json')):
            g=json.loads(path.read_text(encoding='utf-8'))
            if g['job']['experiment']=='E6' or abs(g['job']['spec']['eta']-1)<1e-10:keys.add(g['state_key'])
    for key in keys:
        s=states[key];m=engine(s['job']);ex=Exact(m,s['records'])
        for i,r in enumerate(s['records']):
            if r['policy']!='P3' or r['meta'].get('certificate'):continue
            result=ex.solve('P3',r['objective'])
            if not result or not result['success']:
                opt=ex.columns('P3',r['objective'],True);result=ex.master(opt,r['objective'],True,time_limit=600,incumbent=ex.lower_bound('P3',r['objective']))
            assert result and result['success'],('priority certificate unresolved',s['job'],r['objective']);nr=result['record'];nr['policy']='P3';nr['meta'].update(certificate=True,exact_single_od=True,upper_bound=result['upper'],certificate_gap=result['gap'],finance_retention_hard=True,priority_recertification=True);s['records'][i]=nr
        s['certificates']=[dict(policy=r['policy'],objective=r['objective'],certificate=r['meta'].get('certificate',False),infeasible=r['meta'].get('infeasibility_certificate',False),upper=r['meta'].get('upper_bound'),gap=r['meta'].get('certificate_gap')) for r in s['records'] if r['policy'] not in ['P0','P3-sb']];dump(ROOT/'states'/(key+'.json'),s)
    # A feasible counterpart is evidence of feasibility even when its objective
    # is below the value of an infeasible candidate from another trajectory.
    single_od_repairs=[]
    for s in states.values():
        if s['job']['case'] not in ['HN','WC']:continue
        needs=False
        for r in s['records']:
            allow={'P1':['P0','P1'],'P2':['P0','P2'],'P3':['P0','P1','P2','P3'],'P4':['P0','P1','P2','P3','P4'],'P3-sb':['P0','P1','P2','P3','P3-sb']}.get(r['policy'],['P0'])
            eligible=[x for x in s['records'] if x['policy'] in allow and x['feasible']]
            if eligible and (not r['feasible'] or max(x[r['objective']] for x in eligible)>r[r['objective']]+1e-5):needs=True;break
        if needs:single_od_repairs.append(refine((s,[])))
    print('single-OD known-design repairs',single_od_repairs,flush=True)
    centralkey=next(k for k,s in states.items() if s['job']['case']=='JX' and s['job']['experiment']=='E2' and s['job']['id'].endswith('_reference_none'));changes=[];reference_changes=[];start=time.perf_counter()
    for cycle in range(6):
        found=close_reference(states,centralkey);reference_changes+=found;print('cross-scenario reference',cycle,'improvements',len(found),flush=True)
        if cycle and not found:break
        central=states[centralkey];todo=[(s,central['records']) for s in states.values() if s['job']['case']=='JX']
        with ProcessPoolExecutor(max_workers=8) as pool:
            for i,result in enumerate(pool.map(refine,todo)):
                changes.append(result)
                if (i+1)%25==0:print('reference closure',i+1,'/',len(todo),'elapsed',round(time.perf_counter()-start),flush=True)
        states={p.stem:json.loads(p.read_text(encoding='utf-8')) for p in (ROOT/'states').glob('*.json')}
    else:raise RuntimeError('Reference closure still improving; do not publish a dominated reference.')
    project_all(states);dump(ROOT/'reference_closure.json',dict(priority_states=sorted(keys),single_od_known_design_repairs=single_od_repairs,changes=changes,central_cross_scenario_changes=reference_changes,central_known_dominance_closed=True,improved_objectives=sum(x[1] for x in changes),seconds=time.perf_counter()-start));print('closure complete',sum(x[1] for x in changes))
if __name__=='__main__':main()
