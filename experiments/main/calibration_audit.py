"""Audit share reproduction, class composition, costs, and total load anchors."""
import json
import numpy as np
from model import ROOT,Model,dump
from calibration import KEYS
from run_experiments import tasks

def main():
    seen=set(); rows=[]
    for job in tasks():
        spec={k:v for k,v in job.get('spec',{}).items() if k in KEYS}; key=json.dumps([job['case'],spec],sort_keys=True)
        if key in seen: continue
        seen.add(key); case=json.loads((ROOT/'inputs'/f"{job['case']}.json").read_text(encoding='utf-8')); m=Model(case,spec=spec)
        r=m.evaluate(m.N0,np.ones((m.S,4,3)),True); c=m.c
        error=float(np.max(abs(r['qr'][0]-np.array(c['target_rail'])))); perr=float(np.max(abs(r['participation'][0]-np.array(c['class_participation_targets'])[None,:,None])))
        variable=float((m.N0*m.run_cost[:,None]).sum()); total=float(r['cost'][0]); delta=variable/total
        rr=dict(case_id=job['case'],spec=spec,flow_error=error,participation_error=perr,load_error=abs(float(r['maxlf'][0])-c['reference_load']),variable_share=delta,cost_error=abs(total-c['cost_share']*c['full_reference_cost']))
        rr['passed']=error<1e-6 and perr<1e-10 and rr['load_error']<1e-8 and abs(delta-c['variable_share'])<1e-10 and rr['cost_error']<1e-6
        rows.append(rr)
    dump(ROOT/'calibration_checks.json',dict(n=len(rows),passed=all(r['passed'] for r in rows),failures=[r for r in rows if not r['passed']],reports=rows))
    print('calibrations',len(rows),'passed',all(r['passed'] for r in rows))
if __name__=='__main__': main()
