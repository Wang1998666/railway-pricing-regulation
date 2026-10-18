"""Round-five state-deduplicated re-solve, exact HN/WC and joint multistart JX.

Immutable round-three/four records are warm starts, never final numerical claims.
"""
import os
for name in ['OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','OMP_NUM_THREADS']:os.environ[name]='1'
import argparse,json,hashlib,time,copy
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor,as_completed
import numpy as np
from model import ROOT,Model,VERSION,solve,dump
from exact_single_od import Exact
from local_review_audit import audit
from verify import scalar

SOURCES=['model.py','calibration.py','exact_single_od.py','local_review_audit.py','fast_evaluator.py','period_kernel.py','pareto_kernel.py','copt_backend.py','run_round5.py']
def hashes():return {f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in SOURCES}
def engine(job):
    spec=job.get('spec',{});raw=json.loads((ROOT/'inputs'/f"{job['case']}.json").read_text(encoding='utf-8'));m=Model(raw,spec.get('income',job.get('income','reference')),spec.get('electric',job.get('electric','none')),spec)
    if 'constant_cost_anchor' in spec:
        factor=spec['constant_cost_anchor']/spec['ref_load'];m.run_cost*=factor;m.fixed_cost*=factor
        for p in m.c['products']:p['run_cost']*=factor;p['fixed_cost']*=factor
        m.c['full_reference_cost']*=factor;z=m.evaluate(m.N0,np.ones((m.S,4,3)),True,baseline=True);m.state_profit=float(z['profit'][0]);m.state_U=float(z['U'][0])
    if spec.get('active_period_K'):
        for s,parent in m.parent.items():m.Nmax[s,m.N0[parent]==0]=0
    return m
def statekey(m):
    names=['fixed_rail','road_logs','road_probs','road','runtime','qbar','fare','fare_cap','run_cost','fixed_cost','N0','Nmin','Nmax','fixed','freq_adjustable','adjustable','candidate','tier','seats','serve','route','pax','cycle','fleet','cap','odfloor','beta','mu_sc','mu_pr','mu_mode','lam','eta_floor','ref_vul','budget','displacement_cap','state_profit','state_U']
    z={k:getattr(m,k) for k in names};z.update(case=m.c['id'],step=m.spec.get('step',.025),background=m.c['background_fraction'],parent=[(int(s),int(p)) for s,p in m.parent.items()])
    return hashlib.sha256(json.dumps(z,sort_keys=True,default=lambda a:a.tolist() if hasattr(a,'tolist') else a).encode()).hexdigest()[:24]
def rank(r,obj):return (int(r['feasible']),-r['violation'] if not r['feasible'] else 0.,r[obj])
def transfer(m,r,obj,pol):
    N=np.array(r['N']);ph=np.array(r['phi']);active=(N>0)&m.adjustable[:,None];v=ph[active];step=m.spec.get('step',.025)
    assert np.all(N>=m.Nmin-1e-8) and np.all(N<=m.Nmax+1e-8) and np.max(abs(N-N.round()))<1e-8,('frequency domain',m.c['id'],m.spec,pol)
    assert np.all(v>=.8-1e-8) and np.all(v<=m.fare_cap+1e-8),('fare-cap domain',m.c['id'],m.spec,pol)
    assert np.max(abs((v-.8)/step-np.round((v-.8)/step)),initial=0)<1e-7,('fare menu',m.c['id'],m.spec,pol)
    if pol!='P4':assert not np.any(N[m.candidate])
    if pol in ['P0','P1']:assert np.array_equal(N,m.N0)
    if pol in ['P0','P2']:assert np.all(abs(v-1)<1e-8)
    if pol!='P3-sb':assert np.max(abs(ph[:,:,1:]-ph[:,:,:1]),initial=0)<1e-8
    return m.record(N,ph,obj,pol,copy.deepcopy(r.get('meta',{})))
def polish(m,r):
    if not r['feasible'] or r['policy'] in ['P0','P1','P2'] or r['meta'].get('certificate'):return r
    for i in range(12):
        a=audit(r,engine=m)
        if a['stable']:r['meta']['joint_audit']=a;return r
        r=solve(m,r['objective'],r['policy'],seeds=[r],initial=r,rounds=8,step=m.spec.get('step',.025))
    raise RuntimeError(('unstable',m.c['id'],m.spec,r['policy'],r['objective'],a))
