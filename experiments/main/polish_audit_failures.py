"""Continue only saved designs with an independently detected improving block."""
import hashlib,json
import numpy as np
from model import ROOT,Model,solve,dump
from local_review_audit import audit
from verify import scalar

def main():
    failed={r['cache_key'] for r in json.loads((ROOT/'local_audit.json').read_text(encoding='utf-8'))['failures']};fixed=[]
    for path in (ROOT/'runs').glob('E*/*.json'):
        g=json.loads(path.read_text(encoding='utf-8'));changed=False
        for i,r in enumerate(g['records']):
            key=json.dumps([r['case_id'],r['income'],r['electric'],r['spec'],r['policy'],r['objective'],r['N'],r['phi']],sort_keys=True)
            if hashlib.sha256(key.encode()).hexdigest() not in failed:continue
            raw=json.loads((ROOT/'inputs'/f'{r["case_id"]}.json').read_text(encoding='utf-8'));m=Model(raw,r['income'],r['electric'],r['spec']);nr=r
            for turn in range(3):
                nr=solve(m,r['objective'],r['policy'],seeds=g['records']+[nr],rounds=8,step=r['spec'].get('step',.025))
                test=audit(nr,engine=m)
                if test['stable']:break
            assert test['stable'] and nr['feasible'] and nr['objective_value']>=r['objective_value']-1e-6
            a=scalar(m.c,np.array(nr['N']),np.array(nr['phi']),r['income'],r['electric'],r['spec']);assert abs(a['profit']-nr['profit'])<1e-5
            nr['meta']['audit_repair']=dict(previous_objective=r['objective_value'],extra_rounds=8,continuations=turn+1,improvement=nr['objective_value']-r['objective_value'])
            g['records'][i]=nr;changed=True;fixed.append(dict(file=path.name,policy=r['policy'],objective=r['objective'],improvement=nr['objective_value']-r['objective_value'],final_audit=test))
        if changed:
            g.setdefault('post_audit_repairs',[]).append(dict(program_sha256=hashlib.sha256((ROOT/'polish_audit_failures.py').read_bytes()).hexdigest(),scope='independently detected improving block; same solver and final constraints'))
            dump(path,g)
    dump(ROOT/'audit_repairs.json',fixed);print('Polished',[(r['file'],r['improvement']) for r in fixed])
if __name__=='__main__':main()
