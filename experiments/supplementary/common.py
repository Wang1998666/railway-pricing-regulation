"""V4-only orchestration; the V3 model and verification files stay unchanged."""
import os
for k in ['OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','OMP_NUM_THREADS']:
    os.environ[k]='1'
import sys, json, hashlib, subprocess, time
from pathlib import Path
HERE=Path(__file__).resolve().parent
BASE=HERE.parent/'main'
ROUND6=BASE.parent/'policy_grid'
sys.path.insert(0,str(BASE))
import numpy as np
from model import Model, dump
from exact_single_od import Exact
from run_round5 import engine, multistart
from analyze import groups, record
from verify import scalar
sys.path.insert(0,str(ROUND6))
from run_round6 import check

def read(p): return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def git():
    p=subprocess.run(['git','-C',str(HERE),'rev-parse','HEAD'],capture_output=True,text=True)
    return p.stdout.strip() if p.returncode==0 else 'unversioned: source SHA256 recorded'
def provenance():
    import coptpy as cp, scipy
    return dict(git_commit=git(),v3_git_commit=None,v3_git_reason='Supplied V3 folder has no Git repository',
                solver='COPT',solver_version='.'.join(str(getattr(cp.COPT,'VERSION_'+x)) for x in ['MAJOR','MINOR','TECHNICAL']),
                scipy_version=scipy.__version__,python=sys.version,
                source_sha256={p.name:sha(p) for p in BASE.glob('*.py')},
                input_sha256={p.name:sha(p) for p in (BASE/'inputs').glob('*.json')})
def design_hash(r):
    n=np.array(r['N']); ph=np.array(r['phi']); y=(n.sum(axis=1)>0).astype(int);u=(n>0).astype(int)
    return hashlib.sha256(json.dumps(dict(y=y.tolist(),u=u.tolist(),N=n.tolist(),phi=ph.tolist()),sort_keys=True,separators=(',',':')).encode()).hexdigest()
def reference(ci):return next(g for g in groups('E2') if g['job']['id']==ci+'_reference_none')
def run(m,obj,warm,pol='P3',exact=None,strong=True):
    start=time.perf_counter();res=None
    if m.c['id'] in ['HN','WC'] and pol!='P3-sb':
        ex=exact or Exact(m,warm);res=ex.solve(pol,obj)
        if not res or not res.get('success'):
            res=ex.master(ex.columns(pol,obj,True),obj,True,time_limit=600,incumbent=ex.lower_bound(pol,obj))
        r=res.get('record') if res else None
        status='optimal' if res and res.get('success') else ('infeasible' if res and res.get('status')==2 else 'open')
        if r:
            r['policy']=pol;r['meta'].update(certificate=status=='optimal',upper_bound=res.get('upper'),certificate_gap=res.get('gap'),solver_backend='COPT')
    else:
        r=multistart(m,pol,obj,warm,strong=strong);status='search'
    seconds=time.perf_counter()-start
    err=check(m,r) if r and r['feasible'] else None
    cfg=dict(case=m.c['id'],income=m.income,electric=m.electric,spec=m.spec,policy=pol,objective=obj)
    out=dict(config=cfg,config_sha256=hashlib.sha256(json.dumps(cfg,sort_keys=True).encode()).hexdigest(),
             git_commit=git(),solver='COPT 8.0.6' if status!='search' else 'V3 deterministic multistart',
             status=status,seconds=seconds,scalar_error=err,design_hash=design_hash(r) if r else None,record=r)
    if res:out['master']={k:v for k,v in res.items() if k!='record'}
    return out