def multistart(m,pol,obj,warm,strong=False):
    from fast_evaluator import install
    install(m)
    rr=[];seeds=[];seen=set()
    for r in warm:
        if pol!='P4' and np.array(r['N'])[m.candidate].sum()>0:continue
        if pol!='P3-sb' and r['policy']=='P3-sb':continue
        key=json.dumps([r['N'],r['phi']],default=lambda a:a.tolist())
        if key not in seen:seen.add(key);seeds.append(r)
    rr.append(solve(m,obj,pol,seeds=seeds,rounds=8,step=m.spec.get('step',.025)))
    # Independent trajectories: reference and best feasible opposite objective.
    reference=m.record(m.N0,np.ones((m.S,4,3)),obj,pol)
    inits=[reference]
    if seeds:
        for other in [obj,'welfare' if obj=='profit' else 'profit']:
            ranked=[]
            for r in seeds:
                N=np.clip(np.array(r['N']),m.Nmin,m.Nmax);ph=np.array(r['phi']);
                if pol in ['P0','P1']:N=m.N0.copy()
                if pol in ['P0','P2']:ph=np.ones_like(ph)
                if pol!='P4':N[m.candidate]=0
                if pol!='P3-sb':ph=np.repeat(ph[:,:,:1],3,axis=2)
                ph=np.clip(.8+np.round((ph-.8)/m.spec.get('step',.025))*m.spec.get('step',.025),.8,m.fare_cap);ph[m.tier=='K']=1.
                ranked.append(m.record(N,ph,obj,pol))
            inits.append(max(ranked,key=lambda r:rank(r,other)))
    if strong and pol in ['P3','P4','P3-sb']:
        for fac,price in [(.85,1.1),(1.15,.9)]:
            N=m.N0.copy();N[m.freq_adjustable]=np.clip(np.rint(N[m.freq_adjustable]*fac),m.Nmin[m.freq_adjustable],m.Nmax[m.freq_adjustable]);ph=np.ones((m.S,4,3));ph[m.adjustable]=price;inits.append(m.record(N,ph,obj,pol))
    done={json.dumps([rr[0]['N'],rr[0]['phi']],default=lambda a:a.tolist())}
    for r in inits:
        key=json.dumps([r['N'],r['phi']],default=lambda a:a.tolist())
        if key in done:continue
        done.add(key);rr.append(solve(m,obj,pol,seeds=seeds,initial=r,rounds=8,step=m.spec.get('step',.025)))
    r=polish(m,max(rr,key=lambda r:rank(r,obj)));r['meta'].update(multistart_trajectories=len(rr),coordinated_fare_frequency=True)
    return r
def execute(state):
    path=ROOT/'states'/(state['key']+'.json');source=hashes()
    prior=None
    if path.exists():
        prior=json.loads(path.read_text(encoding='utf-8'))
        closed=not any(r['case_id'] in ['HN','WC'] and r['policy'] not in ['P0','P3-sb'] and not r['meta'].get('certificate') and not r['meta'].get('infeasibility_certificate') and not r['meta'].get('lp_screened') for r in prior['records'])
        closed=closed and not any(r['case_id'] in ['HN','WC'] and r['policy'] not in ['P0','P3-sb'] and not r['meta'].get('certificate') and not r['meta'].get('infeasibility_certificate') and r['meta'].get('solver_backend')!='COPT' for r in prior['records'])
        def matching(f):
            old=prior.get('source_hashes',{}).get(f)
            return old==source[f] or (f=='exact_single_od.py' and old in ['0012fabe4e934131d8d5e2caa78cdc812f64db60affaece43e588d31a686b488','56a5f618843e2c355d879ee11e1ac6521d9fd2b496d25199d318e2269eb9ab34','82562ee846def2a1647bd7f8ed6e7d000728c3bef467e8cf9c6d3ab0b45ef520','8b62afb1c50c871c6314a11f8d3acd70ab8f7c8736c4d5deb3731c406fe0e3e2']) or (f=='fast_evaluator.py' and old=='d972472e060ac0aaad01d3b4d8ced1ff57e21f0eaeb6ea774c6cf4bcc62ed690')
        if closed and all(matching(f) for f in SOURCES if f!='run_round5.py' and (f not in ['fast_evaluator.py','period_kernel.py','pareto_kernel.py','copt_backend.py'] or f in prior.get('source_hashes',{}))) and prior.get('policies')==state['policies']:
            if prior['source_hashes']!=source:
                prior['source_hashes_at_solve']=prior['source_hashes'];prior['source_hashes']=source;prior['cache_reuse_reason']='Solver/audit mathematics match; uncertified masters without incumbent closure are rerun. Period-cache equivalence validated independently to <1e-5 CNY.';dump(path,prior)
            return prior
    start=time.perf_counter();m=engine(state['job']);warm=state['warm']+(prior['records'] if prior else []);records=[];certificates=[];exact=Exact(m,seeds=warm) if m.c['id'] in ['HN','WC'] else None
    central=state['job']['experiment']=='E2' and state['job']['id'].endswith('_reference_none')
    if not central:
        refpath=ROOT/'states'/(statekey(engine({'case':m.c['id']}))+'.json')
        if refpath.exists():warm=warm+json.loads(refpath.read_text(encoding='utf-8'))['records']
    if exact:exact.seeds=warm
    order=[p for p in ['P0','P1','P2','P4','P3','P3-sb'] if p in state['policies']]
    for pol in order:
        for obj in ['profit','welfare']:
            result=exact.solve(pol,obj) if exact and pol not in ['P0','P3-sb'] else None
            if result and result.get('success'):r=result['record']
            else:
                masterseed=[result['record']] if result and 'record' in result else []
                r=multistart(m,pol,obj,warm+records+masterseed,strong=central or pol=='P3-sb') if pol!='P0' else solve(m,obj,pol)
                if exact and pol not in ['P0','P3-sb']:
                    infeasible=result is None or result.get('status')==2
                    r['meta'].update(exact_single_od=True,certificate=False,infeasibility_certificate=bool(infeasible),master_incumbent_considered=True,lp_screened=True,solver_backend='COPT' if result is None else result.get('backend','COPT'),master_status=None if result is None else result.get('status'),upper_bound=None if result is None else result.get('upper'))
                    if infeasible:assert not r['feasible'],('inconsistent infeasibility',state['key'],pol,obj)
            records.append(r)
            if exact and pol not in ['P0','P3-sb']:certificates.append(dict(policy=pol,objective=obj,certificate=r['meta'].get('certificate',False),infeasible=r['meta'].get('infeasibility_certificate',False),upper=r['meta'].get('upper_bound'),gap=r['meta'].get('certificate_gap')))
    # Nested instruments and opposite-objective witnesses must not dominate.
    for cycle in range(4):
        changed=False
        for i,r in enumerate(records):
            allowed={'P0':['P0'],'P1':['P0','P1'],'P2':['P0','P2'],'P3':['P0','P1','P2','P3'],'P4':['P0','P1','P2','P3','P4'],'P3-sb':['P0','P1','P2','P3','P3-sb']}[r['policy']]
            seeds=[x for x in records if x['policy'] in allowed];best=max(seeds,key=lambda x:rank(x,r['objective']))
            if rank(best,r['objective'])>rank(r,r['objective']) and best[r['objective']]>r[r['objective']]+1e-5:
                assert not r['meta'].get('certificate'),('dominated exact',state['key'],r['policy'],r['objective'])
                nr=multistart(m,r['policy'],r['objective'],warm+records)
                for k in ['exact_single_od','certificate','infeasibility_certificate','master_incumbent_considered','lp_screened','solver_backend','master_status','upper_bound']:
                    if k in r['meta']:nr['meta'][k]=r['meta'][k]
                records[i]=nr;changed=True
        if not changed:break
    checks=[];base=scalar(m.c,m.N0,np.ones((m.S,4,3)),m.income,m.electric,m.spec)
    for r in records:
        a=scalar(m.c,np.array(r['N']),np.array(r['phi']),m.income,m.electric,m.spec);err=max(abs(a['profit']-r['profit']),abs(a['U']-base['U']+a['profit']-base['profit']-r['welfare']),abs(a['maxlf']-r['maxlf']));assert err<1e-5,(state['key'],err);checks.append(err)
    out=dict(key=state['key'],job=state['job'],policies=state['policies'],records=records,certificates=certificates,scalar_max_error=max(checks),source_hashes=source,seconds=time.perf_counter()-start)
    dump(path,out);return out
def collect():
    groups=[]
    for path in sorted((ROOT/'runs').glob('*/*.json')):
        g=json.loads(path.read_text(encoding='utf-8'));job=g['job']
        if 'experiment' not in job:
            job=dict(experiment='E16',id=path.stem,case=job['case'],income='reference',electric='none',spec=job['spec'],anchor=job['anchor'],cap=job['cap'],policies=sorted(set(r['policy'] for r in g['records'])))
        g['job']=job;groups.append((str(path),g))
    cc=json.loads((ROOT/'constant_cost_grid.json').read_text(encoding='utf-8'))
    for i,g in enumerate(cc['groups']):groups.append(('CC:'+str(i),g))
    ak=json.loads((ROOT/'active_period_K.json').read_text(encoding='utf-8'))
    for i,g in enumerate(ak):
        g['job']=dict(experiment='AK',id=f"{g['case_id']}_{g['k_cost']}",case=g['case_id'],income='reference',electric='none',spec={'k_cost':g['k_cost'],'active_period_K':True},policies=['P3','P4']);groups.append(('AK:'+str(i),g))
    common={ci:[] for ci in ['HN','WC','JX']}
    for name,g in groups:
        if g['job']['experiment']=='E16' or (g['job']['experiment']=='E2' and g['job']['id'].endswith('_reference_none')):common[g['job']['case']]+=[{k:r[k] for k in ['N','phi','policy']} for r in g['records']]
    states={};mapping={}
    for name,g in groups:
        job=g['job'];m=engine(job);key=statekey(m);mapping[name]=key
        if key not in states:states[key]=dict(key=key,job=job,policies=[],warm=[])
        if job['experiment']=='E2' and job['id'].endswith('_reference_none'):states[key]['job']=job
        s=states[key];s['policies']=sorted(set(s['policies'])|set(job.get('policies',[r['policy'] for r in g['records']])));s['warm']+=[{k:r[k] for k in ['N','phi','policy']} for r in g['records']];g['records']=[]
    for s in states.values():
        warm=s['warm']+common[s['job']['case']];seen=set();unique=[]
        for r in warm:
            k=json.dumps([r['N'],r['phi']],default=lambda a:a.tolist())
            if k not in seen:seen.add(k);unique.append(r)
        s['warm']=unique
    return groups,list(states.values()),mapping,cc,ak
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--workers',type=int,default=8);ap.add_argument('--central',action='store_true');ap.add_argument('--limit',type=int);args=ap.parse_args();groups,states,mapping,cc,ak=collect()
    if args.central:states=[s for s in states if s['job']['experiment']=='E2' and s['job']['id'].endswith('_reference_none')]
    states.sort(key=lambda s:(not(s['job']['experiment']=='E2' and s['job']['id'].endswith('_reference_none')),s['job']['case'],s['key']))
    if args.limit:states=states[:args.limit]
    print('STATES',len(states),'GROUPS',len(groups),flush=True);start=time.perf_counter();results={}
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures={pool.submit(execute,s):s for s in states}
        for i,f in enumerate(as_completed(futures)):
            r=f.result();results[r['key']]=r
            print(i+1,'/',len(states),r['job']['case'],r['job']['id'],'sec',round(r['seconds'],1),'elapsed',round(time.perf_counter()-start,1),flush=True)
    # Projection re-evaluates the physical design under each exact job metadata.
    for name,g in groups:
        if mapping[name] not in results:continue
        st=results[mapping[name]];m=engine(g['job']);lookup={(r['policy'],r['objective']):r for r in st['records']};pols=g['job'].get('policies',sorted(set(r['policy'] for r in g['records'])))
        g['records']=[transfer(m,lookup[(p,o)],o,p) for p in pols for o in ['profit','welfare']];g.update(version=VERSION,source_hashes=hashes(),state_key=mapping[name],controller_file='run_round5.py',controller_sha256=hashes()['run_round5.py'],solver_sha256=hashes()['model.py'],calibration_sha256=hashes()['calibration.py'],fingerprint=hashlib.sha256((ROOT/'inputs'/f"{m.c['id']}.json").read_bytes()).hexdigest(),budgets=[],seconds=st['seconds'],round5=True)
        if name.startswith('CC:'):g['scalar_errors']=[st['scalar_max_error']];g['local_audits']=[];cc['groups'][int(name[3:])]=g
        elif name.startswith('AK:'):g['scalar_errors']=[st['scalar_max_error']];ak[int(name[3:])]=g
        else:dump(Path(name),g)
    dump(ROOT/'constant_cost_grid.json',cc);dump(ROOT/'active_period_K.json',ak)
    dump(ROOT/'round5_manifest.json',dict(groups=len(groups),states=len(states),mapping=mapping,source_hashes=hashes(),seconds=time.perf_counter()-start,exact_certificates=[dict(state=r['key'],job=r['job'],certificates=r['certificates']) for r in results.values()]))
    print('COMPLETE',len(results),flush=True)
if __name__=='__main__':main()
